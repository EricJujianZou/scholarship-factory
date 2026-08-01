from datetime import date

from scholarship_factory.digest import RunStore, build_digest, render
from scholarship_factory.feedback import Decision, DecisionVerdict
from scholarship_factory.models import Opportunity
from scholarship_factory.profile import ApplicantProfile

TODAY = date(2026, 8, 1)


def _opp(title, *, first_seen="2026-08-01T00:00:00+00:00", **kwargs):
    kwargs.setdefault("apply_url", f"https://e.com/{title}")
    kwargs.setdefault("source_url", "https://e.com")
    opp = Opportunity(title=title, **kwargs)
    return opp.model_copy(update={"first_seen": first_seen})


def test_new_items_are_those_first_seen_since_the_last_digest():
    old = _opp("Old", first_seen="2026-07-01T00:00:00+00:00")
    fresh = _opp("Fresh", first_seen="2026-07-30T00:00:00+00:00")

    digest = build_digest(
        [old, fresh],
        ApplicantProfile(),
        since="2026-07-15T00:00:00+00:00",
        today=TODAY,
    )

    assert [i.title for i in digest.new_items] == ["Fresh"]
    assert digest.total_eligible == 2


def test_first_run_with_no_since_reports_everything_as_new():
    digest = build_digest([_opp("A"), _opp("B")], ApplicantProfile(), today=TODAY)
    assert len(digest.new_items) == 2


def test_new_items_are_ordered_by_fit():
    a, b = _opp("A"), _opp("B")
    digest = build_digest(
        [a, b],
        ApplicantProfile(),
        fits={a.id: ("low", "far"), b.id: ("high", "close")},
        today=TODAY,
    )
    assert [i.title for i in digest.new_items] == ["B", "A"]


def test_closing_soon_covers_the_horizon_and_reports_days_left():
    soon = _opp("Soon", deadline="August 10, 2026")
    later = _opp("Later", deadline="December 1, 2026")

    digest = build_digest([soon, later], ApplicantProfile(), today=TODAY)

    assert [i.title for i in digest.closing_soon] == ["Soon"]
    assert digest.closing_soon[0].days_left == 9


def test_decided_opportunities_do_not_nag():
    soon = _opp("Soon", deadline="August 10, 2026")
    decisions = [
        Decision(opportunity_id=soon.id, verdict=DecisionVerdict.NOT_INTERESTED)
    ]

    digest = build_digest(
        [soon], ApplicantProfile(), decisions=decisions, today=TODAY
    )

    assert digest.closing_soon == []
    assert digest.undecided == 0


def test_expired_deadline_is_not_closing_soon():
    past = _opp("Past", deadline="July 1, 2026")
    digest = build_digest([past], ApplicantProfile(), today=TODAY)
    assert digest.closing_soon == []


def test_render_says_so_when_there_is_nothing():
    digest = build_digest([], ApplicantProfile(), today=TODAY)
    text = render(digest)
    assert "Nothing new" in text
    assert "0 eligible in total" in text


def test_render_includes_fit_reason_and_link():
    opp = _opp("Award", deadline="August 5, 2026")
    digest = build_digest(
        [opp],
        ApplicantProfile(),
        fits={opp.id: ("high", "matches your field")},
        today=TODAY,
    )

    text = render(digest)
    assert "HIGH" in text
    assert "matches your field" in text
    assert opp.apply_url in text
    assert "due 2026-08-05 (4d)" in text


def test_run_store_marks_and_reads_back(tmp_path):
    store = RunStore(str(tmp_path / "t.db"))
    assert store.last_digest_at() is None

    stamped = store.mark("2026-08-01T12:00:00+00:00")
    assert store.last_digest_at() == stamped

    store.mark("2026-08-02T12:00:00+00:00")
    assert store.last_digest_at() == "2026-08-02T12:00:00+00:00"
