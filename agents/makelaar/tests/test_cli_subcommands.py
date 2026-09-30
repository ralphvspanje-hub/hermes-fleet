from home_hunt.cli import main
from home_hunt.models import Verdict


def test_classify_subcommand_still_works(capsys, tmp_path):
    import json
    p = tmp_path / "l.json"
    p.write_text(json.dumps([{"source": "f", "source_id": "1", "url": "u",
                              "title": "Studio De Pijp",
                              "description": "inschrijving mogelijk", "price_eur": 1150,
                              "housing_type": "solo", "area": "De Pijp",
                              "registration": True}]), encoding="utf-8")
    rc = main(["classify", str(p)])
    assert rc == 0
    assert "SHOW" in capsys.readouterr().out


def test_scan_subcommand_runs_with_no_sources(monkeypatch, tmp_path, capsys):
    # enabled_sources empty → scan does nothing, exits 0 (no network)
    monkeypatch.setenv("HOME_HUNT_DB", str(tmp_path / "s.sqlite"))
    monkeypatch.setenv("HOME_HUNT_BUDGET_DB", str(tmp_path / "b.sqlite"))   # isolate the budget DB
    rc = main(["scan", "--no-sources"])
    assert rc == 0
    assert "scanned" in capsys.readouterr().out.lower()


def test_usage_when_no_args(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()
