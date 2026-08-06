from scholarship_factory.models import Opportunity
from scholarship_factory.site import build_site, load_site_config
from scholarship_factory.store import OpportunityStore


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
