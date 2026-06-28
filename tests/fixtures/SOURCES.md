# Fixture sources (raw HTML saved 2026-06-28 for Session 2 Extract)

Saved with a desktop User-Agent. These are the acceptance-test inputs for the
S2 Extract tickets (see ../../docs/s2-extract-tickets.md).

| File | Source URL | Role |
|---|---|---|
| `lablab_executorch.html` | https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon | JSON-LD `Event`+`Offer` (dates+free cost) + prize only in prose → JSON-LD path + LLM path + the seam. 0..1 detail. (UA defeats its 403.) |
| `uwaterloo_grants.html` | https://grants.uwaterloo.ca/ | Static prose listing, facts inline (`Up to $7,500`, multi-deadline). LLM path. |
| `oppsforyouth_grants_listing.html` | https://opportunitiesforyouth.org/?s=grants | Listing of thin items; deadlines live on detail pages (traversal coupling). 0..N. |
| `oppsforyouth_detail.html` | https://opportunitiesforyouth.org/2026/06/27/we-empower-ii-grant-2026-up-to-e7500-funding-.../ | Rich 0..1 detail (WE-EMPOWER II Grant, `Up to €7,500` — reward + € currency). |
