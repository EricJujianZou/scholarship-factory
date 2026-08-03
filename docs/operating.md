# Running it day to day

The intended shape: it works overnight, you read a digest with your coffee, and
you spend your attention only on things it flagged.

## One-time setup

```powershell
uv sync --extra gemini
```

Put your key in `.env` in the repo folder - it is gitignored, and both the CLI
and the dashboard read it at start-up:

```
GEMINI_API_KEY="your-key"
```

`setx GEMINI_API_KEY "your-key"` works too and takes precedence; a real
environment variable always wins over the file.

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

The key has to be in `.env` or set with `setx`, not just exported in a shell:
the dashboard launches its jobs from the environment it inherits at start-up.
Without one, the LLM buttons are switched off and the page says so, next to a
**Re-read .env** button - press that after saving a key and the buttons come
back on without a restart.

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
not already decided, then print the digest and mark the run so tomorrow's digest
only reports what is newer. It never prompts, and a failing source is recorded
rather than fatal, so it is safe to schedule.

### The 6am run is not registered

Nothing schedules itself. As of 2026-08-02 no scheduled task exists - the daily
pass only happens when you press **Find new opportunities**. Check with:

```powershell
schtasks /Query /TN "scholarship-factory-poll"
```

`ERROR: The system cannot find the file specified.` means it is not registered.
To register it:

```powershell
schtasks /Create /SC DAILY /ST 06:00 /TN "scholarship-factory-poll" ^
  /TR "cmd /c cd /d C:\Users\zouju\Coding Projects\scholarship-factory && uv run sf poll --seeds seeds.toml --page-cap 15 --max-pages 3 >> poll.log 2>&1"
```

The key reaches a scheduled run through `.env` without any extra setup: the
loader resolves the file from the package's own location, so it works whatever
directory the task starts in. Deleting the task is
`schtasks /Delete /TN "scholarship-factory-poll" /F`.

A different task, `\ADW\ADW-scholarship-factory`, does exist and is
**Disabled**. That one is the build harness - it writes code against tickets,
not opportunities - and is unrelated to polling. Do not enable it expecting a
digest.

Caveats inherited from the machine: Task Scheduler jobs run only while you are
logged in and stop on battery. The digest lands in `poll.log`; `sf digest`
reprints the last one without re-running anything.

## Your 20 minutes

1. Read `poll.log` (or run `sf digest`) - new opportunities ranked by fit, plus
   anything closing within two weeks that you have not ruled on.
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
