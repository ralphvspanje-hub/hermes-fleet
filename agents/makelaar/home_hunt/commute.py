"""Optional Tier-3 commute refinement for the commuter-city exception (geo.py,
HOME_HUNT_COMMUTER_CITIES, off by default): for a SHOW/FLAG listing in an opted-in
commuter city, ask the browse engine to map-screenshot the address and confirm a
≤10-min walk to that city's Centraal station; downgrade to DROP if not. `runner` is
injectable; the default invokes the engine."""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from .models import Verdict
from .geo import commuter_cities, _present

# scraped area text flows into the browse-engine LLM prompt - keep only plain address
# characters so it can't inject instructions or break the prompt's quoting.
_UNSAFE_ADDR = re.compile(r"[^A-Za-z0-9 ,.\-]")


def _sanitize_address(address):
    first_line = (address or "").split("\n")[0]
    return _UNSAFE_ADDR.sub(" ", first_line).strip()[:120]


def _default_runner(address):
    work = tempfile.mkdtemp()
    eng = str(Path.home() / "home-hunt" / "engine" / "run_homehunt_browse.sh")
    subprocess.run(["bash", eng, "commute", work, address], check=False,
                   stdin=subprocess.DEVNULL, timeout=300)
    p = Path(work) / "out.json"
    return json.loads(p.read_text()) if p.exists() else {"verdict": None}


def verify_walk(address, runner=None):
    runner = runner or _default_runner
    try:
        return runner(_sanitize_address(address)).get("verdict")
    except Exception:
        return None      # unknown → bias to show (don't drop on a failed check)


def _in_commuter_city(area):
    a = (area or "").lower()
    return any(_present(c, a) for c in commuter_cities())


def refine_commute_listings(decisions, runner=None):
    out = []
    for d in decisions:
        if (d.verdict in (Verdict.SHOW, Verdict.FLAG)
                and _in_commuter_city(d.listing.area)):
            ok = verify_walk(d.listing.area, runner=runner)
            if ok is False:                      # only a confirmed FAIL drops it
                out.append(type(d)(
                    listing=d.listing, verdict=Verdict.DROP, score=0,
                    reasons=["commute: >10 min walk to Centraal"] + list(d.reasons),
                    scam_flags=d.scam_flags))
                continue
        out.append(d)
    return out
