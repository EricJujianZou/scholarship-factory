import os
import tempfile

from scholarship_factory.profile import ApplicantProfile, ProfileStore


def _temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_defaults_and_all_optional_null():
    p = ApplicantProfile()
    assert p.owner == "me"
    assert p.tags == []
    assert p.region is None and p.education_level is None and p.field_of_study is None
    assert p.bio is None


def test_store_round_trip_including_tags():
    store = ProfileStore(_temp_db())
    p = ApplicantProfile(
        region="Ontario, CA",
        education_level="undergraduate",
        field_of_study="computer science",
        tags=["women-in-stem", "canadian", "first-gen"],
        bio="Third-year CS student.",
    )
    saved = store.insert(p)
    assert saved.created_at is not None and saved.updated_at is not None

    fetched = store.get(p.id)
    assert fetched is not None
    assert fetched.tags == ["women-in-stem", "canadian", "first-gen"]
    assert fetched.region == "Ontario, CA"
    assert fetched.owner == "me"
    assert [x.id for x in store.list()] == [p.id]


def test_update_refreshes_updated_at_only():
    store = ProfileStore(_temp_db())
    saved = store.insert(ApplicantProfile(bio="old", tags=["a"]))

    saved.bio = "new"
    saved.tags = ["a", "b"]
    updated = store.update(saved)

    assert updated.bio == "new"
    assert updated.tags == ["a", "b"]
    assert updated.created_at == saved.created_at  # unchanged
    assert updated.updated_at >= saved.updated_at
