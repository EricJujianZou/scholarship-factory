import os

import pytest

from scholarship_factory import env as env_module
from scholarship_factory.env import load_env, parse_env


@pytest.fixture(autouse=True)
def forget_applied_keys():
    """Each test starts with no memory of keys a previous one supplied."""
    env_module._APPLIED.clear()
    yield
    env_module._APPLIED.clear()


def test_parses_keys_values_and_ignores_comments_and_blanks():
    parsed = parse_env('# a comment\n\nGEMINI_API_KEY="abc"\nOTHER = plain \n')
    assert parsed == {"GEMINI_API_KEY": "abc", "OTHER": "plain"}


def test_a_missing_file_is_not_an_error(tmp_path):
    assert load_env(tmp_path / "nope.env") == {}


def test_loading_sets_the_key_in_the_environment(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY="from-file"\n', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert load_env(path) == {"GEMINI_API_KEY": "from-file"}
    assert os.environ["GEMINI_API_KEY"] == "from-file"


def test_a_real_environment_variable_wins_over_the_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY="from-file"\n', encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "from-shell")

    assert load_env(path) == {}
    assert os.environ["GEMINI_API_KEY"] == "from-shell"


def test_reloading_picks_up_a_key_corrected_after_start_up(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path.write_text('GEMINI_API_KEY="typo"\n', encoding="utf-8")
    load_env(path)

    path.write_text('GEMINI_API_KEY="corrected"\n', encoding="utf-8")
    assert load_env(path, reload=True) == {"GEMINI_API_KEY": "corrected"}
    assert os.environ["GEMINI_API_KEY"] == "corrected"


def test_reloading_still_leaves_a_shell_variable_alone(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY="from-file"\n', encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "from-shell")

    assert load_env(path, reload=True) == {}
    assert os.environ["GEMINI_API_KEY"] == "from-shell"


def test_a_first_load_never_overrides_even_a_key_it_set_before(tmp_path, monkeypatch):
    """Without `reload`, the file only ever fills a gap."""
    path = tmp_path / ".env"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path.write_text('GEMINI_API_KEY="first"\n', encoding="utf-8")
    load_env(path)

    path.write_text('GEMINI_API_KEY="second"\n', encoding="utf-8")
    assert load_env(path) == {}
    assert os.environ["GEMINI_API_KEY"] == "first"


def test_the_unfilled_placeholder_does_not_count_as_a_key(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY=""\n', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert load_env(path) == {}
    assert "GEMINI_API_KEY" not in os.environ
