"""Tier-1 source: read the alert inbox and turn each email into Listings.

Most rental portals let you save a search and email you each new match; forwarding
those alerts to a dedicated inbox is the cheapest and most terms-friendly way to get
listings. The source owns an explicit, ordered parser list: put any bespoke
per-portal parser (a subclass of email_parsers.base.EmailParser) BEFORE the generic
fallbacks so it wins the sender match. Dispatch is kept local (not via a global
registry) so it is deterministic and free of cross-module registration side-effects.
`reader` is injectable (tests pass messages directly)."""
from .base import Source, register
from ..mail import read_unseen, connect
from ..email_parsers.generic import GenericEmail

# (source name, From-address substrings) for alert senders handled by the generic
# parser. Replace with the portals you have saved-search alerts on.
_GENERIC_SENDERS = (
    ("example_alerts", ("example.com",)),
)


@register
class EmailAlerts(Source):
    name = "email_alerts"

    def __init__(self, settings=None, reader=None):
        super().__init__(settings)
        self._reader = reader or self._default_reader
        # bespoke parsers (if you add any) go first so they win over the generics
        self._parsers = [GenericEmail(src, senders) for src, senders in _GENERIC_SENDERS]

    def _default_reader(self):
        s = self.settings
        conn = connect(s.imap_host, s.imap_user, s.imap_password)
        try:
            return read_unseen(conn, mark_seen=True)   # materialises the list
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _parse(self, message):
        parser = next((p for p in self._parsers if p.matches(message.from_addr)), None)
        if parser is None:
            return []
        try:
            return parser.parse(message.html, message.subject)
        except Exception:
            return []

    def fetch(self):
        out = []
        for message in self._reader():
            out.extend(self._parse(message))
        return out
