"""Regression guard: importing the sources package (as the live scan path does)
must self-register all built-in adapters. Run in a FRESH interpreter so it can't
pass just because another test module already imported an adapter."""
import subprocess
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)


def test_all_adapters_register_on_package_import():
    code = (
        "from home_hunt.settings import Settings;"
        "from home_hunt.sources.base import get_enabled, available_sources;"
        "print('NAMES', sorted(available_sources()));"
        "print('ENABLED', len(get_enabled(Settings())))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    for name in ("example", "email_alerts", "example_live", "browse"):
        assert name in out.stdout, f"{name} not registered:\n{out.stdout}"
    # default enabled_sources is just the email-alerts path
    assert "ENABLED 1" in out.stdout, out.stdout
