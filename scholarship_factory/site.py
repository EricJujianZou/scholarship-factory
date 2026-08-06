"""Static public site export (ugmi.com).

`sf site` reads the store and writes one self-contained `index.html`: no
server, no API key, no live database anywhere near the internet. The page
embeds the opportunity rows as JSON and filters them client-side. Facts only,
same rule as the dashboard: the public site never shows personalization
(relevance scores are the owner's own judgments about one applicant) and
never writes anything.

Optional `site.toml` at the repo root configures the storefront pieces:

    stripe_url = "https://buy.stripe.com/..."   # the paid CTA becomes a link
    instagram = "sleppyeric"                     # DM fallback CTA + footer
    price = "$15/mo"
    email_form_action = "https://..."            # email capture form POST target

Anything missing degrades honestly: no stripe_url means the CTA says "DM me",
no email_form_action means no email box rather than a dead one.

Untrusted input note: titles, descriptions and URLs come from scraped pages.
Everything dynamic is rendered via `textContent`, the JSON embed escapes
`</`, and apply URLs are dropped server-side unless they are http(s).
"""
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .store import OpportunityStore

SITE_CONFIG_FILE = "site.toml"


def load_site_config(path: str | Path = SITE_CONFIG_FILE) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text(encoding="utf-8"))


def _source_name(source_url: str) -> str:
    host = urlparse(source_url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host == "raw.githubusercontent.com":
        return "Simplify (github.com/SimplifyJobs)"
    return host


def _row(opp) -> dict | None:
    if not opp.apply_url.lower().startswith(("http://", "https://")):
        return None
    return {
        "title": opp.title,
        "org": opp.organization,
        "type": (opp.type or "other").strip().lower(),
        "desc": opp.description,
        "req": opp.requirements,
        "deadline": opp.deadline,
        "url": opp.apply_url,
        "src": _source_name(opp.source_url),
        "seen": (opp.last_seen or "")[:10],
    }


def build_site(
    store: OpportunityStore, out_dir: str | Path, *, config: dict | None = None
) -> Path:
    config = config or {}
    rows = [r for r in (_row(o) for o in store.list()) if r is not None]
    rows.sort(key=lambda r: r["seen"], reverse=True)
    sources = sorted({r["src"] for r in rows})
    generated = datetime.now(timezone.utc).date().isoformat()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = out / "index.html"
    index.write_text(
        _render(rows, sources, generated, config), encoding="utf-8"
    )
    return index


def _paid_cta(config: dict) -> str:
    price = config.get("price", "$15/mo")
    stripe = config.get("stripe_url")
    instagram = config.get("instagram")
    if stripe:
        button = f'<a class="btn" href="{stripe}">Get your list ({price})</a>'
    elif instagram:
        button = (
            f'<a class="btn" href="https://instagram.com/{instagram}">'
            f"DM @{instagram} to start ({price})</a>"
        )
    else:
        button = f'<span class="btn muted">DM me to start ({price})</span>'
    return button


def _email_form(config: dict) -> str:
    action = config.get("email_form_action")
    if not action:
        return ""
    return (
        f'<form class="email" method="post" action="{action}">'
        '<input type="email" name="email" required placeholder="you@school.edu">'
        "<button>Get the weekly top 5</button></form>"
    )


_TEMPLATE_TEXT = """Subject: quick question from a fellow {school} student

Hi {name},

I'm a {program} student at {school} applying to {company}'s {role} posting.
Before I send my application into the pile, I wanted to ask you one thing:
what's the one skill your team actually uses that the posting doesn't mention?

I've built {your most relevant thing, one line, with a number}.

If my profile seems like a fit, I'd appreciate a referral. If not, the answer
to the question above is genuinely useful and I'll get out of your inbox.

Thanks either way,
{you}"""


def _render(rows: list[dict], sources: list[str], generated: str, config: dict) -> str:
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    instagram = config.get("instagram")
    contact = (
        f'<a href="https://instagram.com/{instagram}">@{instagram}</a>'
        if instagram
        else "the owner"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UGMI: every internship and scholarship we can find, free</title>
<meta name="description" content="A live database of internships, scholarships, hackathons and grants for students. Free to browse.">
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: system-ui, sans-serif; line-height: 1.45; }}
main {{ max-width: 880px; margin: 0 auto; padding: 1rem; }}
header h1 {{ margin: 1rem 0 0.25rem; }}
header p.tag {{ margin: 0 0 1rem; opacity: 0.75; }}
.pitch {{ border: 1px solid color-mix(in srgb, currentColor 25%, transparent); border-radius: 8px; padding: 0.9rem 1rem; margin: 1rem 0; }}
.pitch p {{ margin: 0.3rem 0; }}
.btn {{ display: inline-block; margin-top: 0.5rem; padding: 0.45rem 0.9rem; border-radius: 6px; border: 1px solid currentColor; text-decoration: none; color: inherit; font-weight: 600; }}
.btn.muted {{ opacity: 0.6; }}
.email {{ margin-top: 0.6rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }}
.email input {{ flex: 1 1 200px; padding: 0.45rem; }}
details {{ margin: 1rem 0; }}
pre.tpl {{ white-space: pre-wrap; border: 1px dashed color-mix(in srgb, currentColor 30%, transparent); padding: 0.75rem; border-radius: 6px; font-size: 0.85rem; overflow-x: auto; }}
.controls {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0 0.5rem; }}
.controls input {{ flex: 1 1 240px; padding: 0.5rem; }}
.controls select {{ padding: 0.5rem; }}
#count {{ opacity: 0.7; font-size: 0.9rem; margin: 0.25rem 0 0.75rem; }}
.opp {{ border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent); padding: 0.7rem 0; }}
.opp a.t {{ font-weight: 600; text-decoration: none; }}
.opp a.t:hover {{ text-decoration: underline; }}
.opp .meta {{ font-size: 0.85rem; opacity: 0.75; }}
.opp .deadline {{ font-size: 0.85rem; font-weight: 600; }}
#more {{ margin: 1rem 0; padding: 0.5rem 1rem; }}
footer {{ margin: 2rem 0 1rem; font-size: 0.85rem; opacity: 0.75; }}
</style>
</head>
<body>
<main>
<header>
  <h1>UGMI</h1>
  <p class="tag">u gon make it. {len(rows)} live internships, scholarships, hackathons and grants. Free. Updated {generated}.</p>
</header>

<section class="pitch">
  <p><strong>The list below is everything.</strong> You are probably eligible for a fraction of it, and cold applications get a few percent response.</p>
  <p><strong>Paid:</strong> send your resume and 3 lines, get your matched shortlist every week, plus the actual person to contact at each company and a working outreach template.</p>
  {_paid_cta(config)}
  {_email_form(config)}
</section>

<details>
  <summary><strong>Free: the cold outreach template</strong> (works for referrals and coffee chats)</summary>
  <pre class="tpl">{_TEMPLATE_TEXT}</pre>
</details>

<div class="controls">
  <input id="q" type="search" placeholder="search: company, role, term, city…">
  <select id="type"><option value="">all types</option></select>
</div>
<p id="count"></p>
<div id="list"></div>
<button id="more" hidden>Show more</button>

<footer>
  Sources: {", ".join(sources)}. Facts are extracted from the listed pages, never invented; anything a page didn't state is simply blank. Built by {contact}.
</footer>
</main>

<script id="data" type="application/json">{data}</script>
<script>
const ROWS = JSON.parse(document.getElementById("data").textContent);
const PAGE = 200;
const q = document.getElementById("q");
const typeSel = document.getElementById("type");
const list = document.getElementById("list");
const count = document.getElementById("count");
const more = document.getElementById("more");
let filtered = ROWS, shown = 0;

for (const t of [...new Set(ROWS.map(r => r.type))].sort()) {{
  const o = document.createElement("option");
  o.value = t; o.textContent = t;
  typeSel.appendChild(o);
}}

function matches(r, needle) {{
  return [r.title, r.org, r.desc, r.req, r.type, r.src]
    .some(v => v && v.toLowerCase().includes(needle));
}}

function card(r) {{
  const d = document.createElement("div");
  d.className = "opp";
  const a = document.createElement("a");
  a.className = "t"; a.href = r.url; a.target = "_blank"; a.rel = "noopener";
  a.textContent = r.title;
  d.appendChild(a);
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = [r.org, r.desc, r.req].filter(Boolean).join(" · ");
  d.appendChild(meta);
  if (r.deadline) {{
    const dl = document.createElement("div");
    dl.className = "deadline";
    dl.textContent = "deadline: " + r.deadline;
    d.appendChild(dl);
  }}
  return d;
}}

function renderMore() {{
  const next = filtered.slice(shown, shown + PAGE);
  for (const r of next) list.appendChild(card(r));
  shown += next.length;
  more.hidden = shown >= filtered.length;
}}

function apply() {{
  const needle = q.value.trim().toLowerCase();
  const t = typeSel.value;
  filtered = ROWS.filter(r => (!t || r.type === t) && (!needle || matches(r, needle)));
  list.textContent = "";
  shown = 0;
  count.textContent = filtered.length + " of " + ROWS.length;
  renderMore();
}}

q.addEventListener("input", apply);
typeSel.addEventListener("change", apply);
more.addEventListener("click", renderMore);
apply();
</script>
</body>
</html>
"""
