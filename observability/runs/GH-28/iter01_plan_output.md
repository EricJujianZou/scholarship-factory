I have what I need. No `progress.txt` in this repo; the foundations (`profile.py`, `models.py`, `parse_dates.py`, `parse_money.py`) are all merged and read.

One gotcha worth flagging up front: `typed_deadlines` (`parse_dates.py:44`) needs an anchor from `source_observed_date` or `first_seen`, and returns a **list** of dates (the multi-deadline case is deliberately not collapsed). So the plan has to decide which date drives urgency — I've locked that below rather than leaving it to the implementer.

## Context

- New module `scholarship_factory/rank.py`; no existing file changes. Foundations: `Opportunity` (`models.py:13`, string `deadline`/`reward`, nullable `requirements`/`description`), `ApplicantProfile` (`profile.py:17`, nullable `region`/`education_level`/`field_of_study`).
- `typed_deadlines(opp)` (`parse_dates.py:44`) returns `(list[date] | None, Provenance)` and yields `None` when there is no anchor date — that path must funnel into "undated, still eligible", not an error.
- `typed_reward(opp)` (`parse_money.py:92`) returns `(MoneyValue | None, Provenance)`; `MoneyValue.amount` is the total (`parse_money.py:23`).
- House style (seen in `parse_money.py`): pydantic v2 models, `str`-valued `Enum`s, module-level compiled regex tables, small pure functions, module docstring naming locked decisions.
- Tests are plain pytest functions, one behavior each, no fixtures needed (`tests/test_parse_money.py`).

## Approach

`rank.py` is pure and deterministic: for each opportunity, derive typed deadline/reward via the existing S6 parse layer, run a small two-sided rule table over `requirements + description`, and emit a verdict plus reasons. The rule table is **two-sided by design**: an opportunity constraint phrase excludes only when the profile field also normalizes to a *known* canonical token via an alias table, and that token is absent from the constraint's satisfying set. This is what makes "unknown is never ineligible" structural rather than a habit — a profile region of `"Germany"` canonicalizes to `eu` and therefore satisfies an "EU residents" constraint, and an unrecognized region (or a null one) can never fire a rule at all. The rejected alternative was one-sided phrase matching (opportunity says "EU residents" → exclude unless profile region string contains "EU"), which is fewer lines but silently excludes a real EU applicant who wrote "Germany" — exactly the false-exclusion the ticket forbids.

## Steps

1. Create `scholarship_factory/rank.py` with a module docstring stating the locked decisions (deterministic, no LLM, unknown-never-ineligible, sort order) — done when the file exists and imports cleanly.
2. Define `Verdict(str, Enum)` with `ELIGIBLE = "eligible"`, `INELIGIBLE = "ineligible"`, `EXPIRED = "expired"` in `rank.py` — done when `Verdict.ELIGIBLE == "eligible"`.
3. Define result models in `rank.py`: `RankedOpportunity(BaseModel)` with `opportunity: Opportunity`, `verdict: Verdict`, `reasons: list[str] = Field(default_factory=list)`, `deadline: date | None = None`, `reward: MoneyValue | None = None`; and `RankedResults(BaseModel)` with `eligible: list[RankedOpportunity]` and `excluded: list[RankedOpportunity]`. Done when both construct with an `Opportunity` instance.
4. Add the region rule table in `rank.py` — `_REGION_ALIASES: dict[str, str]` mapping lowercased profile values to canonical tokens (`"canada"/"ca" -> "canada"`; `"united states"/"usa"/"us" -> "usa"`; `"eu"/"european union"/"germany"/"france"/"spain"/"italy"/"netherlands" -> "eu"`; `"united kingdom"/"uk" -> "uk"`), and `_REGION_CONSTRAINTS: list[tuple[re.Pattern, str, frozenset[str]]]` of `(pattern, label, satisfied_by)`: `EU residents|European Union (residents|citizens)` → label `"EU residents"`, `{"eu"}`; `US|United States (residents|citizens)` → `"US residents"`, `{"usa"}`; `Canadian (residents|citizens)|Canada only` → `"Canadian residents"`, `{"canada"}`; `UK (residents|citizens)` → `"UK residents"`, `{"uk"}`. All patterns `re.I` with `\b` guards. Done when the table compiles at import.
5. Add the education rule table in `rank.py` — `_EDUCATION_ALIASES` (`"high school"/"secondary" -> "high_school"`; `"undergraduate"/"undergrad"/"bachelor"/"bachelors" -> "undergraduate"`; `"graduate"/"masters"/"master's"/"phd"/"doctoral" -> "graduate"`) and `_EDUCATION_CONSTRAINTS` with the same triple shape: `high school students? only|must be a high school student` → `"high school students only"`, `{"high_school"}`; `undergraduates? only|must be an undergraduate` → `"undergraduate students only"`, `{"undergraduate"}`; `graduate students? only|PhD (students?|candidates?) only` → `"graduate students only"`, `{"graduate"}`. Done when the table compiles at import.
6. Implement `_canonical(value: str | None, aliases: dict[str, str]) -> str | None` in `rank.py` — exact dict lookup on `value.strip().lower()`, `None` for null/blank/unrecognized (no substring or fuzzy matching). Done when `_canonical("Germany", _REGION_ALIASES) == "eu"` and `_canonical("Mars", _REGION_ALIASES) is None`.
7. Implement `_mismatch_reasons(opp, profile) -> list[str]` in `rank.py` — build `text = " ".join(part for part in (opp.requirements, opp.description) if part)`; return `[]` immediately if text is empty. For each of the two `(constraints, profile_value, aliases, field_label)` pairs: canonicalize the profile value, skip the whole table when it is `None`; otherwise for every constraint whose pattern searches `text` and whose `satisfied_by` lacks the canonical token, append `f"{field_label} mismatch: requires '{label}', profile {field_label} '{profile_value}'"`. Collect from both tables. Done when a `region="Canada"` profile against `requirements="Open to EU residents only"` yields exactly one reason naming both `EU residents` and `Canada`.
8. Implement `_effective_deadline(opp, today) -> tuple[date | None, bool]` in `rank.py` — call `typed_deadlines(opp)`; `None`/empty → `(None, False)`. Otherwise return the earliest date `>= today` with `expired=False`; if every date is `< today`, return `(max(dates), True)`. Done when `["2026-06-01", "2026-10-01"]` against `today=2026-07-15` gives `(date(2026,10,1), False)` and both-past gives the later date with `expired=True`.
9. Implement `rank(opportunities, profile, *, today: date | None = None) -> RankedResults` in `rank.py` — default `today` to `date.today()`; per opportunity compute reasons, effective deadline, and `typed_reward(opp)[0]`. Verdict precedence: **ineligible wins over expired** (a hard applicant mismatch is more fundamental than the calendar), but when expired also holds, append the expiry reason too so nothing is lost. Expiry reason: `f"deadline {deadline.isoformat()} passed"`. Done when a region-mismatched, past-deadline opportunity is `INELIGIBLE` with two reasons.
10. Add sorting to `rank` in `rank.py` — eligible items sorted by key `(deadline is None, deadline or date.max, -reward.amount if reward else float("inf"), opportunity.title)`; excluded items preserve input order. Done when a dated item precedes an undated one and equal deadlines put the larger reward first.
11. Create `tests/test_rank.py` covering each acceptance criterion (region mismatch reason text; all-null opportunity fields stay eligible and sort last; expired bucketing + reason; deadline-then-reward ordering; all-null profile excludes nothing; unrecognized region never excludes). Build `Opportunity` with `source_observed_date` set so `typed_deadlines` has an anchor, and pass an explicit `today=date(2026, 7, 15)`. Done when `uv run pytest -q tests/test_rank.py` passes.
12. Run `uv run pytest -q` from the repo root — done when the full suite is green.

## Acceptance criteria mapping

- "An opportunity whose requirements explicitly demand a region different from the profile's region -> `ineligible` with a reason naming both values." -> steps 4, 6, 7, 9; verified by `test_region_mismatch_is_ineligible_with_reason` in `tests/test_rank.py` asserting `Verdict.INELIGIBLE` and that the reason contains both `'EU residents'` and `'Canada'`.
- "Missing `deadline` / `reward` / `requirements` -> stays `eligible`; sorts after opportunities with parsed deadlines." -> steps 7 (empty text → no reasons), 8 (`None` deadline), 10 (`deadline is None` first in sort key); verified by `test_missing_fields_eligible_and_sorts_last` asserting the bare opportunity is eligible and is the last element of `results.eligible`.
- "A parsed deadline before `today` -> `expired`, excluded from the eligible ordering but present in results with a reason." -> steps 8, 9; verified by `test_past_deadline_is_expired_and_excluded` asserting the item is absent from `eligible`, present in `excluded` with `Verdict.EXPIRED`, and its reason contains the ISO date.
- "Two eligible dated opportunities -> soonest deadline first; equal deadlines -> larger parsed reward first." -> step 10; verified by `test_sort_deadline_then_reward` with three opportunities (two sharing a deadline, differing rewards) asserting the exact title order.
- "Profile with all-null fields -> nothing excluded (everything eligible or expired)." -> steps 6, 7 (a `None` profile field canonicalizes to `None`, skipping the whole table); verified by `test_null_profile_excludes_nothing` asserting no item in the results carries `Verdict.INELIGIBLE`, given an `ApplicantProfile()` and an opportunity whose requirements say "EU residents only".
- "Pure functions, no network, no LLM; `uv run pytest -q` green." -> steps 1–12; verified by `rank.py` importing only `re`/`datetime`/`enum`/`pydantic` plus the local `models`, `profile`, `parse_dates`, `parse_money` modules, and by step 12's full-suite run.

## Risks

1. **`dateparser` resolves the deadline against the anchor, not `today`, and prefers future dates** (`parse_dates.py:18`). A fixture with `source_observed_date="2026-01-01"` and `deadline="June 1"` yields `2026-06-01` — past relative to a `today` of `2026-07-15`, which is what the expired test wants, but the same string with a 2026-08 anchor would jump to 2027. Use explicit, fully-qualified date strings (`"June 1, 2026"`) in tests rather than bare month-days, so the assertion doesn't depend on `PREFER_DATES_FROM` behavior.
2. **The multi-deadline case can be mis-bucketed as expired.** `parse_deadline_dates("June 1st, and October 1st", ...)` returns both dates; taking `dates[0]` or `min(dates)` would mark an opportunity expired while its October window is still open. Step 8's "earliest date `>= today`, expired only if *all* are past" is the guard — if a test shows an item expiring early, check that rule before touching the sort.
3. **The alias tables are the sole gate on false exclusion.** Adding a region constraint pattern without adding the corresponding profile-side aliases (e.g. an "EU residents" rule while `"Portugal"` is missing from `_REGION_ALIASES`) does not cause a wrong exclusion — an unmapped region canonicalizes to `None` and skips the table — but it does mean a real mismatch goes uncaught. Prefer that silent miss over an exclusion; do not add a fallback that compares raw strings when the alias lookup misses.

```json
{
  "stage": "plan",
  "ticket_id": "GH-28",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for deterministic rank() in a new scholarship_factory/rank.py: two-sided alias+constraint rule tables over region/education (unknown never excludes), verdict enum eligible|ineligible|expired with reasons, deadline-then-reward-then-title sort via existing parse_dates/parse_money layers, plus tests/test_rank.py covering every acceptance criterion.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/rank.py",
      "tests/test_rank.py"
    ],
    "read": [
      "scholarship_factory/models.py:13",
      "scholarship_factory/profile.py:17",
      "scholarship_factory/parse_dates.py:44",
      "scholarship_factory/parse_money.py:23",
      "scholarship_factory/parse_money.py:92",
      "tests/test_parse_money.py",
      "tests/test_parse_dates.py"
    ]
  }
}
```