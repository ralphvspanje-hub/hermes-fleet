"""Read unseen emails from an IMAP inbox into (from, subject, html) tuples.
The connection is injectable so tests use a fake; live runs use imaplib over SSL."""
import email
from dataclasses import dataclass
from email.header import decode_header, make_header


@dataclass
class Message:
    from_addr: str
    subject: str
    html: str


def _decode(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""      # degrade to the raw (possibly still-encoded) header


def _html_of(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", "replace")


def read_unseen(imap, mailbox="INBOX", mark_seen=True):
    """imap: an object with imaplib-shaped select/search/fetch/store. Returns list[Message]."""
    if hasattr(imap, "select"):
        imap.select(mailbox)
    typ, data = imap.search(None, "UNSEEN")
    if typ != "OK":
        return []
    out = []
    for num in (data[0].split() if data and data[0] else []):
        typ, msg_data = imap.fetch(num, "(RFC822)")
        if typ != "OK" or not msg_data:
            continue
        raw = next((p[1] for p in msg_data if isinstance(p, tuple)), None)
        if raw is None:
            continue
        msg = email.message_from_bytes(raw)
        out.append(Message(from_addr=_decode(msg.get("From")),
                           subject=_decode(msg.get("Subject")),
                           html=_html_of(msg)))
        if mark_seen:
            imap.store(num, "+FLAGS", "\\Seen")
    return out


def connect(host, user, password, port=993):
    """Live IMAP-over-SSL connection (not used in tests)."""
    import imaplib
    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(user, password)
    return conn
