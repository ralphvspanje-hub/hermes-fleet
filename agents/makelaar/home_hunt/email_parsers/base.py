"""Per-sender email-alert parser base. Each parser turns one alert email's HTML
body into a list[Listing]. Dispatch (matching a parser to a From address) is owned
by the EmailAlerts source via an explicit ordered parser list - see
sources/email_alerts.py - so there is deliberately no global registry here."""


class EmailParser:
    name = "base"
    senders = ()              # substrings matched against the From header (lowercased)

    def matches(self, from_addr):
        f = (from_addr or "").lower()
        return any(s in f for s in self.senders)

    def parse(self, html, subject=""):
        raise NotImplementedError
