"""Static public site export (ugmi.com).

`sf site` reads the store and writes one self-contained `index.html`: no
server, no API key, no live database anywhere near the internet. The page
embeds the opportunity rows as JSON and filters them client-side. Facts only,
same rule as the dashboard: the public site never shows personalization
(relevance scores are the owner's own judgments about one applicant) and
never writes anything.

Optional `site.toml` at the repo root configures the storefront pieces:

    stripe_url = "https://buy.stripe.com/..."   # the paid CTA becomes a link
    instagram = "sleppyeric"                     # DM path + footer credit
    price = "$15/mo"
    email_form_action = "https://..."            # email capture form POST target

Anything missing degrades honestly: no stripe_url means the CTA says "DM me",
no email_form_action means no email box rather than a dead one.

Untrusted input note: titles, descriptions and URLs come from scraped pages.
Everything dynamic is rendered via `textContent`, the JSON embed escapes
`</`, and apply URLs are dropped server-side unless they are http(s).

Copy note: the headline is generated from the corpus, never hardcoded. Only
types the database actually carries in volume get named, so the page cannot
promise a category it does not have.

Design note: two voices carry the page. Anything the owner says is system
sans; anything the scraper produced (org names, types, dates, counts, source
hosts) is uppercase monospace. Exactly two hues do work: --marker highlights
two phrases plus the saved marker, --ink-blue is only ever interactive text.
"""
import json
import re
import tomllib
from collections import Counter
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from .logos import OrgLogoStore, normalize_org
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

# a type has to carry this many rows before the headline is allowed to name it
HEADLINE_MIN = 20

_MONTH_DAY_YEAR = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
)

# adapters write "<category> internship. Term: A, B. Location: C, D"; terms
# never contain a period and Location is always last
_TERM_RE = re.compile(r"Term:\s*([^.]*)")
_LOC_RE = re.compile(r"Location:\s*(.+)\Z", re.S)

_DM_MESSAGE = (
    "hey, I want the weekly list. I'm a [year] [program] student, I'm "
    "looking for [Summer 2027], I can work in [Canada], and I'll send my "
    "resume."
)


def load_site_config(path: str | Path = SITE_CONFIG_FILE) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text(encoding="utf-8"))


#: community boards served off raw.githubusercontent.com, by repo owner;
#: anything else there is Simplify, whose repo name changes every season
_GITHUB_BOARDS = {
    "vanshb03": "Vansh (github.com/vanshb03)",
    "zshah101": "zshah101 (github.com/zshah101)",
}


def _source_name(source_url: str) -> str:
    host = urlparse(source_url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host == "raw.githubusercontent.com":
        owner = urlparse(source_url).path.lstrip("/").split("/", 1)[0].lower()
        return _GITHUB_BOARDS.get(owner, "Simplify (github.com/SimplifyJobs)")
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


def _terms(desc: str | None) -> list[str]:
    """The terms an internship listing states, e.g. ["Summer 2027"]."""
    m = _TERM_RE.search(desc or "")
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def _location(desc: str | None) -> str:
    """The location string a listing states, verbatim and unsplit: the parts
    of "San Jose, CA" are not two places."""
    m = _LOC_RE.search(desc or "")
    return m.group(1).strip() if m else ""


def _row(opp, logos: dict[str, str] | None = None) -> dict | None:
    if not opp.apply_url.lower().startswith(("http://", "https://")):
        return None
    norm_type = _norm_type(opp.type)
    org_key = normalize_org(opp.organization)
    return {
        "title": opp.title,
        "org": opp.organization,
        "type": norm_type,
        "desc": opp.description,
        "req": opp.requirements,
        "deadline": opp.deadline,
        # pay only means pay on internship rows; a scholarship's reward is not a wage
        "pay": opp.reward if norm_type == "internship" else None,
        "logo": (logos or {}).get(org_key) if org_key else None,
        "url": opp.apply_url,
        "src": _source_name(opp.source_url),
        # facets, parsed out of the description the adapter assembled
        "term": _terms(opp.description),
        "loc": _location(opp.description),
        # "added": when this row first showed up, which is what the card says
        "seen": (opp.first_seen or opp.last_seen or "")[:10],
    }


def export_rows(
    store: OpportunityStore, *, config: dict | None = None
) -> list[dict]:
    """The site's row dicts, newest first, with `due`/`soon` computed.

    Sources listed in the config's `retired_sources` are excluded: the owner
    retired them from the public page (2026-08-06) but their rows stay in
    the DB, so every export has to re-apply the exclusion.
    """
    if config is None:
        config = load_site_config()
    retired = tuple(config.get("retired_sources", []))
    logos = OrgLogoStore(store.db_path).all()
    rows = [
        r
        for r in (
            _row(o, logos)
            for o in store.list()
            if not any(h in o.source_url for h in retired)
        )
        if r is not None
    ]
    rows.sort(key=lambda r: r["seen"], reverse=True)
    today = datetime.now(timezone.utc).date()

    for r in rows:
        due = _parse_date(r["deadline"])
        r["soon"] = bool(due and 0 <= (due - today).days <= 14)
        # sort key: only deadlines that are real, parseable and not already past
        r["due"] = due.isoformat() if due and due >= today else None
    return rows


def _encode_data(rows: list[dict]) -> str:
    return json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")


_DATA_OPEN = b'<script id="data" type="application/json">'
_DATA_CLOSE = b"</script>"


def splice_site_data(index_path: str | Path, store: OpportunityStore) -> int:
    """Regenerate ONLY the embedded row-data line inside an existing index.html.

    The live site is a hand-maintained index.html in a separate deploy repo;
    its row data is one `<script id="data" ...>[...]</script>` line. This
    replaces the JSON payload between those markers and leaves every other
    byte of the file untouched (including newline style). Returns the number
    of rows written; raises ValueError when the marker is missing.
    """
    path = Path(index_path)
    raw = path.read_bytes()
    open_at = raw.find(_DATA_OPEN)
    if open_at == -1:
        raise ValueError(f"no {_DATA_OPEN.decode()} marker in {path}")
    payload_at = open_at + len(_DATA_OPEN)
    close_at = raw.find(_DATA_CLOSE, payload_at)
    if close_at == -1:
        raise ValueError(f"data script never closes in {path}")

    rows = export_rows(store)
    payload = _encode_data(rows).encode("utf-8")
    path.write_bytes(raw[:payload_at] + payload + raw[close_at:])
    return len(rows)


def build_site(
    store: OpportunityStore, out_dir: str | Path, *, config: dict | None = None
) -> Path:
    config = config or {}
    rows = export_rows(store)
    sources = sorted({r["src"] for r in rows})
    generated = datetime.now(timezone.utc).date().isoformat()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = out / "index.html"
    index.write_text(
        _render(rows, sources, generated, config), encoding="utf-8"
    )
    return index


def _plural(word: str, n: int) -> str:
    return word if n == 1 else word + "s"


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _type_counts(rows: list[dict]) -> list[tuple[str, int]]:
    """Named types only. "other" is a bucket, not a category, so it never
    appears in prose."""
    return [
        (t, n)
        for t, n in Counter(r["type"] for r in rows).most_common()
        if t != "other"
    ]


def _headline(rows: list[dict]) -> str:
    """Only types the corpus carries in volume. The page cannot promise
    hackathons it does not have."""
    major = [t for t, n in _type_counts(rows) if n >= HEADLINE_MIN]
    if not major:
        return "Everything we can find, in one searchable list."
    return f"Every {_join(major)} we can find, in one searchable list."


def _also_line(rows: list[dict]) -> str:
    """The smaller types, folded in with their real counts."""
    minor = [(t, n) for t, n in _type_counts(rows) if n < HEADLINE_MIN]
    if not minor:
        return ""
    return (
        "Also in here: "
        + _join([f"{n:,} {_plural(t, n)}" for t, n in minor])
        + "."
    )


def _newest(rows: list[dict]) -> str:
    return max((r["seen"] for r in rows if r["seen"]), default="")


def _paid_cta(config: dict) -> str:
    price = config.get("price", "$15/mo")
    stripe = config.get("stripe_url")
    instagram = config.get("instagram")
    if stripe:
        button = f'<a class="btn" href="{stripe}">Get your list ({price})</a>'
    elif instagram:
        button = (
            f'<a class="btn" href="https://ig.me/m/{instagram}">'
            f"DM @{instagram} to start ({price})</a>"
        )
    else:
        button = f'<span class="btn muted">DM me to start ({price})</span>'
    return button


def _dm_block(config: dict) -> str:
    """The other way in. ig.me/m/ opens a message thread; the profile URL
    just opens a profile and the person has to find the button themselves."""
    instagram = config.get("instagram")
    if not instagram:
        return ""
    lead = ""
    if config.get("stripe_url"):
        # without stripe the CTA button is already the DM, so no second line
        lead = (
            f'<p class="dm">or <a href="https://ig.me/m/{instagram}">'
            f"DM @{instagram}</a> first if you have questions</p>"
        )
    return (
        f"{lead}"
        '<div class="msg">'
        '<p class="msg-h">Not sure what to say? Copy this.</p>'
        f'<p class="msg-t" id="msg-text">{escape(_DM_MESSAGE)}</p>'
        '<button class="copy" id="copy-msg" type="button">'
        "Copy the message</button>"
        "</div>"
    )


def _email_form(config: dict) -> str:
    action = config.get("email_form_action")
    if not action:
        return ""
    return (
        '<p class="sub">I send five new ones every Sunday. Not matched to '
        "you, just the five best that opened that week. Free, and no other "
        "emails.</p>"
        f'<form class="email" method="post" action="{action}">'
        '<label class="sr-only" for="email">Your email</label>'
        '<input id="email" type="email" name="email" required '
        'placeholder="your email">'
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
    parts.append('<p class="f-h">freshness</p>')
    # two different claims: when the page was made, and how new the data is
    parts.append(_fact("built", generated))
    parts.append(_fact("newest listing", _newest(rows) or "none yet"))
    return "\n  ".join(parts)


def _facts_summary(rows: list[dict], sources: list[str]) -> str:
    """Two lines, which is all the panel shows on a phone."""
    newest = _newest(rows) or "none yet"
    return (
        f'<span>{len(rows):,} listings from {len(sources)} '
        f"{_plural('source', len(sources))}</span>"
        f"<span>newest listing {escape(newest)}</span>"
    )


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


def _nudge(config: dict) -> str:
    """Shown only after the visitor has revealed intent (searched a few times
    or saved a couple of listings)."""
    instagram = config.get("instagram")
    dm = (
        f' or <a href="https://ig.me/m/{instagram}">DM @{instagram}</a>'
        if instagram
        else ""
    )
    return (
        '<div id="nudge" class="nudge" hidden>'
        "<p>You are digging. I do this filtering by hand for people every "
        f'week. <a href="#offer">See what that is</a>{dm}.</p>'
        "</div>"
    )


def _render(rows: list[dict], sources: list[str], generated: str, config: dict) -> str:
    data = _encode_data(rows)
    instagram = config.get("instagram")
    contact = (
        f'<a href="https://instagram.com/{instagram}">@{instagram}</a>'
        if instagram
        else "the owner"
    )
    price = config.get("price", "$15/mo")
    headline = _headline(rows)
    also = _also_line(rows)
    meta_desc = " ".join(
        p
        for p in (
            headline,
            also,
            "Free to browse, no account and no email.",
        )
        if p
    )
    lede = (
        (also + " " if also else "")
        + "Free to browse. No account, no email, no paywall on the list. "
        + "There is a paid thing further down. The list is not it."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UGMI: {escape(headline)}</title>
<meta name="description" content="{escape(meta_desc)}">
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
/* on a phone the whole panel folds down to its two-line summary */
.facts-d > summary {{
  display: none;
  flex-direction: column;
  gap: 2px;
  min-height: 44px;
  padding: var(--sp-2) 0;
  color: var(--muted-foreground);
  cursor: pointer;
  list-style: none;
}}
.facts-d > summary::-webkit-details-marker {{ display: none; }}

/* paid offer: the one high-contrast object on the page */
.offer {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 340px);
  gap: var(--sp-6) var(--sp-8);
  align-items: start;
  margin: var(--sp-16) 0 var(--sp-6);
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
.offer p.sub + p.sub {{ margin-top: var(--sp-3); }}
.buy {{ display: flex; flex-direction: column; align-items: flex-start; gap: var(--sp-3); }}
.buy > * {{ max-width: 100%; }}
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
.dm {{ margin: 0; font-size: 0.9375rem; color: var(--ink-muted-foreground); }}
.dm a {{ color: var(--primary-foreground); }}
.msg {{
  width: 100%;
  padding: var(--sp-3);
  border: 1px solid var(--ink-muted-foreground);
  border-radius: var(--radius-sm);
}}
.msg-h {{ margin: 0 0 var(--sp-2); font-size: 0.9375rem; font-weight: 600; }}
.msg-t {{
  margin: 0 0 var(--sp-3);
  font-family: var(--mono);
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--ink-muted-foreground);
  overflow-wrap: anywhere;
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
.copy {{
  min-height: 44px;
  padding: 0 var(--sp-4);
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  color: var(--foreground);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}}
.copy:hover {{ background: var(--muted); border-color: var(--foreground); }}
.offer .copy {{
  background: transparent;
  border-color: var(--ink-muted-foreground);
  color: var(--primary-foreground);
}}
.offer .copy:hover {{ background: transparent; border-color: var(--background); }}
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

/* free template, sitting with the offer under the database */
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
  white-space: pre-wrap;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 0.8125rem;
  line-height: 1.6;
}}
.tpl-foot {{
  padding: var(--sp-3) var(--sp-5);
  background: var(--muted);
  border-radius: 0 0 var(--radius) var(--radius);
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
.method.note {{ margin: 0 0 var(--sp-3); }}

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
#sort {{
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
/* one row of one-tap filters, scrolled sideways rather than wrapped so the
   sticky bar never eats the fold */
.chips {{
  display: flex;
  gap: var(--sp-2);
  margin-top: var(--sp-2);
  overflow-x: auto;
  scrollbar-width: none;
  /* the fade is the only honest way to say "there are more of these" */
  -webkit-mask-image: linear-gradient(to right, #000 92%, transparent);
  mask-image: linear-gradient(to right, #000 92%, transparent);
}}
.chips::-webkit-scrollbar {{ display: none; }}
.chip {{
  flex: 0 0 auto;
  min-height: 44px;
  padding: 0 var(--sp-4);
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--background);
  color: var(--foreground);
  font-family: var(--mono);
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}}
/* on a phone the readout moves down here so the search box keeps its width */
.chips #count {{ align-self: center; }}
.chip:hover {{ border-color: var(--foreground); }}
.chip[aria-pressed="true"] {{
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-foreground);
}}

/* the quiet offer bar, shown only once someone has revealed intent */
.nudge {{
  margin: 0 0 var(--sp-4);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--muted-foreground);
}}
.nudge p {{ margin: 0; }}
.nudge a {{ color: var(--ink-blue); }}

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
  align-items: center;
  gap: var(--sp-1) var(--sp-3);
  margin-top: var(--sp-2);
  color: var(--card-muted-foreground);
}}
.opp .deadline {{ color: var(--card-foreground); font-weight: 600; }}
.opp .deadline.soon {{ color: var(--foreground); }}
.opp .save {{
  margin-left: auto;
  min-height: 44px;
  padding: 0 var(--sp-2);
  border: 0;
  background: none;
  color: var(--card-muted-foreground);
  cursor: pointer;
}}
.opp .save[aria-pressed="true"] {{ color: var(--foreground); }}
.opp .save[aria-pressed="true"] .save-t {{
  background-image: linear-gradient(180deg, transparent 55%, var(--marker) 55%);
}}
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
  .offer {{ grid-template-columns: minmax(0, 1fr); }}
}}
@media (max-width: 640px) {{
  .hero {{ padding: var(--sp-6) 0 var(--sp-4); }}
  h1 {{ max-width: none; }}
  .facts-d > summary {{ display: flex; }}
  .offer {{ padding: var(--sp-5); }}
  .tpl-card summary {{ padding: var(--sp-3) var(--sp-4); }}
  .tpl-card summary .hint {{ display: none; }}
  pre.tpl {{ padding: var(--sp-4); }}
  .tpl-foot {{ padding: var(--sp-3) var(--sp-4); }}
  #q, #sort {{ height: 44px; }}
  #q {{ padding: 0 var(--sp-3); font-size: 1rem; }}
  #sort {{ padding: 0 var(--sp-1); max-width: 108px; }}
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
    <h1>{escape(headline)}</h1>
    <p class="lede">{escape(lede)}</p>
  </div>
  <aside class="facts mono">
    <details class="facts-d" id="facts-d" open>
      <summary>{_facts_summary(rows, sources)}</summary>
      <div class="facts-body">
  {_facts(rows, generated)}
      </div>
    </details>
  </aside>
</header>

<p class="method">Facts are extracted from the listed pages, never invented; anything a page didn't state is simply blank.</p>

<div class="bar">
  <div class="controls">
    <label class="sr-only" for="q">Search listings</label>
    <input id="q" type="search" placeholder="search: company, role, term, city…">
    <label class="sr-only" for="sort">Sort listings</label>
    <select id="sort">
      <option value="deadline">soonest deadline</option>
      <option value="new">newest</option>
      <option value="az">A to Z</option>
    </select>
    <p id="count" class="mono"><span id="count-n"></span><span id="count-tail" class="count-tail"></span></p>
  </div>
  <div id="chips" class="chips" role="group" aria-label="Filter listings"></div>
</div>
<p id="since-note" class="method note" hidden></p>
<p id="save-note" class="method note" hidden>Saved on this device only. Clearing your browser clears this.</p>
{_nudge(config)}
<div id="list"></div>
<div id="empty" hidden>
  <p>Nothing matched all of those words. Try dropping one.</p>
  <button id="clear" type="button">Clear the search</button>
</div>
<button id="more" type="button" hidden>Show more</button>
<p id="done" hidden></p>

<section class="offer" id="offer">
  <div>
    <p class="eyebrow">You send a resume once and get a shortlist every week.</p>
    <h2>Get your matched shortlist every week.</h2>
    <p class="sub">The list above is everything, and you are eligible for a fraction of it. Send your resume and 3 lines about yourself. Every week you get your matched shortlist, plus the actual person to contact at each company and a working outreach template.</p>
    <p class="sub">I read these myself. It is one person, so give me up to 48 hours.</p>
  </div>
  <div class="buy">
    <p class="price">{price}</p>
    {_paid_cta(config)}
    {_dm_block(config)}
    {_email_form(config)}
  </div>
</section>

<details class="tpl-card">
  <summary><span class="s-title">Free: the cold outreach template</span><span class="hint">works for referrals and coffee chats</span></summary>
  <pre class="tpl" id="tpl-text">{_TEMPLATE_TEXT}</pre>
  <div class="tpl-foot">
    <button class="copy" id="copy-tpl" type="button">Copy the template</button>
  </div>
</details>

<footer>
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
const PAGE_FIRST = 24;
const PAGE = 200;
// typed shorthand, expanded per token before matching
const SYN = new Map([
  ["swe", "software engineer"],
  ["sde", "software engineer"],
  ["pm", "product manager"],
  ["ds", "data science"],
  ["ml", "machine learning"]
]);
const SAVED_KEY = "ugmi.saved";
const VISIT_KEY = "ugmi.lastVisit";
const TODAY = new Date().toISOString().slice(0, 10);

const q = document.getElementById("q");
const sortSel = document.getElementById("sort");
const chipRow = document.getElementById("chips");
const list = document.getElementById("list");
const countN = document.getElementById("count-n");
const countTail = document.getElementById("count-tail");
const more = document.getElementById("more");
const done = document.getElementById("done");
const empty = document.getElementById("empty");
const clearBtn = document.getElementById("clear");
const bar = document.querySelector(".bar");
const sinceNote = document.getElementById("since-note");
const saveNote = document.getElementById("save-note");
const nudge = document.getElementById("nudge");
const factsD = document.getElementById("facts-d");

// one lowercased haystack per row, built once
let NEWEST = "";
for (const r of ROWS) {{
  r.blob = [r.title, r.org, r.desc, r.req, r.type, r.src]
    .filter(Boolean).join(" ").toLowerCase();
  r.locLower = (r.loc || "").toLowerCase();
  if (r.seen && r.seen > NEWEST) NEWEST = r.seen;
}}

function lsGet(k) {{ try {{ return localStorage.getItem(k); }} catch (e) {{ return null; }} }}
function lsSet(k, v) {{ try {{ localStorage.setItem(k, v); }} catch (e) {{}} }}

let saved = new Set();
try {{
  const raw = JSON.parse(lsGet(SAVED_KEY) || "[]");
  if (Array.isArray(raw)) saved = new Set(raw.filter(x => typeof x === "string"));
}} catch (e) {{}}

let filtered = ROWS, shown = 0, searches = 0, lastCounted = "";
const chips = [];

function el(tag, cls, text) {{
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  return n;
}}

function addChip(label, group, test) {{
  const b = el("button", "chip mono", label);
  b.type = "button";
  b.setAttribute("aria-pressed", "false");
  b.dataset.group = group || "";
  b.test = test;
  b.addEventListener("click", () => {{
    const on = b.getAttribute("aria-pressed") === "true";
    if (!on && b.dataset.group) {{
      for (const c of chips) {{
        if (c !== b && c.dataset.group === b.dataset.group) {{
          c.setAttribute("aria-pressed", "false");
        }}
      }}
    }}
    b.setAttribute("aria-pressed", on ? "false" : "true");
    apply();
  }});
  chips.push(b);
  chipRow.appendChild(b);
  return b;
}}

// saved first: it is the only chip about you
const savedChip = addChip("saved (0)", "", r => saved.has(r.url));

function refreshSaved() {{
  savedChip.textContent = "saved (" + saved.size.toLocaleString() + ")";
  savedChip.hidden = saved.size === 0;
  if (saved.size === 0) savedChip.setAttribute("aria-pressed", "false");
  saveNote.hidden = saved.size === 0;
}}

// "added since your last visit", with a guard: a bulk import is not news
const prevVisit = lsGet(VISIT_KEY);
lsSet(VISIT_KEY, TODAY);
if (prevVisit) {{
  const fresh = ROWS.filter(r => r.seen && r.seen > prevVisit);
  if (fresh.length > 0 && fresh.length < 400) {{
    addChip(fresh.length.toLocaleString() + " added since " + prevVisit, "",
      r => r.seen && r.seen > prevVisit);
  }} else if (fresh.length >= 400) {{
    sinceNote.textContent = "the list was rebuilt on " + NEWEST;
    sinceNote.hidden = false;
  }}
}}

// facets, counted off the rows that actually loaded
const termCount = new Map();
let noTerm = 0;
for (const r of ROWS) {{
  const ts = r.term || [];
  if (!ts.length) noTerm++;
  for (const t of ts) termCount.set(t, (termCount.get(t) || 0) + 1);
}}
for (const [t, n] of [...termCount.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4)) {{
  addChip(t + " (" + n.toLocaleString() + ")", "term",
    r => (r.term || []).indexOf(t) !== -1);
}}
if (noTerm) {{
  // never let unparsed rows vanish behind a facet nobody offered
  addChip("term not stated (" + noTerm.toLocaleString() + ")", "term",
    r => !(r.term || []).length);
}}
for (const [label, hit] of [["remote", "remote"], ["canada", "canada"]]) {{
  const n = ROWS.filter(r => r.locLower.indexOf(hit) !== -1).length;
  if (n) addChip(label + " (" + n.toLocaleString() + ")", "",
    r => r.locLower.indexOf(hit) !== -1);
}}
const typeCount = new Map();
for (const r of ROWS) {{
  if (r.type && r.type !== "internship") typeCount.set(r.type, (typeCount.get(r.type) || 0) + 1);
}}
for (const [t, n] of [...typeCount.entries()].sort((a, b) => b[1] - a[1])) {{
  if (n >= 10) addChip(t + " (" + n.toLocaleString() + ")", "type", r => r.type === t);
}}

function escRe(s) {{
  return s.replace(/[^a-z0-9]/gi, m => "\\\\" + m);
}}

function tokenTest(t) {{
  if (t.length <= 2) {{
    // two letters match too much as a substring, so demand a whole word
    const re = new RegExp("\\\\b" + escRe(t) + "\\\\b");
    return b => re.test(b);
  }}
  return b => b.indexOf(t) !== -1;
}}

function sortRows(rs) {{
  const mode = sortSel.value;
  const byTitle = (a, b) => a.title.localeCompare(b.title);
  const byNew = (a, b) => (b.seen || "").localeCompare(a.seen || "") || byTitle(a, b);
  if (mode === "az") return rs.slice().sort(byTitle);
  if (mode === "new") return rs.slice().sort(byNew);
  return rs.slice().sort((a, b) => {{
    const ad = a.due || "", bd = b.due || "";
    if (ad && bd) return ad === bd ? byNew(a, b) : (ad < bd ? -1 : 1);
    if (ad) return -1;
    if (bd) return 1;
    return byNew(a, b);
  }});
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
  const sv = el("button", "save mono");
  sv.type = "button";
  const svText = el("span", "save-t", "save");
  sv.appendChild(svText);
  function paintSave() {{
    const on = saved.has(r.url);
    sv.setAttribute("aria-pressed", on ? "true" : "false");
    sv.setAttribute("aria-label", (on ? "Remove from saved: " : "Save: ") + r.title);
    svText.textContent = on ? "saved" : "save";
  }}
  paintSave();
  sv.addEventListener("click", () => {{
    if (saved.has(r.url)) saved.delete(r.url); else saved.add(r.url);
    lsSet(SAVED_KEY, JSON.stringify([...saved]));
    paintSave();
    refreshSaved();
    maybeNudge();
    if (savedChip.getAttribute("aria-pressed") === "true") apply();
  }});
  foot.appendChild(sv);
  d.appendChild(foot);
  return d;
}}

function renderMore() {{
  const size = shown === 0 ? PAGE_FIRST : PAGE;
  const next = filtered.slice(shown, shown + size);
  for (const r of next) list.appendChild(card(r));
  shown += next.length;
  const left = filtered.length - shown;
  more.textContent = "Show " + Math.min(PAGE, left) + " more, " + left.toLocaleString() + " left";
  more.hidden = left <= 0;
  done.textContent = "That is all " + filtered.length.toLocaleString() + ". Go apply to something.";
  done.hidden = !(filtered.length > 0 && left <= 0);
}}

function maybeNudge() {{
  if (nudge && (searches >= 3 || saved.size >= 2)) nudge.hidden = false;
}}

function apply() {{
  // every word has to land somewhere in the row, not the whole phrase in one place
  const tests = q.value.trim().toLowerCase().split(/\\s+/).filter(Boolean)
    .map(t => SYN.has(t) ? SYN.get(t) : t)
    .map(tokenTest);
  const on = chips.filter(c => c.getAttribute("aria-pressed") === "true");
  filtered = sortRows(ROWS.filter(
    r => tests.every(fn => fn(r.blob)) && on.every(c => c.test(r))
  ));
  list.textContent = "";
  shown = 0;
  countN.textContent = filtered.length.toLocaleString();
  countTail.textContent = " of " + ROWS.length.toLocaleString() + " listings";
  empty.hidden = filtered.length > 0;
  renderMore();
}}

function wireCopy(btnId, srcId) {{
  const b = document.getElementById(btnId), s = document.getElementById(srcId);
  if (!b || !s) return;
  b.addEventListener("click", () => {{
    const label = b.dataset.label || b.textContent;
    b.dataset.label = label;
    try {{
      navigator.clipboard.writeText(s.textContent).then(() => {{
        b.textContent = "Copied";
        setTimeout(() => {{ b.textContent = label; }}, 1600);
      }}, () => {{ b.textContent = "Copy failed, select it instead"; }});
    }} catch (e) {{ b.textContent = "Copy failed, select it instead"; }}
  }});
}}
wireCopy("copy-msg", "msg-text");
wireCopy("copy-tpl", "tpl-text");

let searchTimer;
q.addEventListener("input", () => {{
  apply();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {{
    const v = q.value.trim().toLowerCase();
    if (v.length >= 2 && v !== lastCounted) {{
      lastCounted = v;
      searches++;
      maybeNudge();
    }}
  }}, 700);
}});
sortSel.addEventListener("change", apply);
more.addEventListener("click", renderMore);
clearBtn.addEventListener("click", () => {{
  q.value = "";
  for (const c of chips) c.setAttribute("aria-pressed", "false");
  apply();
  q.focus();
}});
addEventListener("scroll", () => {{
  bar.classList.toggle("stuck", bar.getBoundingClientRect().top <= 0);
}}, {{ passive: true }});

// a phone gets the facts panel folded to its two-line summary, and the count
// readout moved off the input row so the search box stays typeable
const narrow = matchMedia("(max-width: 640px)");
const countP = document.getElementById("count");
const controls = document.querySelector(".controls");
function syncNarrow() {{
  if (factsD) factsD.open = !narrow.matches;
  if (narrow.matches) chipRow.prepend(countP);
  else controls.appendChild(countP);
}}
narrow.addEventListener("change", syncNarrow);
syncNarrow();

refreshSaved();
apply();
</script>
</body>
</html>
"""
