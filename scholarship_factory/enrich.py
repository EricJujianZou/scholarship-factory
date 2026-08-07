"""Post-import enrichment pass (GH-53): pay + deadline + org logo.

Simplify's listings JSON publishes no pay, no deadline and no logo; those
facts live on the posting page behind each `apply_url`. `enrich_store` walks
stored internship rows missing a fact and fills them via a deterministic-first
ladder:

1. **ATS JSON endpoints** for recognized hosts (Lever, Ashby, Greenhouse) —
   structured, no HTML, one request. Tried first on those hosts because it is
   cheaper and more precise than the page itself (Greenhouse hosted pages
   carry no JSON-LD at all, verified live 2026-08-06).
2. **JSON-LD JobPosting** on the fetched apply page: `baseSalary` -> reward
   (quoted, span = the JSON text), `validThrough` -> deadline (**derived** —
   a posting expiry is not a stated application deadline),
   `hiringOrganization.logo` -> org logo.
3. **LLM page extract** (the GH-5 contract) only for rows the deterministic
   stages left empty, hard-capped per run, skipped gracefully when no
   provider is configured.

The no-fabrication rule applies throughout: a fact the source does not state
stays null with provenance `none`. Pay reuses the `reward` field as a
verbatim-ish quoted string; `parse_money.py` normalizes it downstream.

Politeness: callers pass a fetch_fn (PoliteFetcher + cache in the CLI). The
run stops after `page_cap` network fetches (cache hits are free). Every row
attempt lands in the `enrich_attempts` ledger with an outcome
(`filled` / `no_fact` / `unreachable`) so empty or dead pages are not
re-fetched for `retry_days`.
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import quote, urlsplit

from pydantic import BaseModel

from .fetch import FetchResult
from .jsonld import extract_jobposting_facts
from .logos import OrgLogoStore, normalize_org
from .models import Opportunity, Provenance
from .store import OpportunityStore

DEFAULT_PAGE_CAP = 200
DEFAULT_LLM_CAP = 15
DEFAULT_RETRY_DAYS = 7

#: employers worth spending budget on ahead of the long tail
MARQUEE_ORGS = frozenset(
    {
        "google", "alphabet", "meta", "apple", "microsoft", "amazon", "netflix",
        "nvidia", "tesla", "spacex", "openai", "anthropic", "stripe",
        "databricks", "palantir", "jane street", "citadel", "citadel securities",
        "two sigma", "hudson river trading", "jump trading", "d. e. shaw",
        "bloomberg", "uber", "lyft", "airbnb", "doordash", "snap", "tiktok",
        "bytedance", "shopify", "ibm", "intel", "amd", "qualcomm", "salesforce",
        "adobe", "atlassian", "figma", "ramp", "plaid", "coinbase", "robinhood",
        "roblox", "waymo", "anduril", "snowflake", "datadog", "cloudflare",
    }
)

_CANADA_MARKERS = (
    "canada", "toronto", "vancouver", "montreal", "waterloo", "ottawa",
    "calgary", "edmonton", "kitchener", "mississauga",
)


class AtsRef(BaseModel):
    kind: str  # "lever" | "ashby" | "greenhouse"
    api_url: str
    job_id: str


def ats_ref(apply_url: str) -> AtsRef | None:
    """Map a recognized ATS apply_url to its public JSON endpoint."""
    parts = urlsplit(apply_url)
    host = parts.netloc.lower()
    segments = [s for s in parts.path.split("/") if s]

    if host in ("jobs.lever.co", "jobs.eu.lever.co") and len(segments) >= 2:
        org, job_id = segments[0], segments[1]
        return AtsRef(
            kind="lever",
            api_url=f"https://api.lever.co/v0/postings/{quote(org)}/{quote(job_id)}",
            job_id=job_id,
        )
    if host == "jobs.ashbyhq.com" and len(segments) >= 2:
        org, job_id = segments[0], segments[1]
        return AtsRef(
            kind="ashby",
            api_url=(
                "https://api.ashbyhq.com/posting-api/job-board/"
                f"{quote(org)}?includeCompensation=true"
            ),
            job_id=job_id,
        )
    greenhouse_hosts = (
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "boards.eu.greenhouse.io",
        "job-boards.eu.greenhouse.io",
    )
    # boards-api.greenhouse.io serves EU boards too (verified live 2026-08-06)
    if host in greenhouse_hosts and len(segments) >= 3 and segments[1] == "jobs":
        org, job_id = segments[0], segments[2]
        return AtsRef(
            kind="greenhouse",
            api_url=(
                f"https://boards-api.greenhouse.io/v1/boards/{quote(org)}/jobs/"
                f"{quote(job_id)}?pay_transparency=true"
            ),
            job_id=job_id,
        )
    return None


class AtsFacts(BaseModel):
    pay: str | None = None
    pay_source: str | None = None
    deadline: str | None = None
    deadline_source: str | None = None


def _fmt_amount(value: float) -> str:
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,}"


def _lever_facts(data: dict) -> AtsFacts:
    salary_range = data.get("salaryRange")
    if (
        isinstance(salary_range, dict)
        and isinstance(salary_range.get("min"), (int, float))
        and isinstance(salary_range.get("max"), (int, float))
        and salary_range["max"] > 0  # an all-zero range is a placeholder
    ):
        low, high = salary_range["min"], salary_range["max"]
        text = (
            _fmt_amount(high) if low == high or low <= 0
            else f"{_fmt_amount(low)}–{_fmt_amount(high)}"
        )
        currency = salary_range.get("currency")
        if isinstance(currency, str) and currency.strip():
            text = f"{text} {currency.strip().upper()}"
        interval = salary_range.get("interval")
        if isinstance(interval, str) and interval.strip():
            # Lever intervals read like "per-year-salary"
            words = interval.strip().lower().replace("-", " ")
            text = f"{text} {words}" if words.startswith("per") else f"{text} per {words}"
        return AtsFacts(
            pay=text,
            pay_source=json.dumps({"salaryRange": salary_range}, ensure_ascii=False),
        )
    description = data.get("salaryDescriptionPlain")
    if isinstance(description, str) and description.strip():
        return AtsFacts(pay=description.strip(), pay_source=description.strip())
    return AtsFacts()


def _ashby_facts(data: dict, job_id: str) -> AtsFacts:
    for job in data.get("jobs") or []:
        if not isinstance(job, dict) or job.get("id") != job_id:
            continue
        compensation = job.get("compensation")
        if not isinstance(compensation, dict):
            return AtsFacts()
        summary = compensation.get(
            "scrapeableCompensationSalarySummary"
        ) or compensation.get("compensationTierSummary")
        if isinstance(summary, str) and summary.strip():
            return AtsFacts(
                pay=summary.strip(),
                pay_source=json.dumps(
                    {"compensation": {"summary": summary}}, ensure_ascii=False
                ),
            )
        return AtsFacts()
    return AtsFacts()


def _greenhouse_deadline(data: dict) -> tuple[str | None, str | None]:
    raw = data.get("application_deadline")
    if isinstance(raw, str) and raw.strip():
        value = raw.strip()
    elif isinstance(raw, dict):
        value = next(
            (
                v.strip()
                for k in ("deadline", "date", "closes_at", "close_date")
                if isinstance((v := raw.get(k)), str) and v.strip()
            ),
            None,
        )
    else:
        value = None
    if value is None:
        return None, None
    return value, json.dumps({"application_deadline": raw}, ensure_ascii=False)


def _greenhouse_facts(data: dict) -> AtsFacts:
    parts = []
    ranges = data.get("pay_input_ranges")
    for entry in ranges if isinstance(ranges, list) else []:
        if not isinstance(entry, dict):
            continue
        low, high = entry.get("min_cents"), entry.get("max_cents")
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            continue
        if high <= 0:  # an all-zero range is a placeholder, not stated pay
            continue
        text = (
            f"${low / 100:,.2f}" if low == high
            else f"${low / 100:,.2f}–${high / 100:,.2f}"
        )
        currency = entry.get("currency_type")
        if isinstance(currency, str) and currency.strip():
            text = f"{text} {currency.strip().upper()}"
        title = entry.get("title")
        if isinstance(title, str) and title.strip():
            text = f"{text} ({title.strip()})"
        parts.append(text)

    pay = "; ".join(parts) or None
    pay_source = (
        json.dumps({"pay_input_ranges": ranges}, ensure_ascii=False) if pay else None
    )
    deadline, deadline_source = _greenhouse_deadline(data)
    return AtsFacts(
        pay=pay, pay_source=pay_source,
        deadline=deadline, deadline_source=deadline_source,
    )


def ats_facts(ref: AtsRef, body: str) -> AtsFacts:
    """Parse an ATS JSON response; absent fields are absent facts."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return AtsFacts()
    if not isinstance(data, dict):
        return AtsFacts()
    if ref.kind == "lever":
        return _lever_facts(data)
    if ref.kind == "ashby":
        return _ashby_facts(data, ref.job_id)
    return _greenhouse_facts(data)


class EnrichLedger:
    """Per-row attempt record: don't re-hammer pages that gave nothing."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS enrich_attempts (
                opportunity_id TEXT PRIMARY KEY,
                attempted_at TEXT NOT NULL,
                outcome TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def record(self, opportunity_id: str, outcome: str, at: datetime) -> None:
        self._conn.execute(
            """
            INSERT INTO enrich_attempts (opportunity_id, attempted_at, outcome)
            VALUES (?, ?, ?)
            ON CONFLICT(opportunity_id) DO UPDATE SET
                attempted_at = excluded.attempted_at,
                outcome = excluded.outcome
            """,
            (opportunity_id, at.isoformat(), outcome),
        )
        self._conn.commit()

    def attempted_since(self, opportunity_id: str, cutoff: datetime) -> bool:
        row = self._conn.execute(
            "SELECT attempted_at FROM enrich_attempts WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
        return row is not None and datetime.fromisoformat(row["attempted_at"]) >= cutoff


class EnrichReport(BaseModel):
    rows_considered: int = 0
    rows_skipped_recent: int = 0
    rows_attempted: int = 0
    fetches: int = 0
    cap_reached: bool = False
    outcomes: dict[str, int] = {}
    # stage -> fact -> count, e.g. {"ats": {"pay": 12}, "jsonld": {"logo": 3}}
    fills: dict[str, dict[str, int]] = {}
    llm_calls: int = 0
    llm_skipped_reason: str | None = None

    def count_fill(self, stage: str, fact: str) -> None:
        self.fills.setdefault(stage, {})
        self.fills[stage][fact] = self.fills[stage].get(fact, 0) + 1

    def count_outcome(self, outcome: str) -> None:
        self.outcomes[outcome] = self.outcomes.get(outcome, 0) + 1

    def filled(self, fact: str) -> int:
        return sum(stage.get(fact, 0) for stage in self.fills.values())


def _is_canadian(opp: Opportunity) -> bool:
    text = (opp.description or "").lower()
    return any(marker in text for marker in _CANADA_MARKERS)


def _is_marquee(opp: Opportunity) -> bool:
    return (normalize_org(opp.organization) or "") in MARQUEE_ORGS


def _prioritize(candidates: list[Opportunity]) -> None:
    # Canada first, then marquee employers, then newest (stable two-pass sort)
    candidates.sort(key=lambda o: o.first_seen or "", reverse=True)
    candidates.sort(key=lambda o: (not _is_canadian(o), not _is_marquee(o)))


def _needs(opp: Opportunity, logos: OrgLogoStore) -> dict[str, bool]:
    return {
        "pay": opp.reward is None,
        "deadline": opp.deadline is None,
        "logo": (
            normalize_org(opp.organization) is not None
            and logos.get(opp.organization) is None
        ),
    }


class _Budget:
    """Counts network fetches (cache hits are free) against the page cap."""

    def __init__(self, fetch_fn: Callable[[str], FetchResult], cap: int):
        self._fetch_fn = fetch_fn
        self._cap = cap
        self.fetches = 0

    @property
    def exhausted(self) -> bool:
        return self.fetches >= self._cap

    def fetch(self, url: str) -> FetchResult | None:
        if self.exhausted:
            return None
        result = self._fetch_fn(url)
        if not result.from_cache:
            self.fetches += 1
        return result


def _pick_llm_item(opportunities: list[Opportunity]) -> Opportunity | None:
    for candidate in opportunities:
        if candidate.reward is not None or candidate.deadline is not None:
            return candidate
    return None


def enrich_store(
    store: OpportunityStore,
    *,
    fetch_fn: Callable[[str], FetchResult],
    extract_fn: Callable | None = None,
    page_cap: int = DEFAULT_PAGE_CAP,
    llm_cap: int = DEFAULT_LLM_CAP,
    retry_days: int = DEFAULT_RETRY_DAYS,
    now: datetime | None = None,
    log: Callable[[str], None] = lambda line: None,
) -> EnrichReport:
    """One bounded enrichment pass over internship rows missing facts."""
    now = now or datetime.now(timezone.utc)
    logos = OrgLogoStore(store.db_path)
    ledger = EnrichLedger(store.db_path)
    budget = _Budget(fetch_fn, page_cap)
    report = EnrichReport()
    if extract_fn is None:
        report.llm_skipped_reason = "no LLM provider configured; deterministic stages only"
        log(f"LLM stage skipped: {report.llm_skipped_reason}")

    candidates = [
        opp
        for opp in store.list()
        if (opp.type or "").strip().lower() == "internship"
        and any(_needs(opp, logos).values())
    ]
    _prioritize(candidates)
    report.rows_considered = len(candidates)
    cutoff = now - timedelta(days=retry_days)

    for opp in candidates:
        if budget.exhausted:
            report.cap_reached = True
            break
        if ledger.attempted_since(opp.id, cutoff):
            report.rows_skipped_recent += 1
            continue

        report.rows_attempted += 1
        need = _needs(opp, logos)
        fetch_ok = fetch_failed = False
        changed = False
        page_body: str | None = None

        def _fill(fact: str, stage: str) -> None:
            nonlocal changed
            need[fact] = False
            changed = True
            report.count_fill(stage, fact)

        # stage: ATS JSON endpoint (deterministic, no HTML)
        ref = ats_ref(opp.apply_url)
        if ref is not None and (need["pay"] or need["deadline"]):
            result = budget.fetch(ref.api_url)
            if result is not None and result.ok:
                fetch_ok = True
                facts = ats_facts(ref, result.body)
                if need["pay"] and facts.pay:
                    opp.reward = facts.pay
                    opp.reward_provenance = Provenance.QUOTED
                    opp.reward_source = facts.pay_source
                    _fill("pay", "ats")
                if need["deadline"] and facts.deadline:
                    # greenhouse application_deadline is a stated deadline
                    opp.deadline = facts.deadline
                    opp.deadline_provenance = Provenance.QUOTED
                    opp.deadline_source = facts.deadline_source
                    _fill("deadline", "ats")
            elif result is not None:
                fetch_failed = True

        # stage: JSON-LD JobPosting on the apply page itself
        if any(need.values()) and not budget.exhausted:
            result = budget.fetch(opp.apply_url)
            if result is not None and result.ok:
                fetch_ok = True
                page_body = result.body
                facts = extract_jobposting_facts(result.body)
                if facts is not None:
                    if need["pay"] and facts.salary:
                        opp.reward = facts.salary
                        opp.reward_provenance = Provenance.QUOTED
                        opp.reward_source = facts.salary_source
                        _fill("pay", "jsonld")
                    if need["deadline"] and facts.valid_through:
                        # a posting expiry, not a stated application deadline
                        opp.deadline = facts.valid_through
                        opp.deadline_provenance = Provenance.DERIVED
                        opp.deadline_source = facts.valid_through_source
                        _fill("deadline", "jsonld")
                    if need["logo"] and facts.logo:
                        if logos.set(
                            facts.organization or opp.organization,
                            facts.logo,
                            source=opp.apply_url,
                        ):
                            _fill("logo", "jsonld")
            elif result is not None:
                fetch_failed = True

        # stage: LLM page extract, only for rows the ladder left empty
        if (
            (need["pay"] or need["deadline"])
            and extract_fn is not None
            and report.llm_calls < llm_cap
            and page_body is not None
        ):
            report.llm_calls += 1
            try:
                extraction = extract_fn(page_body, opp.apply_url)
            except Exception as exc:
                log(f"LLM extract failed for {opp.apply_url}: {exc}")
            else:
                item = _pick_llm_item(extraction.opportunities)
                if item is not None:
                    if need["pay"] and item.reward is not None:
                        opp.reward = item.reward
                        opp.reward_provenance = item.reward_provenance
                        opp.reward_source = item.reward_source
                        _fill("pay", "llm")
                    if need["deadline"] and item.deadline is not None:
                        opp.deadline = item.deadline
                        opp.deadline_provenance = item.deadline_provenance
                        opp.deadline_source = item.deadline_source
                        _fill("deadline", "llm")

        if changed:
            store.update(opp)
            outcome = "filled"
        elif fetch_ok:
            outcome = "no_fact"
        elif fetch_failed:
            outcome = "unreachable"
        else:
            # cap ran out mid-row before any fetch happened; leave no ledger
            # mark so the row is first in line next run
            report.rows_attempted -= 1
            report.cap_reached = True
            break
        ledger.record(opp.id, outcome, now)
        report.count_outcome(outcome)

    report.fetches = budget.fetches
    return report
