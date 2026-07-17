Denied again — headless, so no approval is possible. I'll rely on reading plus the test stage's count.

## Review — GH-43, iteration 2

**Verdict: success.** My blocking finding from iteration 1 is fixed correctly and completely, and the fix is tight rather than sprawling — the diff this iteration touches only `index.html` and `tests/test_api.py`, leaving the already-reviewed `api.py`/`cli.py`/`pyproject.toml` untouched.

### The XSS fix holds

I checked the escaping against the specific ways this kind of fix usually goes wrong:

- **`escapeHtml` (`index.html:54`)** does a single pass over `/[&<>"']/g` with a lookup replacer, so `&` can't double-escape the entities it just emitted. It covers both quote characters, making it sound in text and quoted-attribute contexts alike.
- **`fmt` (`index.html:62`)** escapes on the *value* branch only and still returns the trusted `<span class="missing">` markup on the absent branch. This was the trap the plan flagged — wrapping `fmt`'s output would have rendered visible `&lt;span…` text and quietly broken the missing-fact display. It's done right, so "no deadline found" still renders as intended.
- **`safeUrl` (`index.html:66`)** allowlists `http:`/`https:` and returns `null` otherwise, so `javascript:alert(1)` degrades to an unlinked title (`index.html:81-83`) rather than an executable href. It also returns the original `url` rather than `u.href`, but `escapeHtml(href)` at line 82 escapes the quotes, so an attribute breakout is blocked on the second layer too.
- **Coverage is complete.** A grep for `${opp.` / `${item.` returns zero unwrapped interpolations; the only two `innerHTML` sinks (`index.html:107,109`) are fed exclusively by `renderCard`/`renderExcludedCard`, both fully escaped. `loadProfile` writes through `.value` property assignment, which doesn't parse HTML.

The `__import__("pathlib")` hygiene note is also resolved — `from pathlib import Path` is at the top and the new `_index_html()` helper is shared with the existing test.

### One honest caveat on the new test

`test_markup_in_stored_fields_is_not_rendered_raw` asserts on *source text* (`"${opp.title}" not in html`), not on rendered output. That's a brittle test — it would pass on a refactor that renamed the helper while reintroducing the hole. I'm accepting it because the plan reasoned the limit out openly rather than papering over it: TestClient runs no JavaScript, and the served page never contains a title (they arrive via `fetch`), so rendered-output assertions are genuinely unreachable without a JS runtime. The half of that test that *is* behavioral — the API returning the markup byte-identical in JSON — is correct and worth keeping, since JSON isn't HTML and escaping is properly the renderer's job. The real verification of the escaping here is my read of the code above, not this test.

I also endorse the plan's rejection of the CSP/script-split alternative. It would have been more assertable from TestClient, but adding a route and a file split to buy a convenient test is the wrong trade.

### Lenses 1 and 3

**Intent:** all five criteria hold. Criteria 1, 3, and 4 are unchanged from iteration 1, where I verified the rank ordering against the sort key at `rank.py:172` and confirmed parsed values ship alongside verbatim strings structurally. Criterion 2's render-as-absent path is preserved by `fmt`'s untouched missing branch. No auth exists anywhere in `api.py`.

**Visual: skipped for lack of tooling** — still no Playwright in this session. Reading the markup, the structure is unchanged and sane: centered column, eligible cards, `<details>` excluded section collapsed by default, profile editor.

**On the test suite:** I could not run `uv run pytest -q` myself — it required approval both iterations and I'm headless. The test stage reports 136 passed, up from 135, which is exactly consistent with the single test added this iteration. Combined with my own reading of the logic, I'm satisfied, but I'm flagging plainly that the green suite is the test stage's evidence and not independently reproduced by me.

The working tree shows only `state.json` and untracked `observability/` files — harness bookkeeping written by the stages themselves, not source changes. The source tree is clean.

```json
{
  "stage": "review",
  "ticket_id": "GH-43",
  "outcome": "success",
  "exit_signal": true,
  "summary": "Iteration 1's blocking stored-XSS finding is fully fixed: escapeHtml folded into fmt's value branch (missing-fact span preserved), safeUrl http(s) allowlist degrading a javascript: apply_url to an unlinked title, and zero unwrapped interpolations remaining at either innerHTML sink. All 5 acceptance criteria verified; scope discipline held (only index.html + test_api.py touched). Visual lens skipped for lack of Playwright. Caveat: pytest required approval in this headless session, so the green suite (136 passed, +1 consistent with the one added test) is the test stage's evidence, not independently reproduced here. The new XSS test asserts source contract rather than rendered output — an acknowledged and correctly-reasoned limit of TestClient, which runs no JS.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": ["playwright"],
  "system_repair_suggested": false,
  "pr_description": "## Dashboard — read API + single-page opportunity dashboard\n\nThe first visible surface for the project: a local FastAPI service and a single self-contained HTML page that shows ranked opportunities and lets you edit the profile they're ranked against.\n\n**What changed**\n\n- `scholarship_factory/api.py` — new FastAPI app built by a `create_app(db_path)` factory. `GET /api/opportunities` returns `rank()`'s output directly (eligible in rank order, excluded with verdicts and reasons, parsed deadline/reward alongside the verbatim stored strings). `GET`/`PUT /api/profile` view and edit the single profile, which is the one write needed to make ranking usable.\n- `scholarship_factory/static/index.html` — vanilla-JS dashboard at `/`: eligible cards with title/org/deadline/reward and an apply link, a collapsed excluded section showing why each item was dropped, and a minimal profile editor. No build step, no npm, no CDN.\n- `scholarship_factory/cli.py` — `sf serve` subcommand (`--host`, `--port`, inheriting `--db`) starting uvicorn.\n- `tests/test_api.py` — 5 tests via FastAPI's TestClient against a temp db; no live server, no network.\n\n**Notable decisions and tradeoffs**\n\n- **SQLite stores are constructed per request**, not once at app scope. FastAPI runs sync endpoints in a threadpool, and these stores open their connection in `__init__` with the default `check_same_thread=True`, so an app-scoped store would raise `ProgrammingError` on every request. Connections are cheap and this is a single-user local service. The tradeoff: per-request connections are never explicitly closed (neither store exposes `close()`), so they're reclaimed on GC — acceptable at this scale, but it's the thing to revisit if this ever serves more than one user.\n- **Provenance honesty is enforced end to end.** A missing fact serializes as JSON `null` and renders as an italic \"no deadline found\", never as an invented value.\n- **The dashboard escapes everything it renders.** Opportunity titles, orgs, and URLs originate in JSON-LD scraped from third-party sites, so they're untrusted input flowing into `innerHTML`. All interpolations go through `escapeHtml`, and `apply_url` is scheme-checked by `safeUrl` (non-http(s) URLs render as an unlinked title) — this closed a stored-XSS hole caught in review.\n\n**Risks a merger should know**\n\n- The XSS escaping is verified by code review plus source-contract assertions, **not** by rendered-output tests: TestClient executes no JavaScript and no Playwright is available, so nothing in CI would catch a future refactor that reintroduces a raw interpolation. A JS-runtime or Playwright test is the natural follow-up.\n- `PUT /api/profile` is full-replacement semantics — a partial body nulls the omitted fields. Correct for PUT, but worth knowing if a PATCH-style caller is ever added.\n- Ranking calls `date.today()` with no injectable clock at the API layer; tests use far-past/far-future deadlines so verdicts don't rot.\n- No auth, by design — bind stays on 127.0.0.1."
}
```