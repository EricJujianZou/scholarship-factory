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
        '<label class="sr-only" for="email">Your school email</label>'
        '<input id="email" type="email" name="email" required '
        'placeholder="you@school.edu">'
        '<button class="btn">Get the weekly top 5</button></form>'
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
:root {{
  --background: oklch(1 0 0);
  --foreground: oklch(0.1788 0.0047 264.45);
  --card: oklch(0.9542 0 0);
  --card-foreground: oklch(0.1788 0.0047 264.45);
  --primary: oklch(0.2244 0.0039 264.49);
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.9619 0 0);
  --muted: oklch(0.9696 0 0);
  --muted-foreground: oklch(0.5547 0 0);
  /* muted text sitting on --card needs to be darker than --muted-foreground
     to clear 4.5:1 against that lighter gray */
  --card-muted-foreground: oklch(0.5 0 0);
  --border: oklch(0.9234 0 0);
  --ring: oklch(0.2244 0.0039 264.49);
  --radius: 0.875rem;
  --radius-sm: 0.5rem;
  --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --sp-2: 8px;
  --sp-3: 12px;
  --sp-4: 16px;
  --sp-6: 24px;
  --sp-8: 32px;
  --sp-12: 48px;
  color-scheme: light;
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0;
  background: var(--background);
  color: var(--foreground);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
}}
main {{ max-width: 960px; margin: 0 auto; padding: 0 var(--sp-4) var(--sp-12); }}
a {{ color: var(--foreground); }}
:focus-visible {{ outline: 2px solid var(--ring); outline-offset: 2px; }}
.sr-only {{
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}}

/* hero */
.hero {{ padding: var(--sp-12) 0 var(--sp-8); }}
.brand {{
  display: inline-block;
  margin: 0 0 var(--sp-6);
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--primary-foreground);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}}
h1 {{
  margin: 0 0 var(--sp-4);
  max-width: 17ch;
  font-size: clamp(2.125rem, 6.5vw, 3.25rem);
  line-height: 1.05;
  letter-spacing: -0.03em;
  font-weight: 700;
}}
.lede {{ margin: 0; max-width: 58ch; font-size: 1.0625rem; color: var(--muted-foreground); }}

/* paid offer */
.offer {{
  margin: 0;
  padding: var(--sp-6);
  background: var(--card);
  color: var(--card-foreground);
  border-radius: var(--radius);
}}
.eyebrow {{
  margin: 0 0 var(--sp-2);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--card-muted-foreground);
}}
.offer h2 {{
  margin: 0 0 var(--sp-3);
  max-width: 22ch;
  font-size: 1.5rem;
  line-height: 1.15;
  letter-spacing: -0.02em;
}}
.offer p {{ margin: 0 0 var(--sp-3); max-width: 62ch; }}
.offer p.sub {{ color: var(--card-muted-foreground); }}

/* buttons and inputs */
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 var(--sp-6);
  border: 1px solid var(--primary);
  border-radius: 999px;
  background: var(--primary);
  color: var(--primary-foreground);
  font: inherit;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: opacity 0.12s ease;
}}
.btn:hover {{ opacity: 0.86; }}
.btn.muted {{
  background: var(--secondary);
  color: var(--card-muted-foreground);
  border-color: var(--border);
  box-shadow: none;
  cursor: default;
}}
.btn.muted:hover {{ opacity: 1; }}
.offer .btn {{ margin-top: var(--sp-2); }}
input, select {{
  min-height: 44px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--background);
  color: var(--foreground);
  font: inherit;
}}
::placeholder {{ color: var(--muted-foreground); opacity: 1; }}
.email {{ display: flex; gap: var(--sp-2); flex-wrap: wrap; margin-top: var(--sp-3); }}
.email input {{ flex: 1 1 240px; }}
.email .btn {{ margin-top: 0; padding: 0 var(--sp-4); }}

/* free template */
.tpl-card {{
  margin: var(--sp-4) 0 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--background);
}}
.tpl-card summary {{
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-height: 44px;
  padding: var(--sp-3) var(--sp-6);
  border-radius: var(--radius);
  font-weight: 600;
  cursor: pointer;
  list-style: none;
}}
.tpl-card summary::-webkit-details-marker {{ display: none; }}
.tpl-card summary::after {{
  content: "+";
  font-size: 1.25rem;
  line-height: 1;
  color: var(--muted-foreground);
}}
.tpl-card[open] summary::after {{ content: "-"; }}
.tpl-card summary .s-title {{ margin-right: auto; }}
.tpl-card summary .hint {{
  font-weight: 400;
  font-size: 0.875rem;
  color: var(--muted-foreground);
}}
.tpl-card[open] summary {{
  border-bottom: 1px solid var(--border);
  border-radius: var(--radius) var(--radius) 0 0;
}}
pre.tpl {{
  margin: 0;
  padding: var(--sp-6);
  background: var(--muted);
  border-radius: 0 0 var(--radius) var(--radius);
  white-space: pre-wrap;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.6;
}}

/* sticky search bar */
.bar {{
  position: sticky;
  top: 0;
  z-index: 5;
  margin: var(--sp-8) calc(var(--sp-4) * -1) var(--sp-4);
  padding: var(--sp-3) var(--sp-4);
  background: var(--background);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-xs);
}}
.controls {{ display: flex; gap: var(--sp-2); flex-wrap: wrap; }}
.controls input {{ flex: 1 1 260px; min-width: 0; }}
.controls select {{ flex: 0 1 190px; }}
#count {{
  margin: var(--sp-2) 0 0;
  min-height: 1.25rem;
  font-size: 0.875rem;
  color: var(--muted-foreground);
}}

/* listings */
#list {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
  gap: var(--sp-3);
}}
.opp {{
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-4);
  background: var(--card);
  color: var(--card-foreground);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: background-color 0.12s ease, border-color 0.12s ease;
}}
.opp:hover {{ background: var(--muted); border-color: var(--foreground); }}
.opp .badge {{
  align-self: flex-start;
  padding: 3px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  color: var(--card-muted-foreground);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.opp a.t {{
  font-size: 1.0625rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--card-foreground);
  text-decoration: none;
  overflow-wrap: anywhere;
}}
.opp a.t:hover {{ text-decoration: underline; }}
.opp .meta {{ font-size: 0.9rem; color: var(--card-muted-foreground); overflow-wrap: anywhere; }}
.opp .deadline {{
  align-self: flex-start;
  margin-top: auto;
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  font-size: 0.8125rem;
  font-weight: 600;
}}
#more {{
  display: block;
  width: 100%;
  min-height: 44px;
  margin: var(--sp-6) 0 0;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  color: var(--foreground);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}}
#more:hover {{ background: var(--muted); border-color: var(--foreground); }}

footer {{
  max-width: 72ch;
  margin-top: var(--sp-12);
  padding-top: var(--sp-6);
  border-top: 1px solid var(--border);
  font-size: 0.875rem;
  color: var(--muted-foreground);
}}
footer p {{ margin: 0 0 var(--sp-2); }}

@media (max-width: 640px) {{
  .hero {{ padding: var(--sp-8) 0 var(--sp-6); }}
  h1 {{ max-width: none; }}
  .offer {{ padding: var(--sp-4); }}
  .tpl-card summary {{ padding: var(--sp-3) var(--sp-4); }}
  .tpl-card summary .hint {{ display: none; }}
  pre.tpl {{ padding: var(--sp-4); }}
  .controls select {{ flex: 1 1 100%; }}
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; }}
}}
</style>
</head>
<body>
<main>
<header class="hero">
  <p class="brand">UGMI</p>
  <h1>Every internship, scholarship, hackathon and grant we can find.</h1>
  <p class="lede">u gon make it. {len(rows)} listings are live right now and all of them are free to browse. Updated {generated}.</p>
</header>

<section class="offer">
  <p class="eyebrow">Paid</p>
  <h2>Get your matched shortlist every week.</h2>
  <p>The list below is everything. You are probably eligible for a fraction of it, and cold applications get a few percent response.</p>
  <p class="sub">Send your resume and 3 lines about yourself. Every week you get your matched shortlist, plus the actual person to contact at each company and a working outreach template.</p>
  {_paid_cta(config)}
  {_email_form(config)}
</section>

<details class="tpl-card">
  <summary><span class="s-title">Free: the cold outreach template</span><span class="hint">works for referrals and coffee chats</span></summary>
  <pre class="tpl">{_TEMPLATE_TEXT}</pre>
</details>

<div class="bar">
  <div class="controls">
    <label class="sr-only" for="q">Search listings</label>
    <input id="q" type="search" placeholder="search: company, role, term, city…">
    <label class="sr-only" for="type">Filter by type</label>
    <select id="type"><option value="">all types</option></select>
  </div>
  <p id="count"></p>
</div>
<div id="list"></div>
<button id="more" hidden>Show more</button>

<footer>
  <p>Sources: {", ".join(sources)}. Facts are extracted from the listed pages, never invented; anything a page didn't state is simply blank.</p>
  <p>Built by {contact}.</p>
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
  if (r.type) {{
    const b = document.createElement("span");
    b.className = "badge";
    b.textContent = r.type;
    d.appendChild(b);
  }}
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
  count.textContent = filtered.length + " of " + ROWS.length + " listings";
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
