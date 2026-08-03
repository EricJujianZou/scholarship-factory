# Running it day to day

One pass does the sourcing and ranking; you spend your attention only on what it
flagged. Today you start that pass yourself from the dashboard - nothing runs on
a schedule.

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

Nothing runs it on a schedule. A pass happens when you press **Find new
opportunities**, and `sf digest` reprints the last one without re-running
anything.

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
