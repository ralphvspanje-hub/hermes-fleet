"""Draft a copy-paste intro/application for a listing. Returns TEXT only: the user
reviews, edits, and sends every message themselves; the agent never sends.
Uses the Anthropic SDK; the client is injectable so tests run without network or the
`anthropic` package. Off by default in the pipeline (see pipeline.scan draft_fn)."""
from .models import HousingType

# The user reviews + edits before sending. Fill these in for your own situation.
DEFAULT_PROFILE = {
    "name": "YOUR_NAME",
    "age": None,
    "facts": "YOUR_SITUATION (job, start date, why you need a place, registration)",
    "interests": "YOUR_INTERESTS",
    "contact": "YOUR_NAME (shares contact details in conversation)",
}


def _who(profile):
    """'Name (age)' when an age is given, else just the name."""
    age = profile.get("age")
    return f"{profile['name']} ({age})" if age is not None else profile["name"]


def build_prompt(listing, profile):
    lane = ("een gedeeld huis (huisgenoten)" if listing.housing_type == HousingType.SHARED
            else "een zelfstandige studio/appartement (makelaar/verhuurder)")
    return (
        "Schrijf een korte, warme, natuurlijke reactie in het Nederlands op deze "
        f"woningadvertentie. Het is {lane}. Pas de toon daarop aan (informeel & "
        "persoonlijk voor huisgenoten; beknopt & net voor een makelaar). Verwerk waar "
        "relevant één gedeelde interesse als de advertentie er een noemt. Eén alinea, "
        "geen opsomming, geen aanhef-placeholder als de naam onbekend is.\n\n"
        f"--- Over de afzender ---\n{_who(profile)}; "
        f"{profile['facts']}. Interesses: {profile['interests']}. "
        f"Contact om af te sluiten: {profile['contact']}.\n\n"
        f"--- De advertentie ---\nTitel: {listing.title}\nBuurt: {listing.area or '-'}\n"
        f"Prijs: €{listing.price_eur or '-'}\nTekst: {listing.description}\n"
    )


def draft_intro(listing, client=None, model="claude-sonnet-5", profile=None,
                max_tokens=700):
    profile = profile or DEFAULT_PROFILE
    client = client or _default_client()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": build_prompt(listing, profile)}],
    )
    return _text_of(resp)


def _text_of(resp):
    parts = [getattr(b, "text", "") for b in getattr(resp, "content", [])]
    return "".join(parts).strip()


def _default_client():
    import anthropic   # lazy: only for live runs
    return anthropic.Anthropic()
