from home_hunt.sources.email_alerts import EmailAlerts
from home_hunt.mail import Message
from home_hunt.settings import Settings


def _msgs():
    return [
        Message(from_addr="Example <alerts@example.com>", subject="Nieuw",
                html=('<div class="listing"><a href="https://example.com/listing/43219999">Studio</a>'
                      '<span>&euro; 1.200 p/m</span></div>')),
        Message(from_addr="x@unknown.com", subject="spam", html="<a href='http://x'>y</a>"),
    ]


def test_email_alerts_parses_known_senders_only():
    src = EmailAlerts(Settings(), reader=lambda: _msgs())
    listings = src.fetch()
    assert [l.source for l in listings] == ["example_alerts"]    # unknown sender dropped
    assert listings[0].source_id == "/listing/43219999"


def test_email_alerts_dispatches_generic_sender():
    msgs = [Message(
        from_addr="Example Alerts <noreply@EXAMPLE.COM>", subject="Nieuw aanbod",
        html=('<div class="listing">'
              '<a href="https://example.com/huurwoning/amsterdam/55021/voorbeeldstraat">Studio</a>'
              '<span>&euro; 1.150 p/m</span></div>'))]
    src = EmailAlerts(Settings(), reader=lambda: msgs)
    listings = src.fetch()
    assert [l.source for l in listings] == ["example_alerts"]
    assert listings[0].price_eur == 1150
