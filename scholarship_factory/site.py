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

Design note: two voices carry the page. Anything the owner says is system
sans; anything the scraper produced (org names, types, dates, counts, source
hosts) is uppercase monospace. Exactly two hues do work: --marker highlights
two phrases plus the freshness signals, --ink-blue is only ever interactive
text.
"""
import json
import re
import tomllib
from collections import Counter
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from .store import OpportunityStore

SITE_CONFIG_FILE = "site.toml"

# scraped `type` values are free text; anything outside this set collapses to
# "other" so the badge never grows into a two-line pill
KNOWN_TYPES = frozenset(
    {
        "internship",
        "scholarship",
        "fellowship",
        "grant",
        "hackathon",
        "competition",
        "award",
        "other",
    }
)

_MONTH_DAY_YEAR = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
)


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


def _norm_type(value: str | None) -> str:
    t = (value or "other").strip().lower()
    return t if t in KNOWN_TYPES else "other"


def _parse_date(text: str | None) -> date | None:
    """Only ISO-like and "Month DD, YYYY" deadlines. Deadlines are quoted free
    text, so anything else stays unparsed rather than guessed."""
    if not text:
        return None
    s = text.strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = _MONTH_DAY_YEAR.match(s)
    if not m:
        return None
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt
            ).date()
        except ValueError:
            continue
    return None


def _row(opp) -> dict | None:
    if not opp.apply_url.lower().startswith(("http://", "https://")):
        return None
    return {
        "title": opp.title,
        "org": opp.organization,
        "type": _norm_type(opp.type),
        "desc": opp.description,
        "req": opp.requirements,
        "deadline": opp.deadline,
        "url": opp.apply_url,
        "src": _source_name(opp.source_url),
        # "added": when this row first showed up, which is what the card says
        "seen": (opp.first_seen or opp.last_seen or "")[:10],
    }


def build_site(
    store: OpportunityStore, out_dir: str | Path, *, config: dict | None = None
) -> Path:
    config = config or {}
    rows = [r for r in (_row(o) for o in store.list()) if r is not None]
    rows.sort(key=lambda r: r["seen"], reverse=True)
    sources = sorted({r["src"] for r in rows})
    today = datetime.now(timezone.utc).date()
    generated = today.isoformat()

    for r in rows:
        added = _parse_date(r["seen"])
        r["fresh"] = bool(added and 0 <= (today - added).days <= 7)
        due = _parse_date(r["deadline"])
        r["soon"] = bool(due and 0 <= (due - today).days <= 14)
    if all(r["fresh"] for r in rows):
        # a marker every row wears marks nothing; young database, no signal yet
        for r in rows:
            r["fresh"] = False

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


def _fact(label: str, value: str) -> str:
    return (
        f'<div class="fact"><span class="f-k">{escape(label)}</span>'
        f'<span class="f-v">{escape(value)}</span></div>'
    )


def _facts(rows: list[dict], generated: str) -> str:
    """The scraper's own accounting, in the scraper's voice."""
    parts = ['<p class="f-h">what is in here</p>']
    for t, n in Counter(r["type"] for r in rows).most_common():
        parts.append(_fact(t, f"{n:,}"))
    parts.append('<p class="f-h">where it comes from</p>')
    for s, n in Counter(r["src"] for r in rows).most_common():
        parts.append(_fact(s, f"{n:,}"))
    parts.append('<p class="f-h">last updated</p>')
    parts.append(_fact("utc", generated))
    return "\n  ".join(parts)


def _source_tags(sources: list[str]) -> str:
    return "\n    ".join(
        f'<li class="mono">{escape(s)}</li>' for s in sources
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
    price = config.get("price", "$15/mo")
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
  /* muted text sitting on --primary (the one dark object): 7:1 on that fill */
  --ink-muted-foreground: oklch(0.78 0 0);
  --border: oklch(0.9234 0 0);
  --ring: oklch(0.2244 0.0039 264.49);
  /* exactly two hues, strict roles. --marker is only ever a text wash,
     --ink-blue is only ever interactive text on a light surface. */
  --marker: #FFE24B;
  --ink-blue: #1F4FFF;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --radius: 0.875rem;
  --radius-sm: 0.5rem;
  --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  /* whitespace tiers: 4/8 inside a group, 12 inside a card, 24 within a
     section, 64 between major blocks */
  --sp-1: 4px;
  --sp-2: 8px;
  --sp-3: 12px;
  --sp-4: 16px;
  --sp-5: 20px;
  --sp-6: 24px;
  --sp-8: 32px;
  --sp-16: 64px;
  color-scheme: light;
}}
* {{ box-sizing: border-box; }}
/* beats the display rules below, which would otherwise unhide [hidden] */
[hidden] {{ display: none !important; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0;
  background: var(--background);
  color: var(--foreground);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.5;
}}
main {{ max-width: 960px; margin: 0 auto; padding: 0 var(--sp-4) var(--sp-16); }}
a {{ color: var(--foreground); }}
:focus-visible {{ outline: 2px solid var(--ring); outline-offset: 2px; }}
.sr-only {{
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}}
/* the scraper's voice */
.mono {{
  font-family: var(--mono);
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
/* the highlighter. never a fill, always a wash under the text */
.mark {{
  background-image: linear-gradient(180deg, transparent 55%, var(--marker) 55%);
}}

/* hero */
.hero {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 300px);
  gap: var(--sp-6) var(--sp-8);
  align-items: start;
  /* deliberately tight: the first row of listings has to clear a 900px fold */
  padding: 28px 0 var(--sp-3);
}}
.brand {{
  margin: 0;
  font-size: 1.125rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}}
.tag {{ display: inline-block; margin: var(--sp-1) 0 0; }}
.bignum {{
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  margin: var(--sp-3) 0 var(--sp-2);
}}
.bignum .n {{
  font-size: clamp(3.5rem, 9vw, 6rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 0.88;
  font-variant-numeric: tabular-nums;
}}
.bignum .unit {{ color: var(--muted-foreground); }}
h1 {{
  margin: 0 0 var(--sp-3);
  max-width: 22ch;
  font-size: clamp(1.875rem, 3.4vw, 2.5rem);
  line-height: 1.05;
  letter-spacing: -0.03em;
  font-weight: 800;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.lede {{ margin: 0; max-width: 60ch; font-size: 1.0625rem; color: var(--muted-foreground); }}
/* the scraper's own accounting, filling the hero's right half */
.facts {{ margin: 0; padding-top: var(--sp-2); }}
.facts .f-h {{
  margin: 0 0 var(--sp-2);
  padding-bottom: var(--sp-1);
  border-bottom: 1px solid var(--foreground);
  color: var(--foreground);
}}
.facts .f-h + .fact {{ margin-top: 0; }}
.facts p.f-h ~ p.f-h {{ margin-top: var(--sp-4); }}
.fact {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: 1px 0;
  color: var(--muted-foreground);
}}
.fact .f-k {{ overflow-wrap: anywhere; }}
.fact .f-v {{
  flex: 0 0 auto;
  color: var(--foreground);
  font-variant-numeric: tabular-nums;
}}

/* paid offer: the one high-contrast object on the page */
.offer {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--sp-6) var(--sp-8);
  align-items: end;
  margin: 0;
  padding: var(--sp-5);
  background: var(--primary);
  color: var(--primary-foreground);
  border-radius: var(--radius);
}}
.offer .eyebrow {{
  margin: 0 0 var(--sp-2);
  font-size: 0.875rem;
  color: var(--ink-muted-foreground);
}}
.offer h2 {{
  margin: 0 0 var(--sp-3);
  max-width: 22ch;
  font-size: 1.5rem;
  line-height: 1.15;
  letter-spacing: -0.02em;
  font-weight: 800;
}}
.offer p.sub {{ margin: 0; max-width: 62ch; font-size: 0.9375rem; color: var(--ink-muted-foreground); }}
.buy {{ display: flex; flex-direction: column; align-items: flex-start; gap: var(--sp-3); }}
/* the wash sits on white here because the card behind it is near-black:
   near-black text stays AA on both halves of the slip */
.price {{
  margin: 0;
  padding: 2px 10px;
  background-image: linear-gradient(180deg, var(--background) 55%, var(--marker) 55%);
  color: var(--foreground);
  font-family: var(--mono);
  font-size: 2rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}}

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
/* inside the dark card the CTA inverts */
.offer .btn {{
  background: var(--background);
  border-color: var(--background);
  color: var(--foreground);
}}
.offer .btn.muted {{ background: var(--ink-muted-foreground); border-color: var(--ink-muted-foreground); }}
.offer :focus-visible {{ outline-color: var(--background); }}
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
.email {{ display: flex; gap: var(--sp-2); flex-wrap: wrap; }}
.email input {{ flex: 1 1 200px; }}
.email .btn {{ padding: 0 var(--sp-4); }}

/* free template, kept for the closing block so listings clear the fold */
.tpl-card {{
  margin: 0 0 var(--sp-6);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--background);
}}
.tpl-card summary {{
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-height: 44px;
  padding: var(--sp-3) var(--sp-5);
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
  padding: var(--sp-5);
  background: var(--muted);
  border-radius: 0 0 var(--radius) var(--radius);
  white-space: pre-wrap;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 0.8125rem;
  line-height: 1.6;
}}

/* the rule the whole database runs on, stated right before the data */
.method {{
  margin: var(--sp-3) 0 var(--sp-2);
  font-family: var(--mono);
  font-size: 0.6875rem;
  letter-spacing: 0.04em;
  line-height: 1.6;
  color: var(--muted-foreground);
}}

/* sticky search bar */
.bar {{
  position: sticky;
  top: 0;
  z-index: 5;
  margin: 0 calc(var(--sp-4) * -1) var(--sp-3);
  padding: var(--sp-2) var(--sp-4) var(--sp-3);
  background: var(--background);
  border-bottom: 1px solid transparent;
  transition: border-color 0.12s ease;
}}
.bar.stuck {{
  background: rgba(255, 255, 255, 0.82);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  border-bottom-color: var(--border);
}}
.controls {{ display: flex; align-items: center; gap: var(--sp-2); }}
#q {{
  flex: 1 1 auto;
  min-width: 0;
  height: 52px;
  padding: 0 var(--sp-4);
  font-size: 1.0625rem;
}}
#type {{
  flex: 0 0 auto;
  height: 52px;
  font-family: var(--mono);
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
#count {{
  flex: 0 0 auto;
  margin: 0;
  color: var(--muted-foreground);
  font-variant-numeric: tabular-nums;
}}
#count #count-n {{ color: var(--foreground); }}

/* listings */
#list {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
  align-items: start;
  gap: var(--sp-4);
}}
.opp {{
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-5);
  background: var(--card);
  color: var(--card-foreground);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: background-color 0.12s ease, border-color 0.12s ease,
    box-shadow 0.12s ease;
}}
/* hover inverts the card: white paper, 2px ink edge (drawn as border plus
   inset ring so nothing reflows), title turns interactive */
.opp:hover {{
  background: var(--background);
  border-color: var(--foreground);
  box-shadow: inset 0 0 0 1px var(--foreground);
}}
.opp:hover a.t {{ color: var(--ink-blue); text-decoration: underline; }}
.opp-top {{
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  color: var(--card-muted-foreground);
}}
.opp .org {{ overflow-wrap: anywhere; }}
.opp .badge {{
  flex: 0 0 auto;
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid var(--card-muted-foreground);
  border-radius: 999px;
  white-space: nowrap;
}}
.opp a.t {{
  font-size: 1.125rem;
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--card-foreground);
  text-decoration: none;
  overflow-wrap: anywhere;
}}
.opp .meta {{
  font-size: 0.875rem;
  line-height: 1.45;
  color: var(--card-muted-foreground);
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.opp-foot {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-1) var(--sp-3);
  margin-top: var(--sp-2);
  color: var(--card-muted-foreground);
}}
.opp .deadline {{ color: var(--card-foreground); font-weight: 600; }}
.opp .deadline.soon, .opp .new {{ color: var(--foreground); }}
#more, #clear {{
  display: block;
  min-height: 44px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  color: var(--foreground);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}}
#more {{ width: 100%; margin: var(--sp-6) 0 0; }}
#clear {{ padding: 0 var(--sp-6); }}
#more:hover, #clear:hover {{ background: var(--muted); border-color: var(--foreground); }}
#empty {{ padding: var(--sp-8) 0; }}
#empty p {{ margin: 0 0 var(--sp-4); max-width: 46ch; font-size: 1.0625rem; }}
#done {{ margin: var(--sp-6) 0 0; font-size: 1.0625rem; color: var(--muted-foreground); }}

/* closing block */
footer {{
  margin-top: var(--sp-16);
  padding-top: var(--sp-6);
  border-top: 1px solid var(--foreground);
}}
footer a {{ color: var(--ink-blue); }}
footer a.btn {{ color: var(--primary-foreground); }}
footer .f-cta {{
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-4);
  margin: 0 0 var(--sp-6);
  max-width: 60ch;
  font-size: 1.0625rem;
  font-weight: 600;
}}
footer .credit {{ margin: 0 0 var(--sp-6); max-width: 60ch; color: var(--muted-foreground); }}
footer .f-h {{ margin: 0 0 var(--sp-2); color: var(--muted-foreground); }}
footer .tags {{
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}}
footer .tags li {{
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--card-muted-foreground);
}}

@media (max-width: 860px) {{
  .hero {{ grid-template-columns: minmax(0, 1fr); }}
  .offer {{ grid-template-columns: minmax(0, 1fr); align-items: start; }}
}}
@media (max-width: 640px) {{
  .hero {{ padding: var(--sp-6) 0 var(--sp-4); }}
  h1 {{ max-width: none; }}
  .offer {{ padding: var(--sp-5); }}
  .tpl-card summary {{ padding: var(--sp-3) var(--sp-4); }}
  .tpl-card summary .hint {{ display: none; }}
  pre.tpl {{ padding: var(--sp-4); }}
  #q, #type {{ height: 44px; }}
  #q {{ padding: 0 var(--sp-3); font-size: 1rem; }}
  #type {{ padding: 0 var(--sp-1); max-width: 108px; }}
  /* the readout keeps a unit when the full "of N listings" will not fit */
  .count-tail {{ display: none; }}
  #count::after {{ content: " shown"; }}
}}
@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; }}
}}
</style>
</head>
<body>
<main>
<header class="hero">
  <div>
    <p class="brand">UGMI</p>
    <p class="mono mark tag">u gon make it</p>
    <p class="bignum"><span class="n">{len(rows):,}</span><span class="mono unit">listings live</span></p>
    <h1>Every internship, scholarship, hackathon and grant we can find.</h1>
    <p class="lede">All of it is free to browse. No account, no email, no paywall on the list.</p>
  </div>
  <aside class="facts mono">
  {_facts(rows, generated)}
  </aside>
</header>

<section class="offer">
  <div>
    <p class="eyebrow">You send a resume once and get a shortlist every week.</p>
    <h2>Get your matched shortlist every week.</h2>
    <p class="sub">The list below is everything, and you are eligible for a fraction of it. Send your resume and 3 lines about yourself. Every week you get your matched shortlist, plus the actual person to contact at each company and a working outreach template.</p>
  </div>
  <div class="buy">
    <p class="price">{price}</p>
    {_paid_cta(config)}
    {_email_form(config)}
  </div>
</section>

<p class="method">Facts are extracted from the listed pages, never invented; anything a page didn't state is simply blank.</p>

<div class="bar">
  <div class="controls">
    <label class="sr-only" for="q">Search listings</label>
    <input id="q" type="search" placeholder="search: company, role, term, city…">
    <label class="sr-only" for="type">Filter by type</label>
    <select id="type"><option value="">all types</option></select>
    <p id="count" class="mono"><span id="count-n"></span><span id="count-tail" class="count-tail"></span></p>
  </div>
</div>
<div id="list"></div>
<div id="empty" hidden>
  <p>Nothing matched that. The database is big but it is not magic. Try a shorter word.</p>
  <button id="clear" type="button">Clear the search</button>
</div>
<button id="more" type="button" hidden>Show more</button>
<p id="done" hidden></p>

<footer>
  <details class="tpl-card">
    <summary><span class="s-title">Free: the cold outreach template</span><span class="hint">works for referrals and coffee chats</span></summary>
    <pre class="tpl">{_TEMPLATE_TEXT}</pre>
  </details>
  <p class="f-cta">Want this filtered down to the ones you can actually win? {_paid_cta(config)}</p>
  <p class="credit">Built by one Waterloo student who got tired of 40 tabs. {contact}</p>
  <p class="mono f-h">sources</p>
  <ul class="tags">
    {_source_tags(sources)}
  </ul>
</footer>
</main>

<script id="data" type="application/json">{data}</script>
<script>
const ROWS = JSON.parse(document.getElementById("data").textContent);
const PAGE = 200;
const q = document.getElementById("q");
const typeSel = document.getElementById("type");
const list = document.getElementById("list");
const countN = document.getElementById("count-n");
const countTail = document.getElementById("count-tail");
const more = document.getElementById("more");
const done = document.getElementById("done");
const empty = document.getElementById("empty");
const clearBtn = document.getElementById("clear");
const bar = document.querySelector(".bar");
let filtered = ROWS, shown = 0;

for (const t of [...new Set(ROWS.map(r => r.type))].sort()) {{
  const o = document.createElement("option");
  o.value = t; o.textContent = t;
  typeSel.appendChild(o);
}}

function el(tag, cls, text) {{
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  return n;
}}

function matches(r, needle) {{
  return [r.title, r.org, r.desc, r.req, r.type, r.src]
    .some(v => v && v.toLowerCase().includes(needle));
}}

function card(r) {{
  const d = el("div", "opp");
  const top = el("div", "opp-top");
  if (r.org) top.appendChild(el("span", "mono org", r.org));
  // the badge only earns its space when it says something new
  if (r.type && r.type !== "internship") top.appendChild(el("span", "mono badge", r.type));
  if (top.childNodes.length) d.appendChild(top);
  const a = el("a", "t", r.title);
  a.href = r.url; a.target = "_blank"; a.rel = "noopener";
  d.appendChild(a);
  const meta = [r.desc, r.req].filter(Boolean).join(" · ");
  if (meta) d.appendChild(el("div", "meta", meta));
  const foot = el("div", "opp-foot");
  if (r.deadline) {{
    foot.appendChild(el("span", "mono deadline" + (r.soon ? " soon mark" : ""),
      "deadline " + r.deadline));
  }}
  if (r.seen) foot.appendChild(el("span", "mono added", "added " + r.seen));
  if (r.fresh) foot.appendChild(el("span", "mono new mark", "new"));
  if (foot.childNodes.length) d.appendChild(foot);
  return d;
}}

function renderMore() {{
  const next = filtered.slice(shown, shown + PAGE);
  for (const r of next) list.appendChild(card(r));
  shown += next.length;
  const left = filtered.length - shown;
  more.textContent = "Show " + Math.min(PAGE, left) + " more, " + left.toLocaleString() + " left";
  more.hidden = left <= 0;
  done.textContent = "That is all " + filtered.length.toLocaleString() + ". Go apply to something.";
  done.hidden = !(filtered.length > 0 && left <= 0);
}}

function apply() {{
  const needle = q.value.trim().toLowerCase();
  const t = typeSel.value;
  filtered = ROWS.filter(r => (!t || r.type === t) && (!needle || matches(r, needle)));
  list.textContent = "";
  shown = 0;
  countN.textContent = filtered.length.toLocaleString();
  countTail.textContent = " of " + ROWS.length.toLocaleString() + " listings";
  empty.hidden = filtered.length > 0;
  renderMore();
}}

q.addEventListener("input", apply);
typeSel.addEventListener("change", apply);
more.addEventListener("click", renderMore);
clearBtn.addEventListener("click", () => {{
  q.value = ""; typeSel.value = ""; apply(); q.focus();
}});
addEventListener("scroll", () => {{
  bar.classList.toggle("stuck", bar.getBoundingClientRect().top <= 0);
}}, {{ passive: true }});
apply();
</script>
</body>
</html>
"""
