from scholarship_factory.logos import OrgLogoStore
from scholarship_factory.models import Opportunity, Provenance
from scholarship_factory.site import (
    KNOWN_TYPES,
    build_site,
    load_site_config,
    splice_site_data,
)
from scholarship_factory.store import OpportunityStore


def _rows_of(html):
    import json

    data = html.split('<script id="data" type="application/json">')[1]
    return json.loads(data.split("</script>")[0])


def _h1(html):
    return html.split("<h1>")[1].split("</h1>")[0]


def _store_with(tmp_path, *opps):
    store = OpportunityStore(str(tmp_path / "t.db"))
    for opp in opps:
        store.insert(opp)
    return store


def _opp(title, apply_url="https://example.com/a", **kwargs):
    kwargs.setdefault("source_url", "https://example.com")
    return Opportunity(title=title, apply_url=apply_url, **kwargs)


def test_build_embeds_rows_and_is_self_contained(tmp_path):
    store = _store_with(
        tmp_path,
        _opp("SWE Intern", organization="Example Corp", type="internship"),
        _opp("Waterloo Award", apply_url="https://uw.ca/award", type="scholarship"),
    )

    index = build_site(store, tmp_path / "site")

    html = index.read_text(encoding="utf-8")
    assert "SWE Intern" in html
    assert "Waterloo Award" in html
    assert "Example Corp" in html
    # self-contained: no external scripts, styles or fetches
    assert "http" not in html.split("<style>")[1].split("</style>")[0]
    assert 'src="http' not in html


def test_script_closing_tag_in_title_cannot_break_out(tmp_path):
    store = _store_with(tmp_path, _opp("</script><script>alert(1)</script>"))

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    import json

    data = html.split('<script id="data" type="application/json">')[1]
    data = data.split("</script>")[0]
    # the split above found the real closing tag, so the payload held no raw
    # "</script>" of its own; the escaped form survives and parses back intact
    assert "<\\/script>" in data
    [row] = json.loads(data)
    assert row["title"] == "</script><script>alert(1)</script>"


def test_non_http_apply_url_is_dropped(tmp_path):
    store = _store_with(
        tmp_path,
        _opp("Evil", apply_url="javascript:alert(1)"),
        _opp("Fine", apply_url="https://ok.example.com/x"),
    )

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    assert "javascript:alert(1)" not in html
    assert "Fine" in html


def test_cta_degrades_from_stripe_to_dm_to_muted(tmp_path):
    store = _store_with(tmp_path, _opp("A"))

    with_stripe = build_site(
        store, tmp_path / "s1", config={"stripe_url": "https://buy.stripe.com/x"}
    ).read_text(encoding="utf-8")
    assert "buy.stripe.com" in with_stripe

    with_ig = build_site(
        store, tmp_path / "s2", config={"instagram": "sleppyeric"}
    ).read_text(encoding="utf-8")
    assert "instagram.com/sleppyeric" in with_ig

    bare = build_site(store, tmp_path / "s3").read_text(encoding="utf-8")
    assert "DM me to start" in bare


def test_email_form_absent_without_action(tmp_path):
    store = _store_with(tmp_path, _opp("A"))
    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")
    assert "<form" not in html


def test_simplify_source_is_credited(tmp_path):
    store = _store_with(
        tmp_path,
        _opp(
            "Intern",
            source_url="https://raw.githubusercontent.com/SimplifyJobs/x/listings.json",
        ),
    )
    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")
    assert "Simplify (github.com/SimplifyJobs)" in html


def test_unknown_types_collapse_to_other(tmp_path):
    import json

    store = _store_with(
        tmp_path,
        _opp("A", type="Master's Scholarship and Internship Programme"),
        _opp("B", apply_url="https://example.com/b", type="Fellowship"),
        _opp("C", apply_url="https://example.com/c", type=None),
    )

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    data = html.split('<script id="data" type="application/json">')[1]
    data = data.split("</script>")[0]
    types = sorted(r["type"] for r in json.loads(data))
    assert types == ["fellowship", "other", "other"]


def test_missing_config_file_is_empty(tmp_path):
    assert load_site_config(tmp_path / "nope.toml") == {}


def test_headline_never_names_a_type_the_rows_do_not_have(tmp_path):
    store = _store_with(
        tmp_path,
        *[
            _opp(f"S{i}", apply_url=f"https://uw.ca/s{i}", type="scholarship")
            for i in range(25)
        ],
        *[
            _opp(f"I{i}", apply_url=f"https://ex.com/i{i}", type="internship")
            for i in range(3)
        ],
    )

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    h1 = _h1(html)
    present = {r["type"] for r in _rows_of(html)}
    for t in KNOWN_TYPES:
        if t in h1:
            assert t in present, f"h1 names {t!r} but no row has it"
    # only the type that cleared the volume floor gets named
    assert "scholarship" in h1
    assert "internship" not in h1
    assert "hackathon" not in h1
    # the small ones are still accounted for, with real counts
    assert "3 internships" in html


def test_headline_names_nothing_when_no_type_has_volume(tmp_path):
    store = _store_with(tmp_path, _opp("A", type="internship"))

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    h1 = _h1(html)
    assert h1 == "Everything we can find, in one searchable list."
    for t in KNOWN_TYPES:
        assert t not in h1


def test_term_and_location_parsed_out_of_the_description(tmp_path):
    store = _store_with(
        tmp_path,
        _opp(
            "SWE Intern",
            type="internship",
            description=(
                "Software Engineering internship. "
                "Term: Summer 2027, Fall 2027. Location: Toronto, ON, Canada"
            ),
        ),
        _opp(
            "Term only",
            apply_url="https://example.com/b",
            description="Hardware internship. Term: Winter 2026",
        ),
        _opp(
            "Prose",
            apply_url="https://example.com/c",
            description="A grant for journalists reporting on anything.",
        ),
    )

    rows = {r["title"]: r for r in _rows_of(
        build_site(store, tmp_path / "site").read_text(encoding="utf-8")
    )}

    assert rows["SWE Intern"]["term"] == ["Summer 2027", "Fall 2027"]
    # "Toronto, ON, Canada" is one place, not three
    assert rows["SWE Intern"]["loc"] == "Toronto, ON, Canada"
    assert rows["Term only"]["term"] == ["Winter 2026"]
    assert rows["Term only"]["loc"] == ""
    assert rows["Prose"]["term"] == []
    assert rows["Prose"]["loc"] == ""


def test_facts_separate_build_date_from_newest_listing(tmp_path):
    store = _store_with(tmp_path, _opp("A"))

    html = build_site(store, tmp_path / "site").read_text(encoding="utf-8")

    assert "built" in html
    assert "newest listing" in html
    newest = max(r["seen"] for r in _rows_of(html))
    assert newest in html


def test_rows_carry_pay_for_internships_and_logo_from_the_org_table(tmp_path):
    store = _store_with(
        tmp_path,
        _opp(
            "SWE Intern",
            type="internship",
            organization="Acme Robotics",
            reward="$34–$41 CAD/hr",
            reward_provenance=Provenance.QUOTED,
            reward_source="$34–$41 CAD/hr",
        ),
        _opp(
            "Award",
            apply_url="https://uw.ca/award",
            type="scholarship",
            organization="UW",
            reward="$5,000",
            reward_provenance=Provenance.QUOTED,
            reward_source="$5,000",
        ),
        _opp("No facts", apply_url="https://x.ca/b", type="internship"),
    )
    OrgLogoStore(store.db_path).set("Acme Robotics", "https://acme.example/logo.png")

    rows = {r["title"]: r for r in _rows_of(
        build_site(store, tmp_path / "site").read_text(encoding="utf-8")
    )}

    assert rows["SWE Intern"]["pay"] == "$34–$41 CAD/hr"
    assert rows["SWE Intern"]["logo"] == "https://acme.example/logo.png"
    # a scholarship's reward is not a wage; the pay pill stays off
    assert rows["Award"]["pay"] is None
    assert rows["No facts"]["pay"] is None
    assert rows["No facts"]["logo"] is None


def _deploy_fixture(tmp_path, data=b"[]"):
    # a hand-maintained page: CRLF lines, bespoke markup, one data line
    raw = (
        b"<!doctype html>\r\n<html>\r\n<head><title>UGMI</title></head>\r\n"
        b"<body>\r\n<p>hand-crafted \xe2\x80\x94 do not regenerate</p>\r\n"
        b'<script id="data" type="application/json">' + data + b"</script>\r\n"
        b"<script>const ROWS = JSON.parse(document.getElementById('data').textContent);</script>\r\n"
        b"</body>\r\n</html>\r\n"
    )
    path = tmp_path / "index.html"
    path.write_bytes(raw)
    return path, raw


def test_splice_replaces_only_the_data_line(tmp_path):
    import json

    store = _store_with(
        tmp_path,
        _opp(
            "SWE Intern",
            type="internship",
            organization="Acme",
            reward="$40/hr",
            reward_provenance=Provenance.QUOTED,
            reward_source="$40/hr",
        ),
    )
    path, before = _deploy_fixture(tmp_path, data=b'[{"title": "old"}]')

    count = splice_site_data(path, store)

    after = path.read_bytes()
    open_marker = b'<script id="data" type="application/json">'
    prefix_end = before.index(open_marker) + len(open_marker)
    # every byte outside the payload is untouched, CRLFs included
    assert after[:prefix_end] == before[:prefix_end]
    assert after[after.index(b"</script>", prefix_end):] == before[before.index(b"</script>", prefix_end):]
    payload = after[prefix_end:after.index(b"</script>", prefix_end)]
    [row] = json.loads(payload.decode("utf-8"))
    assert count == 1
    assert row["title"] == "SWE Intern"
    assert row["pay"] == "$40/hr"
    assert "soon" in row and "due" in row


def test_splice_refuses_a_file_without_the_marker(tmp_path):
    import pytest

    store = _store_with(tmp_path, _opp("A"))
    rogue = tmp_path / "other.html"
    rogue.write_text("<html><body>no data line</body></html>", encoding="utf-8")

    with pytest.raises(ValueError):
        splice_site_data(rogue, store)


def test_dm_path_uses_the_message_deep_link(tmp_path):
    store = _store_with(tmp_path, _opp("A"))

    html = build_site(
        store,
        tmp_path / "site",
        config={"stripe_url": "https://buy.stripe.com/x", "instagram": "sleppyeric"},
    ).read_text(encoding="utf-8")

    assert "https://ig.me/m/sleppyeric" in html
    # the suggested opener ships with the link, not as an exercise for the reader
    assert "I want the weekly list" in html


def test_retired_sources_never_reach_an_export(tmp_path):
    from scholarship_factory.site import export_rows

    store = _store_with(
        tmp_path,
        _opp("SWE Intern", type="internship"),
        _opp(
            "Old Regional Award",
            apply_url="https://example.org/award",
            source_url="https://opportunitydesk.org/2026/08/05/x/",
        ),
    )

    rows = export_rows(
        store, config={"retired_sources": ["opportunitydesk.org"]}
    )

    assert [r["title"] for r in rows] == ["SWE Intern"]
