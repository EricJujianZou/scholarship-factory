import os
import tempfile

from scholarship_factory import cli
from scholarship_factory.cli import main
from scholarship_factory.extract import ExtractionResult, PageKind
from scholarship_factory.fetch import FetchResult
from scholarship_factory.models import Opportunity
from scholarship_factory.store import OpportunityStore


def _seeded_db() -> tuple[str, str]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = OpportunityStore(path)
    opp = store.insert(
        Opportunity(
            title="Test Grant",
            apply_url="https://example.com/apply",
            source_url="https://example.com",
            status="new",
        )
    )
    return path, opp.id


def test_list_prints_stored(capsys):
    path, opp_id = _seeded_db()
    rc = main(["list", "--db", path])
    out = capsys.readouterr().out
    assert rc == 0
    assert opp_id in out
    assert "Test Grant" in out


def test_list_status_filter_and_empty(capsys):
    path, _ = _seeded_db()
    rc = main(["list", "--db", path, "--status", "archived"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == ""  # no rows match


def test_show_found_includes_provenance(capsys):
    path, opp_id = _seeded_db()
    rc = main(["show", opp_id, "--db", path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "deadline_provenance:" in out
    assert "deadline_source:" in out
    assert "Test Grant" in out


def test_show_not_found_exits_nonzero(capsys):
    path, _ = _seeded_db()
    rc = main(["show", "does-not-exist", "--db", path])
    err = capsys.readouterr().err
    assert rc == 1
    assert "not found" in err


def _write_toml(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".toml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_source_prints_summary(capsys, monkeypatch, tmp_path):
    seeds_path = _write_toml(
        """
[[seeds]]
type = "url"
value = "https://example.com/a"

[[seeds]]
type = "instagram"
value = "somepage"
"""
    )

    def fake_fetch(url: str) -> FetchResult:
        return FetchResult(requested_url=url, final_url=url, status_code=200, body="<html></html>")

    def fake_extract(body: str, url: str) -> ExtractionResult:
        return ExtractionResult(kind=PageKind.DETAIL, opportunities=[])

    monkeypatch.setattr(cli, "fetch_url", fake_fetch)
    monkeypatch.setattr(cli, "extract", fake_extract)

    rc = main(["source", "--seeds", seeds_path, "--db", str(tmp_path / "t.db")])
    out = capsys.readouterr().out

    assert rc == 0
    assert "targets attempted: 1" in out
    assert "skipped: 1" in out
