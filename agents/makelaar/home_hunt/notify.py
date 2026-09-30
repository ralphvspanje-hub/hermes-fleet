"""Push to Telegram via the Bot API (stdlib urllib - no requests dep). The poster
is injectable for tests. Splits any message over Telegram's 4096-char limit
(long plain messages silently truncate otherwise)."""
import json
import urllib.parse
import urllib.request
from .models import Verdict

_TG_LIMIT = 4096


def _default_poster(token, method, payload):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def format_card(decision, draft=""):
    l = decision.listing
    tag = "⚠️ FLAG" if decision.verdict == Verdict.FLAG else "MATCH"
    lines = [
        f"[{decision.score}] {tag} - {l.title}",
        f"€{l.price_eur or '?'} · {l.area or '?'} · {l.housing_type.value}",
        l.url,
        "· " + " | ".join(decision.reasons),
    ]
    if draft:
        lines += ["", "✍️ Concept-bericht (jij verstuurt zelf):", draft]
    return "\n".join(lines)


def format_digest(decisions, hidden_count=0):
    head = f"🏠 Dagdigest - {len(decisions)} match(es)"
    if hidden_count:
        head += f"  ·  {hidden_count} weggefilterd"
    body = [f"[{d.score}] {d.listing.title} - €{d.listing.price_eur or '?'} "
            f"· {d.listing.area or '?'}\n   {d.listing.url}" for d in decisions]
    return head + "\n\n" + "\n".join(body) if body else head + "\n\n(geen nieuwe matches vandaag)"


def _chunks(text, n=_TG_LIMIT):
    """Split into <=n-char Telegram messages on LINE boundaries, so a URL (always on
    its own line) is never cut across two messages. A single line longer than n is
    hard-split as a last resort (URLs are far shorter than the limit)."""
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(line) > n:                          # pathological over-long line
            if cur:
                chunks.append(cur)
                cur = ""
            chunks += [line[i:i + n] for i in range(0, len(line), n)]
            continue
        candidate = f"{cur}\n{line}" if cur else line
        if len(candidate) > n:
            chunks.append(cur)
            cur = line
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks or [""]


class Notifier:
    def __init__(self, settings, poster=None):
        self.settings = settings
        self._post = poster or _default_poster

    def _send(self, text):
        out = []
        for chunk in _chunks(text):
            out.append(self._post(
                self.settings.telegram_bot_token, "sendMessage",
                {"chat_id": self.settings.telegram_chat_id, "text": chunk,
                 "disable_web_page_preview": "true"}))
        return out

    def instant(self, decision, draft=""):
        return self._send(format_card(decision, draft))

    def digest(self, decisions, hidden_count=0):
        return self._send(format_digest(decisions, hidden_count))
