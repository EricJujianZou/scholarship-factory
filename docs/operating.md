# Running it day to day

One pass does the sourcing and ranking; you spend your attention only on what it
flagged. That pass now runs itself every morning (see *The daily dispatcher*),
and you can still start one by hand from the dashboard whenever you want.

## One-time setup

```powershell
uv sync --extra gemini
```

Put your key in `.env` in the repo folder - it is gitignored, and both the CLI
and the dashboard read it at start-up:

```
GEMINI_API_KEY="your-key"
```

(A real environment variable still wins over the file if one is set, but you
don't need `setx` - `.env` covers every way this runs.)

One file holds everything you supply - the ranking profile and your own
material:

```powershell
copy context.example.toml context.toml   # gitignored - it holds personal data
uv run sf context import context.toml    # re-run whenever you edit it
```

The `[profile]` section is what ranking filters and sorts on; the rest is the
corpus a draft gets written from. The dashboard's profile editor at
<http://127.0.0.1:8000> edits the same profile - whichever you touch last wins,
and omitting the section from the file leaves the stored profile alone.

## Opening the dashboard

Double-click `dashboard.bat` in the repo folder. It starts the server if it is
not already running, waits for the port, and opens the browser; if the server is
already up it just opens the tab. The server runs in the minimized window it
opens - close that window to stop it.

Everything below can be run from the dashboard instead of the terminal. The
buttons across the top are the same commands, each with what it does and what it
costs written next to it, and the output streams into the page while it runs:

| Button | Runs |
|---|---|
| Find new opportunities | `sf poll --seeds seeds.toml --page-cap 15 --max-pages 3` |
| (no button) Fill pay/logos | `sf enrich --cap 400 --llm-cap 15` - the daily task runs it |
| Re-rank everything | `sf rank` |
| Reload my context | `sf context import context.toml` |
| What does it ask for? (per row) | `sf requirements <id>` |
| Refresh facts (per row) | re-fetch and re-extract that one page |

The key has to be in `.env`, not just exported in a shell: the dashboard
launches its jobs from the environment it inherits at start-up. Without one, the
LLM buttons are switched off and the page says so, next to a **Re-read .env**
button - press that after saving a key and the buttons come back on without a
restart.

**A running server is invisible to `dashboard.bat`.** The batch file starts a
server only when nothing is listening on the port, so double-clicking it while
an old server is up just opens another tab against that old process - which
still has the environment it started with hours ago. Closing the browser does
not stop it; the server lives in its own minimized *scholarship-factory server*
console window. This is what **Re-read .env** exists to avoid.

## The daily loop

```powershell
uv run sf poll --seeds seeds.toml --page-cap 15 --max-pages 3
```

`poll` is one unattended pass: source every seed, re-score everything you have
not already decided, then print the digest and mark the run so the next digest
only reports what is newer. It never prompts, and a failing source is recorded
rather than fatal.

You can still press **Find new opportunities** for a pass on demand, and
`sf digest` reprints the last one without re-running anything.

## The daily dispatcher

`poll` alone only grows the database. The scheduled run does the whole chain
that ends with the public site being different:

```
sf poll  ->  sf enrich  ->  sf splice ugmi.ca/index.html  ->  git push
 new rows    pay, deadline    rewrite only the data line      deploying is
             and org logos    of the live page               pushing that file
```

Register it once:

```powershell
.\scripts\register-daily.ps1          # 07:00 daily; -At "06:30" to move it
```

It registers under your own account, which is what lets the push reach
`git@git.skullheadx.com` using your SSH agent. `-StartWhenAvailable` is set, so
a run missed while the laptop was asleep happens at the next wake instead of
being skipped.

- Logs: `observability\daily\<date>.log`, one file per day, every command's
  output indented under it.
- Run it now: `Start-ScheduledTask -TaskName "scholarship-factory daily"`, or
  `.\scripts\daily.ps1` directly.
- Prepare without deploying: `.\scripts\daily.ps1 -NoPush` leaves the spliced
  `index.html` uncommitted for you to look at.
- Stop it: `Unregister-ScheduledTask -TaskName "scholarship-factory daily"`.

A failed splice stops the chain before the push, so the live page keeps
yesterday's data rather than getting a broken one. A failed *poll* does not -
the store from yesterday is still worth publishing. Only one run happens at a
time; a second one exits immediately rather than interleaving writes to the
same SQLite file.

**Where the daily growth actually comes from.** Three of the seeds are
community boards that crawl ATS boards on their own schedule and publish the
result as JSON - Simplify, vanshb03 and zshah101. Re-fetching them each morning
is one HTTP request each, zero LLM calls, and it is the bulk of what arrives.
zshah101 is the only one of the three that publishes **pay**, and because a
dedup hit merges facts rather than discarding them, its salaries also backfill
rows that arrived earlier from the other two boards.

## Pay, deadlines and logos on the cards

New rows land bare: a community board publishes a title, a company and a link.
`sf enrich` is what turns them into a card worth looking at, walking a
deterministic-first ladder per row and stopping as soon as a fact is found:

1. **The ATS's own JSON** for Lever, Ashby and Greenhouse links - one request,
   structured, no HTML. About 28% of stored internships are on one of these.
2. **JSON-LD `JobPosting`** on the apply page: salary, posting expiry, and
   `hiringOrganization.logo`.
3. **The apply page's `og:image`**, when it points somewhere logos are known to
   live (Greenhouse's `/logos/` uploads, Lever's client-logo bucket). Free - the
   page body is already in hand from stage 2.
4. **An LLM read of the page**, capped, only for rows the first three left empty.

Logos are stored per *company*, not per row, so one page that states Stripe's
logo fills every Stripe card. Nothing is downloaded or re-hosted; the site
hotlinks. A row that gives nothing is marked in a ledger and not re-fetched for
seven days, so the daily run always spends its budget on rows it has not tried.

This is a sweep, not a single pass: with ~1,700 rows still missing a fact and a
400-fetch daily cap, coverage climbs over days rather than arriving at once.
`--cap` is the dial if you want it faster.

## Your 20 minutes

1. Press **Find new opportunities**, or run `sf digest` for the last pass - new
   opportunities ranked by fit, plus anything closing within two weeks that you
   have not ruled on.
2. Open the dashboard, hit **Interested** / **Not interested**. Those decisions
   feed the next ranking directly, and every fifth one re-distils the written
   preference summary shown at the top of the page.
3. For anything you kept: `sf requirements <id>` reads its apply page and tells
   you what the application actually demands - essay prompts and their word
   limits, documents, how many referees.

## Cost

Every fetched page is one LLM call, and `sf rank` adds one for the whole batch.
`--page-cap` and `--max-pages` are the dials. A run of 3 seeds at cap 15 with 3
pages each is on the order of 100-150 calls.
