"""Source interface + registry. Every source (HTML scraper, computer-use sweep,
email-alert reader) implements `fetch() -> list[Listing]` and registers a name."""
from abc import ABC, abstractmethod

_REGISTRY = {}


def register(cls):
    """Class decorator: add a Source subclass to the registry under its `name`."""
    _REGISTRY[cls.name] = cls
    return cls


class Source(ABC):
    name = "base"
    est_cost_eur = 0.0    # >0 marks a paid (Tier-3) source the SpendGuard gates

    def __init__(self, settings=None):
        self.settings = settings

    @abstractmethod
    def fetch(self):
        """Return a list[Listing]. May raise on network/parse failure (the
        pipeline isolates each source in try/except and reports loudly)."""
        raise NotImplementedError


def available_sources():
    return dict(_REGISTRY)


def get_enabled(settings):
    """Instantiate the enabled sources (in settings order), skipping unknown names."""
    return [_REGISTRY[n](settings) for n in settings.enabled_sources if n in _REGISTRY]
