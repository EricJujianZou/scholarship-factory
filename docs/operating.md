# Running it day to day

The intended shape: it works overnight, you read a digest with your coffee, and
you spend your attention only on things it flagged.

## One-time setup

```powershell
uv sync --extra gemini
setx GEMINI_API_KEY "your-key"        # persists for scheduled runs; reopen the shell
```

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

## The daily loop

```powershell
uv run sf poll --seeds seeds.toml --page-cap 15 --max-pages 3
```

`poll` is one unattended pass: source every seed, re-score everything you have
not already decided, then print the digest and mark the run so tomorrow's digest
only reports what is newer. It never prompts, and a failing source is recorded
rather than fatal, so it is safe to schedule.

Schedule it for 6am daily:

```powershell
schtasks /Create /SC DAILY /ST 06:00 /TN "scholarship-factory-poll" ^
  /TR "cmd /c cd /d C:\Users\zouju\Coding Projects\scholarship-factory && uv run sf poll --seeds seeds.toml --page-cap 15 --max-pages 3 >> poll.log 2>&1"
```

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
