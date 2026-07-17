Confirmed: the only `textContent` uses are for the internal "saved" literal; every untrusted field goes through `innerHTML` unescaped.

## Review — GH-43

**Verdict: failure.** The feature is well-built and the four functional criteria hold up under reading, but the dashboard renders scraped third-party content into `innerHTML` with no escaping, which is a stored-XSS hole introduced by this diff. That's a must-fix under Lens 2.

### Lens 1 — intent

Four of five criteria verify cleanly against the code:

- **Ranked output.** `rank()` returns `RankedResults` with `eligible`/`excluded`, and `api.py:39` returns it directly as the response model, so parsed `deadline: date | None` and `reward: MoneyValue` ship alongside the verbatim `opportunity.deadline`/`reward` strings structurally — no hand-written serializer to get wrong. I confirmed the ordering assertion in `tests/test_api.py:66` against the sort key at `rank.py:172`: `deadline is None` sorts last, so `["Eligible Future Grant", "No Deadline Grant"]` is genuinely what that seed produces. The test's far-future (2099) and far-past (2020) deadlines mean the verdicts don't rot over time.
- **Null deadline.** `deadline=None` serializes to JSON `null` via pydantic; nothing invented.
- **Profile re-rank.** `PUT /api/profile` uses `existing.model_copy(update=body.model_dump())`, preserving `id`/`owner`/`created_at`, and `test_profile_update_reranks` shows the EU-only opportunity crossing from excluded to eligible when region flips to Germany. That's real behavioral evidence, not prose.
- **`GET /`** asserts 200, html content-type, and both endpoint paths.

One criterion is **weakly verified**: "the page renders it as absent." The test (`tests/test_api.py:91`) only asserts the literal string `no deadline found` exists in the HTML *file* — an assertion about source text, not about rendering. Reading `fmt()` at `index.html:58`, the logic is correct, so I'm satisfied by inspection rather than by the test.

### Lens 2 — quality & security

**Must-fix — stored XSS from scraped content.** `renderCard` and `renderExcludedCard` interpolate `opp.title`, `opp.organization`, `opp.apply_url`, and `item.reasons` straight into template strings assigned to `innerHTML` (`index.html:66-83`), with no escaping anywhere in the file. These fields are not user-typed — `extract.py:105-111` populates them from `jsonld.py`, which parses `application/ld+json` blocks out of fetched remote pages. So a hostile or compromised source site controls a string that becomes live markup in the dashboard's origin.

The concrete failure: a source page publishes `"title": "<img src=x onerror='fetch(\"/api/profile\",{method:\"PUT\",headers:{\"Content-Type\":\"application/json\"},body:JSON.stringify({region:\"nowhere\"})})'>"`. On the next `sf source` run that lands in the DB, and the first dashboard load executes it. Since there's no auth (correctly, per the ticket), the injected script can freely read the full opportunity list and overwrite the profile via the API, or exfiltrate both to an external host. Separately, `href="${opp.apply_url}"` is vulnerable to a `"` breaking out of the attribute, and to a `javascript:` scheme URL.

I want to be clear this is in scope rather than a pre-existing condition: `index.html` is new in this diff, and it's the first thing in the project to render stored content as markup. The fix is small — an `escapeHtml()` helper applied to every interpolated field, plus an `http(s)`-scheme check on `apply_url` before using it as an `href`.

**Hygiene (not blocking):** `tests/test_api.py:90` uses `__import__("pathlib").Path` inline instead of a top-level `import pathlib`; it works but doesn't match the file's own import style. Also worth noting the fetches in `loadOpportunities`/`loadProfile` have no error handling, so an API failure leaves a silently blank page — minor for a local single-user tool, your call whether it matters.

The design decisions I checked all hold: per-request store construction avoids the SQLite cross-thread error the plan flagged; the deferred `import uvicorn` inside `_cmd_serve` keeps `sf list` import-light and avoids a cycle with `api.py`'s module-level import from `.cli`; PUT replacing all five fields is correct PUT semantics.

### Lens 3 — visual

**Skipped for lack of tooling** — no Playwright tool is available in this session, so I fell back to reading the markup against the criteria. The structure is sane: centered 900px column, eligible cards with title/org/deadline/reward and an `apply_url` anchor, a `<details>` excluded section correctly collapsed by default (no `open` attribute), and a profile form wired to `PUT`. Missing facts render as an italic grey `.missing` span rather than a fabricated value, which honors the provenance rule.

### Fix list (ordered)

1. Escape all untrusted interpolations in `index.html` (`title`, `organization`, `deadline`, `reward`, `reasons`, `verdict`) before they reach `innerHTML`.
2. Validate `apply_url` is `http`/`https` before emitting it as an `href`.
3. Add a test seeding an opportunity whose title contains markup, asserting the served page escapes it.
4. Optional: replace the `__import__("pathlib")` call in `tests/test_api.py:90` with a normal import.

I did not run `uv run pytest -q` myself — the command required approval and I'm headless, so I could not confirm the "135 passed" claim independently. My acceptance-criteria findings above come from reading the code and tests, and the ordering/serialization logic checks out.

```json
{
  "stage": "review",
  "ticket_id": "GH-43",
  "outcome": "failure",
  "exit_signal": false,
  "summary": "API, CLI, and tests are solid and 4/5 criteria verify by inspection (rank order confirmed against rank.py's sort key; null deadline serializes correctly; profile PUT re-ranks). Blocking: the new dashboard interpolates scraped third-party content (title/organization/apply_url, sourced from remote JSON-LD via extract.py) into innerHTML with no escaping — stored XSS against an unauthenticated local write API. Visual lens skipped: no Playwright available. Could not run pytest (approval required in headless session).",
  "failure_reason": "Stored XSS in scholarship_factory/static/index.html: renderCard/renderExcludedCard (lines 66-83) interpolate attacker-influenceable fields into innerHTML unescaped, and apply_url is emitted as an href without scheme validation. Fixes, in order: (1) add an escapeHtml() helper and apply it to every interpolated field (title, organization, deadline, reward, reasons, verdict); (2) reject non-http(s) apply_url before using it as an href; (3) add a test seeding an opportunity whose title contains markup and assert the served page escapes it; (4) optional hygiene: replace the inline __import__(\"pathlib\") at tests/test_api.py:90 with a top-level import.",
  "files_changed": 0,
  "suggested_tools": ["playwright"],
  "system_repair_suggested": false
}
```