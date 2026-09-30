"""Tier 3: ingest the JSON that run_homehunt_browse.sh writes (headless Claude Code
+ Playwright MCP did the logged-in/adaptive browsing). Reuses the CLI's dict→Listing
mapper so the contract matches the rest of the engine."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from .base import Source, register
from ..cli import _listing_from_dict


def listings_from_browse_json(path):
    # Note: the engine emits already-parsed price_eur ints, so _listing_from_dict
    # takes them verbatim: the <€300 scrape floor (normalize.parse_price) does NOT
    # apply here. A genuinely cheap browsed room price is therefore kept as-is.
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    source = doc.get("source", "browse")
    out = []
    for d in doc.get("listings", []):
        d.setdefault("source", source)
        out.append(_listing_from_dict(d))
    return out


@register
class BrowseSource(Source):
    """Tier-3 source: run the browse engine in `listings` mode against the search page
    in HOME_HUNT_BROWSE_URL, then ingest the out.json it writes. For sites that need a
    login or adaptive navigation. `runner` is injectable (tests pass an out.json
    path); live use is gated behind the SpendGuard in the pipeline."""
    name = "browse"
    # Conservative CEILING per headless-Claude + browser run (not a fixed price): a
    # real run can cost well over a token-pennies estimate, so we book it high so the
    # monthly SpendGuard actually engages rather than never tripping.
    est_cost_eur = 2.0

    def __init__(self, settings=None, runner=None):
        super().__init__(settings)
        self._runner = runner or self._default_runner

    def _default_runner(self):
        work = tempfile.mkdtemp()
        eng = str(Path.home() / "home-hunt" / "engine" / "run_homehunt_browse.sh")
        subprocess.run(["bash", eng, "listings", work], check=False,
                       stdin=subprocess.DEVNULL, timeout=600)
        return str(Path(work) / "out.json")

    def fetch(self):
        path = self._runner()
        if not path or not os.path.exists(path):
            return []
        return listings_from_browse_json(path)
