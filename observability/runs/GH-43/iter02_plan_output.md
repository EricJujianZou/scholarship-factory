Iteration 1's API, CLI, `sf serve`, and uvicorn 0.51.0 are all intact — only the dashboard escaping is broken. The plan is deliberately narrow.

## Context

- Retry of iteration 1. Review (`observability/runs/GH-43/iter01_review_output.md:20-24`) passed all functional criteria but failed the ticket on stored XSS. `api.py`, `cli.py:74-103` (`sf serve`), and uvicorn 0.51.0 in `uv.lock:681` are all correct and **must not be touched**.
- The hole is confined to `scholarship_factory/static/index.html:53-84`: `renderCard`/`renderExcludedCard` build template strings assigned to `innerHTML` (`index.html:89-92`) with zero escaping. `opp.title`/`organization`/`apply_url` come from remote JSON-LD via `extract.py`→`jsonld.py`, so a hostile source site controls live markup in the dashboard origin, against an unauthenticated write API.
- Two escaping subtleties shape the fix: `fmt()` (`index.html:58`) returns *trusted* markup on the missing branch (`<span class="missing">`) and the *raw value* otherwise, so escaping must go on the value branch only, not around `fmt`'s output. And `apply_url` sits in an attribute (`index.html:68`), so it needs both entity-escaping and a scheme check — escaping alone still permits `javascript:`.
- **TestClient executes no JavaScript**, and no Playwright is available (review `suggested_tools: ["playwright"]`). This constrains what step 5's test can honestly assert.

## Approach

Add an `escapeHtml()` helper and route every untrusted interpolation through it, folding the escape into `fmt()`'s value branch so the missing-fact markup keeps working, plus a `safeUrl()` scheme allowlist that degrades an unusable `apply_url` to a plain non-linked title rather than emitting a `javascript:` href. This is the review's ordered fix list, unchanged, and touches one file plus its test.

I considered and rejected the stronger mitigation of moving the inline `<script>` to `/static/app.js` and serving a `script-src 'self'` CSP header on `/`. It would neutralize injected inline handlers as defense-in-depth and, unlike escaping, is directly assertable from TestClient via the response header — genuinely tempting given the JS-testing gap below. But it's a file split plus a new route that nobody asked for, and correct escaping already closes the hole; adding an architectural change to buy a more convenient test is the wrong trade under this repo's simplicity rule.

On verification honesty: the served `index.html` never contains any opportunity title (the page fetches it client-side), so "assert the served page escapes it" cannot be tested literally without a JS runtime. Step 5 therefore asserts the two things that *are* checkable — the API returns markup verbatim in JSON (correct: JSON isn't HTML, escaping is the renderer's job), and the source enforces the escaping contract at each interpolation site.

## Steps

1. Add `escapeHtml(value)` in `scholarship_factory/static/index.html` above `missing()` (line 54): `String(value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[ch])`. Escaping both quote characters makes it safe in text and quoted-attribute contexts alike — done when the function exists and handles `&` first.
2. Change `fmt()` (`index.html:58`) to return `missing(missingText)` when absent and `escapeHtml(value)` otherwise — done when `fmt("<b>x</b>", "none")` returns `&lt;b&gt;x&lt;/b&gt;` and `fmt(null, "none")` still returns the `.missing` span markup.
3. Add `safeUrl(url)` in `index.html`: `try { const u = new URL(url, window.location.href); return (u.protocol === "http:" || u.protocol === "https:") ? url : null; } catch { return null; }` — done when `safeUrl("javascript:alert(1)")` and `safeUrl("data:text/html,x")` both return `null` and an `https://` URL returns unchanged.
4. Rewrite `renderCard` (`index.html:62-72`) to use `const href = safeUrl(opp.apply_url)` and `const title = escapeHtml(opp.title)`; emit `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${title}</a>` when `href` is non-null, else emit bare `${title}` with no anchor; keep `fmt(opp.organization, ...)`/`deadline`/`reward` (now escaping via step 2). Rewrite `renderExcludedCard` (`index.html:74-84`) to use `escapeHtml(opp.title)`, `escapeHtml(item.verdict)`, and `escapeHtml((item.reasons || []).join("; ")) || "no reason recorded"` — join before escaping, fallback literal stays unescaped — done when no `${opp.` or `${item.` interpolation in the file lacks an `escapeHtml`/`fmt`/`safeUrl` wrapper.
5. Add `test_markup_in_stored_fields_is_not_rendered_raw` to `tests/test_api.py`: seed an opportunity titled `<img src=x onerror="alert(1)">` with `apply_url="javascript:alert(1)"`, assert `GET /api/opportunities` returns that title byte-identical in JSON, then read `index.html` and assert `"function escapeHtml("` is present, `"${opp.title}"` and `"${opp.apply_url}"` do **not** appear, and `"${escapeHtml(opp.title)}"` and `"safeUrl(opp.apply_url)"` do — done when the test passes and fails if step 4 is reverted.
6. Replace `__import__("pathlib").Path` at `tests/test_api.py:90` with a top-level `from pathlib import Path` and reuse it in step 5's test via a shared `_index_html() -> str` helper — done when no `__import__` remains in the file.
7. Run `uv run pytest -q` — done when the suite is green with no regression in the 4 pre-existing `test_api.py` tests.

## Acceptance criteria mapping

- `"GET /api/opportunities` on a seeded temp db returns eligible items in rank order plus excluded items with verdicts/reasons; parsed deadline/reward appear alongside the verbatim stored strings."` -> unchanged from iter 1 (`api.py:39`); verified by the existing `test_opportunities_ranked_with_parsed_and_verbatim` (`tests/test_api.py:57`), which step 7 must keep green.
- `"An opportunity with deadline=None serializes with a null deadline (nothing invented) and the page renders it as absent."` -> steps 2, 6; verified by the existing `test_missing_deadline_serializes_null` (`tests/test_api.py:78`) — step 2 must preserve the `.missing` span branch so the `no deadline found` assertion still holds.
- `"PUT /api/profile updates region/education_level/field_of_study/tags/bio and a subsequent GET /api/opportunities reflects re-ranking against the new profile."` -> unchanged from iter 1 (`api.py:49`); verified by the existing `test_profile_update_reranks` (`tests/test_api.py:94`).
- `"GET / serves the dashboard HTML (asserted 200 + content-type html; page references the two API endpoints)."` -> steps 1-4 keep the page self-contained; verified by the existing `test_root_serves_dashboard` (`tests/test_api.py:125`).
- `"No auth added; TestClient only, no network; uv run pytest -q green."` -> steps 5, 7; verified by the full `tests/test_api.py` — no auth is added by this iteration and step 5's test seeds the store directly with no network.

## Risks

1. **The XSS fix is not provable by the test suite.** TestClient runs no JS, so step 5's source-contract assertions prove the escaping *code exists and is wired in*, not that the browser output is inert. If the implementer reads the review's "assert the served page escapes it" literally and hunts for the seeded title in `GET /` output, they'll find it absent and may conclude the page is broken — it isn't; titles arrive via `fetch`. Do not add a JS runtime or Playwright to close this gap in this ticket; note it and move on.
2. **Escaping `fmt`'s output instead of its input.** Wrapping the `fmt(...)` call in `escapeHtml` double-escapes the missing-fact span into visible `&lt;span…` text and breaks `test_missing_deadline_serializes_null`'s intent. The escape belongs strictly on the value branch inside `fmt` (step 2).
3. **Scope creep into passing code.** `api.py`, `cli.py`, `pyproject.toml`, and `uv.lock` are already correct and reviewed; the review's only non-blocking hygiene note beyond the `__import__` is the missing `fetch` error handling in `loadOpportunities`/`loadProfile`, which it explicitly left as optional. Leave it — every changed line this iteration should trace to the XSS fix.

```json
{
  "stage": "plan",
  "ticket_id": "GH-43",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Retry plan targeting the review's blocking stored-XSS finding only: add escapeHtml() folded into fmt()'s value branch, a safeUrl() http(s) allowlist for apply_url (degrading to an unlinked title), escape every interpolation in renderCard/renderExcludedCard, plus a source-contract test and the __import__ hygiene fix. api.py/cli.py/uvicorn from iter 1 are correct and untouched. Noted explicitly: TestClient runs no JS, so the fix is verified by source contract plus the API-returns-verbatim assertion, not by rendered output; rejected a CSP/script-split as unrequested scope.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": ["playwright"],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/static/index.html:53",
      "scholarship_factory/static/index.html:58",
      "scholarship_factory/static/index.html:62",
      "scholarship_factory/static/index.html:74",
      "tests/test_api.py:90"
    ],
    "read": [
      "scholarship_factory/api.py:35",
      "scholarship_factory/cli.py:74",
      "scholarship_factory/rank.py:30",
      "scholarship_factory/models.py:13",
      "scholarship_factory/profile.py:42",
      "observability/runs/GH-43/iter01_review_output.md:20",
      "uv.lock:681"
    ]
  }
}
```