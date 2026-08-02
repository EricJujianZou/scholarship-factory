import pytest

from scholarship_factory.context import (
    ContextEntry,
    ContextKind,
    ContextStore,
    load_context_file,
)
from scholarship_factory.profile import (
    ApplicantProfile,
    ProfileStore,
    load_profile_file,
    save_profile,
)


def _write(tmp_path, text):
    path = tmp_path / "context.toml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_load_context_file_reads_every_section(tmp_path):
    path = _write(
        tmp_path,
        """
[[fact]]
title = "citizenship"
body = "Canadian citizen"

[[award]]
title = "Entrance Scholarship"
tags = ["merit"]

[[essay]]
title = "Why CS - 500 words"
body = "Full text here."
""",
    )

    entries = load_context_file(path)

    kinds = sorted(e.kind.value for e in entries)
    assert kinds == ["award", "essay", "fact"]
    award = next(e for e in entries if e.kind == ContextKind.AWARD)
    assert award.tags == ["merit"]


def test_unknown_section_names_the_valid_ones(tmp_path):
    path = _write(tmp_path, '[[hobbies]]\ntitle = "chess"\n')
    with pytest.raises(ValueError, match="hobbies"):
        load_context_file(path)


def test_reimport_updates_in_place_rather_than_duplicating(tmp_path):
    store = ContextStore(str(tmp_path / "t.db"))
    store.upsert(ContextEntry(kind=ContextKind.AWARD, title="A", body="first"))
    store.upsert(ContextEntry(kind=ContextKind.AWARD, title="A", body="second"))

    entries = store.list(ContextKind.AWARD)
    assert len(entries) == 1
    assert entries[0].body == "second"


def test_same_title_under_a_different_kind_is_a_different_entry(tmp_path):
    store = ContextStore(str(tmp_path / "t.db"))
    store.upsert(ContextEntry(kind=ContextKind.AWARD, title="Waterloo", body="award"))
    store.upsert(ContextEntry(kind=ContextKind.EDUCATION, title="Waterloo", body="degree"))

    assert len(store.list()) == 2


def test_tags_survive_the_round_trip(tmp_path):
    store = ContextStore(str(tmp_path / "t.db"))
    store.upsert(
        ContextEntry(kind=ContextKind.PROJECT, title="P", tags=["a", "b"])
    )
    assert store.list()[0].tags == ["a", "b"]


def test_facts_lookup_returns_title_to_body(tmp_path):
    store = ContextStore(str(tmp_path / "t.db"))
    store.upsert(ContextEntry(kind=ContextKind.FACT, title="citizenship", body="Canadian"))
    store.upsert(ContextEntry(kind=ContextKind.AWARD, title="Prize", body="ignored"))

    assert store.facts() == {"citizenship": "Canadian"}


def test_delete_removes_an_entry(tmp_path):
    store = ContextStore(str(tmp_path / "t.db"))
    entry = store.upsert(ContextEntry(kind=ContextKind.AWARD, title="A"))
    store.delete(entry.id)
    assert store.list() == []


def test_the_shipped_example_file_parses():
    """The file the owner copies must not be the thing that breaks the import."""
    entries = load_context_file("context.example.toml")
    assert {e.kind for e in entries} >= {
        ContextKind.FACT,
        ContextKind.EDUCATION,
        ContextKind.ESSAY,
        ContextKind.REFERENCE,
    }


def test_profile_section_is_not_an_unknown_section(tmp_path):
    """It shares the file; profile.py, not this module, is what reads it."""
    path = _write(tmp_path, '[profile]\nregion = "Canada"\n\n[[fact]]\ntitle = "x"\n')
    assert [e.title for e in load_context_file(path)] == ["x"]


def test_load_profile_file_reads_the_section(tmp_path):
    path = _write(
        tmp_path,
        '[profile]\nregion = "Canada"\neducation_level = "undergraduate"\n'
        'tags = ["software"]\n',
    )
    profile = load_profile_file(path)
    assert profile.region == "Canada"
    assert profile.education_level == "undergraduate"
    assert profile.tags == ["software"]


def test_a_file_without_a_profile_section_leaves_the_profile_alone(tmp_path):
    path = _write(tmp_path, '[[fact]]\ntitle = "citizenship"\n')
    assert load_profile_file(path) is None


def test_unknown_profile_field_names_the_valid_ones(tmp_path):
    path = _write(tmp_path, '[profile]\ngpa = "4.0"\n')
    with pytest.raises(ValueError, match="gpa"):
        load_profile_file(path)


def test_save_profile_updates_the_single_row_rather_than_adding_one(tmp_path):
    store = ProfileStore(str(tmp_path / "t.db"))
    first = save_profile(store, ApplicantProfile(region="Canada"))
    second = save_profile(store, ApplicantProfile(region="EU", bio="new"))

    assert len(store.list()) == 1
    assert second.id == first.id
    assert (second.region, second.bio) == ("EU", "new")


def test_the_shipped_example_profile_is_one_the_hard_filters_understand():
    """A region the filters cannot canonicalise silently filters nothing."""
    from scholarship_factory.rank import _EDUCATION_ALIASES, _REGION_ALIASES

    profile = load_profile_file("context.example.toml")
    assert profile.region.lower() in _REGION_ALIASES
    assert profile.education_level.lower() in _EDUCATION_ALIASES
