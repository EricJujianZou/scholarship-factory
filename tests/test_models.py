import pytest
from pydantic import ValidationError

from scholarship_factory import Opportunity, Provenance


def test_null_deadline_with_none_provenance_is_valid():
    opp = Opportunity(
        title="Test Scholarship",
        apply_url="https://example.com/apply",
        source_url="https://example.com/apply",
        deadline=None,
        deadline_provenance="none",
    )
    assert opp.deadline is None
    assert opp.deadline_provenance == Provenance.NONE


def test_defaults():
    opp = Opportunity(
        title="Test Scholarship",
        apply_url="https://example.com/apply",
        source_url="https://example.com/apply",
    )
    assert opp.owner == "me"
    assert opp.status == "new"
    assert opp.deadline_provenance == Provenance.NONE


def test_invalid_provenance_raises():
    with pytest.raises(ValidationError):
        Opportunity(
            title="Test Scholarship",
            apply_url="https://example.com/apply",
            source_url="https://example.com/apply",
            deadline_provenance="confident",
        )


def test_quoted_deadline_with_source_is_valid():
    opp = Opportunity(
        title="Test Scholarship",
        apply_url="https://example.com/apply",
        source_url="https://example.com/apply",
        deadline="2026-07-01",
        deadline_provenance="quoted",
        deadline_source="Applications close July 1, 2026",
    )
    assert opp.deadline_source == "Applications close July 1, 2026"


def test_quoted_deadline_without_source_raises():
    with pytest.raises(ValidationError):
        Opportunity(
            title="Test Scholarship",
            apply_url="https://example.com/apply",
            source_url="https://example.com/apply",
            deadline="2026-07-01",
            deadline_provenance="quoted",
            deadline_source=None,
        )
