"""Runtime / I/O configuration - distinct from Config (which holds decision
thresholds). Telegram credentials come from the environment, never hardcoded
(secrets stay out of the agent and the repo)."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    db_path: str = "home_hunt.sqlite"
    # Default live mix: portal alert emails are the primary path (many portals can't
    # or mustn't be scraped). Every other registered source (example, example_live,
    # browse, or your own) is enabled explicitly via HOME_HUNT_SOURCES.
    enabled_sources: tuple = ("email_alerts",)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    imap_host: str = ""
    imap_user: str = ""
    imap_password: str = ""
    request_timeout: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    @classmethod
    def from_env(cls, **overrides):
        """Build from HOME_HUNT_* env vars; explicit kwargs override env."""
        values = dict(
            telegram_bot_token=os.environ.get("HOME_HUNT_TG_TOKEN", ""),
            telegram_chat_id=os.environ.get("HOME_HUNT_TG_CHAT", ""),
            imap_host=os.environ.get("HOME_HUNT_IMAP_HOST", ""),
            imap_user=os.environ.get("HOME_HUNT_IMAP_USER", ""),
            imap_password=os.environ.get("HOME_HUNT_IMAP_PASSWORD", ""),
            db_path=os.environ.get("HOME_HUNT_DB", "home_hunt.sqlite"),
        )
        sources = os.environ.get("HOME_HUNT_SOURCES", "").strip()
        if sources:                       # deploy knob: comma-separated live source names
            values["enabled_sources"] = tuple(
                s.strip() for s in sources.split(",") if s.strip())
        values.update(overrides)
        return cls(**values)
