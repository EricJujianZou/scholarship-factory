import os

from scholarship_factory.env import load_env, parse_env


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


def test_the_unfilled_placeholder_does_not_count_as_a_key(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('GEMINI_API_KEY=""\n', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert load_env(path) == {}
    assert "GEMINI_API_KEY" not in os.environ
