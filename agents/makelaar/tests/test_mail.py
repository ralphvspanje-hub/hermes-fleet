from home_hunt.mail import read_unseen, Message


class _FakeIMAP:
    """Minimal imaplib-shaped fake: one unseen multipart/alternative message."""
    def __init__(self):
        self.stored = []

    def search(self, charset, *criteria):
        return "OK", [b"1"]

    def fetch(self, num, parts):
        raw = (b"From: Example <alerts@example.com>\r\nSubject: Nieuw aanbod\r\n"
               b"Content-Type: text/html; charset=utf-8\r\n\r\n"
               b"<html><a href='https://example.com/listing/123/'>Studio</a></html>")
        return "OK", [(b"1 (RFC822 {0})", raw)]

    def store(self, num, flags, value):
        self.stored.append((num, value))
        return "OK", [b""]


def test_read_unseen_parses_from_subject_html():
    msgs = read_unseen(_FakeIMAP(), mark_seen=True)
    assert len(msgs) == 1
    m = msgs[0]
    assert isinstance(m, Message)
    assert "example.com" in m.from_addr.lower()
    assert m.subject == "Nieuw aanbod"
    assert "example.com/listing" in m.html
