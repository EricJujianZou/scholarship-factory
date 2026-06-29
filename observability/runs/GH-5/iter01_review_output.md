All five listing URLs are present in the listing HTML (no fabricated items). I now have everything I need. Let me record the verdict.

## Review — GH-5 (Extract spine)

I oriented per PRIME, read the plan/implement/test outputs and the full manifest, then reviewed `git diff main...HEAD` through the three lenses. The reviewer session is locked read-only (Bash/Write denied), so I verified the substring contract independently with Grep + clean_html reasoning rather than re-running pytest (test & implement stages both report 21 green).

**Lens 1 — intent (all 6 ACs walked against evidence):**
- **AC1 (uwaterloo quoted+verbatim, multi-deadline):** `test_uwaterloo_grants_facts_are_quoted_and_verbatim` asserts QUOTED provenance, `*_source ∈ cleaned`, and both "June 1st" + "October 1st" present. I confirmed the raw HTML (`<p><strong>Amount:</strong> Up to $7,500 </p>`, line 159 deadline) reduces under `clean_html` to exactly the recorded spans `"Amount: Up to $7,500"` / `"Application Deadline: (2 annually): June 1st, and October 1st"`. ✓
- **AC2 (listing → N thin items, list, no fabricated deadlines):** asserts `kind==LIST`, len 5, every deadline `None`/`NONE`, title+url present. All 5 recorded URLs genuinely occur in the listing HTML — items are sourced, not invented. ✓
- **AC3 (detail → 1 record, €7,500):** asserts `DETAIL`, len 1, "WE-EMPOWER II Grant", `reward=="Up to €7,500"`, QUOTED. `reward_source="Funding of up to €7,500"` is verbatim (line 1039). The AC's "EUR" vs the page's "€" was a known Risk-2 call: verbatim-substring honesty correctly wins. ✓
- **AC4 (absent fact → null/none/null):** `test_fact_with_source_not_on_page_is_nulled` exercises `_quoted_fact` directly. ✓
- **AC5 (deterministic/offline):** `StubClient` drives `extract`; `anthropic` is imported lazily only inside `_default_client`, and is gated behind the `llm` extra in both `pyproject.toml` and `uv.lock` (`marker = "extra == 'llm'"`), so the default dev sync stays network-free. ✓
- **AC6 (pytest green):** reported 21 passing by two prior stages; logic verified. ✓

**Lens 2 — quality & security:** The honesty gate is enforced in code, not just the prompt — `_quoted_fact` demotes any fact whose `*_source` isn't a literal substring of the cleaned text to `(None, None, NONE)`, which also keeps the `Opportunity` model_validator satisfied (source is never None while provenance != none). Provenance is derived from verified presence rather than trusting an LLM enum — the right call. `clean_html` correctly preserves JSON-LD/`<time>` while skipping `<script>/<style>`. No injection/secret/subprocess concerns (no network in tests; client is injectable). No dead code; tests assert concrete values. One acceptable design note: only the *source* span is substring-verified, not the display *value* (e.g. `reward="Up to €7,500"` vs source `"Funding of up to €7,500"`) — the source span is the provenance anchor, and the value happens to also appear verbatim in the page title here.

**Lens 3 — visual:** No user-facing surface — this is a backend extraction module (`clean.py` + `extract.py`). Playwright N/A; nothing to render.

**Tree state:** the committed diff is clean; the only uncommitted items (`state.json`, `observability/runs/GH-5/*`) are harness run artifacts expected mid-run, not implementation leftovers.

Everything holds.

```json
{
  "stage": "review",
  "ticket_id": "GH-5",
  "outcome": "success",
  "exit_signal": true,
  "summary": "Extract spine is correct and honest: stdlib pre-clean preserves fact-bearing text, extract() enforces quoted-only provenance by substring-verifying every source span (demoting unverifiable facts to none), and the typed detail/list result with 0..N segmentation is fully exercised by 21 offline recorded-response tests. All 6 ACs verified with evidence; anthropic is lazy-imported and gated behind the 'llm' extra so default tests stay offline. No user-facing surface (visual lens N/A). Candidate for a 'recorded-LLM-extraction' skill in skills/.",
  "failure_reason": null,
  "files_changed": 9,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the S2 Extract spine: one fetched page -> 0..N honest Opportunity records.\n\n**What changed**\n- `scholarship_factory/clean.py`: stdlib (`html.parser`) pre-clean that strips `<script>`/`<style>` but preserves fact-bearing content (`<time datetime>`, JSON-LD bodies, inline text) and normalizes whitespace.\n- `scholarship_factory/extract.py`: `extract(raw_html, source_url, *, client=None, model=...)` calls the Anthropic SDK via forced tool-use as structured output, maps the result to `Opportunity` records, and returns a typed `ExtractionResult` carrying `PageKind.DETAIL` vs `PageKind.LIST`. The LLM client is injectable; `anthropic` is imported lazily only when no client is passed.\n- No-fabrication is enforced in code, not just the prompt: each deadline/reward/cost is kept only if its `*_source` is a literal substring of the cleaned page text; otherwise the value, source, and provenance are nulled to `none`.\n- `pyproject.toml` + `uv.lock`: `anthropic` declared as the optional `llm` extra so the default/test sync needs no network.\n- 3 recorded LLM-response fixtures + `tests/test_extract.py` (offline, stubbed client) covering quoted/verbatim provenance, the uncollapsed multi-deadline case, N thin list items, the single detail record, and the absent-fact -> none path.\n\n**Tradeoffs / risks for a merger**\n- Substring verification anchors on the *source span*; the display *value* is not separately substring-checked (the source is the provenance anchor). \n- AC#3 writes the reward as \"EUR 7,500\" but the page renders \"€7,500\"; the verbatim euro-sign form is stored intentionally (honesty over the AC's paraphrase).\n- `source_observed_date` is passed through without span verification (no provenance field exists for it in the model).\n- Tests are fully offline; the live Anthropic path is exercised only when the `llm` extra is installed and a real client is constructed."
}
```