from home_hunt.settings import Settings


def test_defaults():
    s = Settings()
    assert s.db_path.endswith(".sqlite")
    assert s.enabled_sources == ("email_alerts",)   # primary path; others opt-in
    assert s.telegram_bot_token == ""        # never hardcoded
    assert s.request_timeout > 0
    assert "Mozilla" in s.user_agent


def test_from_env(monkeypatch):
    monkeypatch.setenv("HOME_HUNT_TG_TOKEN", "tok123")
    monkeypatch.setenv("HOME_HUNT_TG_CHAT", "555")
    monkeypatch.setenv("HOME_HUNT_DB", "/tmp/x.sqlite")
    s = Settings.from_env()
    assert s.telegram_bot_token == "tok123"
    assert s.telegram_chat_id == "555"
    assert s.db_path == "/tmp/x.sqlite"


def test_from_env_override_wins(monkeypatch):
    monkeypatch.setenv("HOME_HUNT_TG_TOKEN", "fromenv")
    s = Settings.from_env(telegram_bot_token="explicit")
    assert s.telegram_bot_token == "explicit"


def test_from_env_sources_override(monkeypatch):
    monkeypatch.setenv("HOME_HUNT_SOURCES", "email_alerts, example")
    s = Settings.from_env()
    assert s.enabled_sources == ("email_alerts", "example")   # deploy can pick live tiers


def test_from_env_sources_default_when_unset(monkeypatch):
    monkeypatch.delenv("HOME_HUNT_SOURCES", raising=False)
    assert Settings.from_env().enabled_sources[0] == "email_alerts"   # default mix


def test_imap_defaults_empty_and_from_env(monkeypatch):
    assert Settings().imap_host == "" and Settings().imap_user == ""
    monkeypatch.setenv("HOME_HUNT_IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("HOME_HUNT_IMAP_USER", "alerts@example.com")
    monkeypatch.setenv("HOME_HUNT_IMAP_PASSWORD", "app-pw")
    s = Settings.from_env()
    assert s.imap_host == "imap.example.com"
    assert s.imap_user == "alerts@example.com"
    assert s.imap_password == "app-pw"
