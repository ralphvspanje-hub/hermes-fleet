"""Source registry package. Importing this package registers all built-in
sources: each applies the @register decorator at import time, so they must be
imported for get_enabled() to find them on the live scan path. Add your own
source module to this import list (see example_site.py for the pattern)."""
from . import example_site  # noqa: F401  (Tier-1 HTML scraper template)
from . import email_alerts  # noqa: F401  (Tier-1: portal alert emails)
from . import playwright_fetch  # noqa: F401  (Tier-2: JS-rendered pages)
from . import browse_json  # noqa: F401  (Tier-3: headless browse engine)
