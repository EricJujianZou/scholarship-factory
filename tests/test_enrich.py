import json
from datetime import datetime, timedelta, timezone

from scholarship_factory.enrich import ats_facts, ats_ref, enrich_store
from scholarship_factory.extract import ExtractionResult, PageKind
from scholarship_factory.fetch import FetchResult
from scholarship_factory.logos import OrgLogoStore
from scholarship_factory.models import Opportunity, Provenance
from scholarship_factory.store import OpportunityStore

JOBPOSTING_HTML = """<html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "JobPosting", "title": "SWE Intern",
 "validThrough": "2026-09-30T23:59:59+00:00",
 "baseSalary": {"@type": "MonetaryAmount", "currency": "CAD",
   "value": {"@type": "QuantitativeValue", "minValue": 34, "maxValue": 41,
             "unitText": "HOUR"}},
 "hiringOrganization": {"@type": "Organization", "name": "Acme Robotics",
   "logo": "https://acme.example/logo.png"}}
</script></head><body>a page</body></html>"""

PLAIN_HTML = "<html><body>nothing structured here</body></html>"

LEVER_JSON = json.dumps(
    {
        "id": "aaaa",
        "salaryRange": {"min": 100000, "max": 150000, "currency": "USD", "interval": "per-year-salary"},
    }
)

ASHBY_JSON = json.dumps(
    {
        "apiVersion": "1",
        "jobs": [
            {"id": "other", "compensation": {"scrapeableCompensationSalarySummary": "$1"}},
            {
                "id": "bbbb-1111",
                "compensation": {
                    "compensationTierSummary": "$150K – $275K • Plus Equity",
                    "scrapeableCompensationSalarySummary": "$150K - $275K",
                },
            },
        ],
    }
)

GREENHOUSE_JSON = json.dumps(
    {
        "id": 123,
        "company_name": "Astranis",
        "application_deadline": "2026-10-15",
        "pay_input_ranges": [
            {
                "min_cents": 2900,
                "max_cents": 3400,
                "currency_type": "USD",
                "title": "Base Hourly Pay",
            }
        ],
    }
)


def _ok(url: str, body: str) -> FetchResult:
    return FetchResult(requested_url=url, final_url=url, status_code=200, body=body)


def _fail(url: str) -> FetchResult:
    return FetchResult(
        requested_url=url, final_url=url, status_code=None, body=None, error="boom"
    )


def _intern(apply_url, org="Acme Robotics", title="SWE Intern", **kwargs):
    return Opportunity(
        title=title,
        apply_url=apply_url,
        source_url="https://src.example/listings",
        type="internship",
        organization=org,
        **kwargs,
    )


def _store(tmp_path, *opps):
    store = OpportunityStore(str(tmp_path / "t.db"))
    return store, [store.insert(o) for o in opps]


class CountingFetch:
    def __init__(self, pages: dict[str, str], fail: set[str] = frozenset()):
        self.pages = pages
        self.fail = fail
        self.urls: list[str] = []

    def __call__(self, url: str) -> FetchResult:
        self.urls.append(url)
        if url in self.fail or url not in self.pages:
            return _fail(url)
        return _ok(url, self.pages[url])


# --- ATS url recognition -----------------------------------------------------

def test_ats_ref_recognizes_lever_ashby_greenhouse():
    lever = ats_ref("https://jobs.lever.co/waabi/aaaa/apply")
    assert lever.kind == "lever"
    assert lever.api_url == "https://api.lever.co/v0/postings/waabi/aaaa"

    ashby = ats_ref("https://jobs.ashbyhq.com/etched/bbbb-1111/application")
    assert ashby.kind == "ashby"
    assert ashby.api_url == (
        "https://api.ashbyhq.com/posting-api/job-board/etched?includeCompensation=true"
    )
    assert ashby.job_id == "bbbb-1111"

    for host in ("boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"):
        gh = ats_ref(f"https://{host}/astranis/jobs/4601135006")
        assert gh.kind == "greenhouse"
        assert gh.api_url == (
            "https://boards-api.greenhouse.io/v1/boards/astranis/jobs/"
            "4601135006?pay_transparency=true"
        )

    assert ats_ref("https://careers.acme.example/job/1") is None
    assert ats_ref("https://jobs.lever.co/onlyorg") is None


def test_ats_facts_absent_fields_are_absent_facts():
    ref = ats_ref("https://jobs.lever.co/waabi/aaaa/apply")
    facts = ats_facts(ref, json.dumps({"id": "aaaa", "salaryRange": None}))
    assert facts.pay is None and facts.deadline is None
    assert ats_facts(ref, "not json").pay is None


# --- stage: JSON-LD JobPosting ----------------------------------------------

def test_jsonld_page_fills_pay_deadline_and_logo(tmp_path):
    url = "https://careers.acme.example/job/1"
    store, [opp] = _store(tmp_path, _intern(url))
    fetch = CountingFetch({url: JOBPOSTING_HTML})

    report = enrich_store(store, fetch_fn=fetch)

    fresh = store.get(opp.id)
    assert fresh.reward == "34–41 CAD per hour"
    assert fresh.reward_provenance == Provenance.QUOTED
    assert "baseSalary" in fresh.reward_source
    # validThrough is a posting expiry, recorded honestly as derived
    assert fresh.deadline == "2026-09-30"
    assert fresh.deadline_provenance == Provenance.DERIVED
    assert "validThrough" in fresh.deadline_source
    assert OrgLogoStore(store.db_path).get("Acme Robotics") == "https://acme.example/logo.png"
    assert report.outcomes == {"filled": 1}
    assert report.filled("pay") == 1 and report.filled("deadline") == 1
    assert report.filled("logo") == 1


def test_page_og_image_fills_the_logo_when_there_is_no_jsonld(tmp_path):
    url = "https://job-boards.greenhouse.io/mcghealth/jobs/8350486002"
    api = "https://boards-api.greenhouse.io/v1/boards/mcghealth/jobs/8350486002?pay_transparency=true"
    logo = (
        "https://s2-recruiting.cdn.greenhouse.io/external_greenhouse_job_boards"
        "/logos/400/621/800/original/MCG-Logo.png"
    )
    page = f'<html><head><meta property="og:image" content="{logo}"/></head></html>'
    store, [opp] = _store(tmp_path, _intern(url, org="MCG Health"))
    fetch = CountingFetch({api: "{}", url: page})

    report = enrich_store(store, fetch_fn=fetch)

    assert OrgLogoStore(store.db_path).get("MCG Health") == logo
    assert report.fills["page"] == {"logo": 1}
    # the page states no pay or deadline, and none was invented
    assert store.get(opp.id).reward is None


def test_one_page_logo_covers_the_org_so_siblings_are_not_fetched(tmp_path):
    logo = "https://lever-client-logos.s3.amazonaws.com/palantir.png"
    page = f'<html><head><meta property="og:image" content="{logo}"/></head></html>'
    first = "https://jobs.lever.co/palantir/aaaa"
    second = "https://jobs.lever.co/palantir/bbbb"
    store, _ = _store(
        tmp_path,
        _intern(first, org="Palantir", reward="$50/hr", reward_provenance=Provenance.QUOTED,
                reward_source="$50/hr", deadline="2026-10-01",
                deadline_provenance=Provenance.QUOTED, deadline_source="2026-10-01"),
        _intern(second, org="Palantir", reward="$50/hr", reward_provenance=Provenance.QUOTED,
                reward_source="$50/hr", deadline="2026-10-01",
                deadline_provenance=Provenance.QUOTED, deadline_source="2026-10-01"),
    )
    fetch = CountingFetch({first: page, second: page})

    report = enrich_store(store, fetch_fn=fetch)

    assert report.filled("logo") == 1
    # the second row's only gap was its org's logo, which the first row closed
    assert fetch.urls == [first]


# --- stage: ATS endpoints ----------------------------------------------------

def test_lever_api_fills_pay(tmp_path):
    url = "https://jobs.lever.co/waabi/aaaa/apply"
    api = "https://api.lever.co/v0/postings/waabi/aaaa"
    store, [opp] = _store(tmp_path, _intern(url, org="Waabi"))
    fetch = CountingFetch({api: LEVER_JSON, url: PLAIN_HTML})

    report = enrich_store(store, fetch_fn=fetch)

    fresh = store.get(opp.id)
    assert fresh.reward == "100,000–150,000 USD per year salary"
    assert fresh.reward_provenance == Provenance.QUOTED
    assert "salaryRange" in fresh.reward_source
    assert fresh.deadline is None
    assert fresh.deadline_provenance == Provenance.NONE
    assert report.fills["ats"]["pay"] == 1


def test_ashby_board_fills_pay_for_matching_job(tmp_path):
    url = "https://jobs.ashbyhq.com/etched/bbbb-1111/application"
    api = "https://api.ashbyhq.com/posting-api/job-board/etched?includeCompensation=true"
    store, [opp] = _store(tmp_path, _intern(url, org="Etched"))
    fetch = CountingFetch({api: ASHBY_JSON, url: PLAIN_HTML})

    enrich_store(store, fetch_fn=fetch)

    fresh = store.get(opp.id)
    assert fresh.reward == "$150K - $275K"
    assert fresh.reward_provenance == Provenance.QUOTED


def test_greenhouse_api_fills_pay_and_stated_deadline(tmp_path):
    url = "https://job-boards.greenhouse.io/astranis/jobs/4601135006"
    api = (
        "https://boards-api.greenhouse.io/v1/boards/astranis/jobs/"
        "4601135006?pay_transparency=true"
    )
    store, [opp] = _store(tmp_path, _intern(url, org="Astranis"))
    fetch = CountingFetch({api: GREENHOUSE_JSON, url: PLAIN_HTML})

    enrich_store(store, fetch_fn=fetch)

    fresh = store.get(opp.id)
    assert fresh.reward == "$29.00–$34.00 USD (Base Hourly Pay)"
    assert fresh.reward_provenance == Provenance.QUOTED
    # application_deadline is a stated deadline, unlike validThrough
    assert fresh.deadline == "2026-10-15"
    assert fresh.deadline_provenance == Provenance.QUOTED
    assert "application_deadline" in fresh.deadline_source


def test_zero_salaries_are_placeholders_not_pay(tmp_path):
    # seen live on amd.com: JSON-LD baseSalary of 0 USD; Lever/Greenhouse
    # zero ranges mean the same "not stated"
    zero_jsonld = JOBPOSTING_HTML.replace(
        '"minValue": 34, "maxValue": 41', '"minValue": 0, "maxValue": 0'
    )
    url = "https://careers.acme.example/job/zero"
    store, [opp] = _store(tmp_path, _intern(url))
    enrich_store(store, fetch_fn=CountingFetch({url: zero_jsonld}))
    fresh = store.get(opp.id)
    assert fresh.reward is None
    assert fresh.reward_provenance == Provenance.NONE

    lever = ats_ref("https://jobs.lever.co/waabi/aaaa/apply")
    zero_range = json.dumps({"salaryRange": {"min": 0, "max": 0, "currency": "USD"}})
    assert ats_facts(lever, zero_range).pay is None

    gh = ats_ref("https://boards.greenhouse.io/x/jobs/1")
    zero_cents = json.dumps(
        {"pay_input_ranges": [{"min_cents": 0, "max_cents": 0, "currency_type": "USD"}]}
    )
    assert ats_facts(gh, zero_cents).pay is None


# --- honesty: empty pages stay empty ----------------------------------------

def test_page_with_nothing_leaves_row_null_and_valid(tmp_path):
    url = "https://careers.acme.example/job/2"
    store, [opp] = _store(tmp_path, _intern(url))
    fetch = CountingFetch({url: PLAIN_HTML})

    report = enrich_store(store, fetch_fn=fetch)

    fresh = store.get(opp.id)  # round-trips through the provenance validator
    assert fresh.reward is None and fresh.reward_provenance == Provenance.NONE
    assert fresh.deadline is None and fresh.deadline_provenance == Provenance.NONE
    assert report.outcomes == {"no_fact": 1}


def test_unreachable_page_is_recorded(tmp_path):
    url = "https://careers.acme.example/job/3"
    store, _ = _store(tmp_path, _intern(url))
    fetch = CountingFetch({}, fail={url})

    report = enrich_store(store, fetch_fn=fetch)

    assert report.outcomes == {"unreachable": 1}


# --- ledger + budget ---------------------------------------------------------

def test_ledger_prevents_refetch_inside_window_and_allows_after(tmp_path):
    url = "https://careers.acme.example/job/4"
    store, _ = _store(tmp_path, _intern(url))
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)

    fetch = CountingFetch({url: PLAIN_HTML})
    enrich_store(store, fetch_fn=fetch, now=now)
    assert len(fetch.urls) == 1

    again = CountingFetch({url: PLAIN_HTML})
    report = enrich_store(store, fetch_fn=again, now=now + timedelta(days=1))
    assert again.urls == []
    assert report.rows_skipped_recent == 1

    later = CountingFetch({url: PLAIN_HTML})
    report = enrich_store(store, fetch_fn=later, now=now + timedelta(days=8))
    assert len(later.urls) == 1
    assert report.rows_skipped_recent == 0


def test_page_cap_bounds_network_fetches(tmp_path):
    urls = [f"https://careers.acme.example/job/{i}" for i in range(3)]
    store, _ = _store(
        tmp_path, *[_intern(u, title=f"Intern {i}") for i, u in enumerate(urls)]
    )
    fetch = CountingFetch({u: PLAIN_HTML for u in urls})

    report = enrich_store(store, fetch_fn=fetch, page_cap=2)

    assert report.fetches == 2
    assert report.rows_attempted == 2
    assert report.cap_reached is True


def test_priority_canada_then_marquee_then_newest(tmp_path):
    store, _ = _store(
        tmp_path,
        _intern("https://x.example/us", org="Small Co",
                description="SWE internship. Location: NYC"),
        _intern("https://x.example/marquee", org="NVIDIA",
                description="SWE internship. Location: Santa Clara, CA"),
        _intern("https://x.example/ca", org="Tiny Co",
                description="SWE internship. Location: Toronto, ON, Canada"),
    )
    fetch = CountingFetch({})

    enrich_store(store, fetch_fn=fetch, page_cap=2)

    assert fetch.urls == ["https://x.example/ca", "https://x.example/marquee"]


# --- LLM stage ---------------------------------------------------------------

def _llm_result(source_url):
    return ExtractionResult(
        kind=PageKind.DETAIL,
        opportunities=[
            Opportunity(
                title="SWE Intern",
                apply_url=source_url,
                source_url=source_url,
                reward="$40/hr",
                reward_provenance=Provenance.QUOTED,
                reward_source="$40/hr",
                deadline="October 1, 2026",
                deadline_provenance=Provenance.QUOTED,
                deadline_source="Apply by October 1, 2026",
            )
        ],
    )


def test_llm_fills_only_what_the_ladder_left_and_respects_cap(tmp_path):
    urls = [f"https://careers.acme.example/llm/{i}" for i in range(2)]
    store, _ = _store(
        tmp_path, *[_intern(u, title=f"Intern {i}") for i, u in enumerate(urls)]
    )
    fetch = CountingFetch({u: PLAIN_HTML for u in urls})
    calls = []

    def extract_fn(body, url):
        calls.append(url)
        return _llm_result(url)

    report = enrich_store(store, fetch_fn=fetch, extract_fn=extract_fn, llm_cap=1)

    assert len(calls) == 1
    assert report.llm_calls == 1
    assert report.fills["llm"] == {"pay": 1, "deadline": 1}
    filled = [o for o in store.list() if o.reward is not None]
    assert len(filled) == 1
    assert filled[0].reward == "$40/hr"
    assert filled[0].deadline_provenance == Provenance.QUOTED


def test_no_llm_provider_is_skipped_gracefully(tmp_path):
    url = "https://careers.acme.example/job/9"
    store, _ = _store(tmp_path, _intern(url))
    fetch = CountingFetch({url: PLAIN_HTML})
    lines = []

    report = enrich_store(store, fetch_fn=fetch, extract_fn=None, log=lines.append)

    assert report.llm_skipped_reason is not None
    assert any("LLM stage skipped" in line for line in lines)
    assert report.outcomes == {"no_fact": 1}


# --- scoping -----------------------------------------------------------------

def test_non_internship_rows_and_complete_rows_are_left_alone(tmp_path):
    scholarship = Opportunity(
        title="Award",
        apply_url="https://uw.example/award",
        source_url="https://src.example",
        type="scholarship",
    )
    done = _intern(
        "https://x.example/done",
        reward="$1",
        reward_provenance=Provenance.QUOTED,
        reward_source="$1",
        deadline="2026-01-01",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="2026-01-01",
    )
    store, _ = _store(tmp_path, scholarship, done)
    OrgLogoStore(store.db_path).set("Acme Robotics", "https://acme.example/logo.png")
    fetch = CountingFetch({})

    report = enrich_store(store, fetch_fn=fetch)

    assert fetch.urls == []
    assert report.rows_considered == 0
