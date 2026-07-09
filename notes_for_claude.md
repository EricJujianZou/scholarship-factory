# notes_for_claude.md

Operational notes for Claude working in this repo. Conventions and gotchas that
aren't obvious from the code. Keep it short and factual.

## GitHub access — use the REST API, not the `gh` CLI

The `gh` CLI is **not** authenticated in this environment (`gh auth login` was
never run, no `GH_TOKEN`/`GITHUB_TOKEN`). Do **not** use `gh` for issues, PRs, or
any GitHub operation — it will fail. Use the **GitHub REST API** directly.

**Auth token** lives in the Windows Credential Manager (git's `wincred` helper),
not in an env var. Pull it at call time:

```bash
TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill | sed -n 's/^password=//p')
```

**Example calls** (repo is `EricJujianZou/scholarship-factory`):

```bash
# List open issues
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/EricJujianZou/scholarship-factory/issues?state=open"

# Create an issue
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/EricJujianZou/scholarship-factory/issues" \
  -d '{"title":"...","body":"...","labels":["adw"]}'

# List PRs
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/EricJujianZou/scholarship-factory/pulls?state=all"
```

Never print the token to output; interpolate it directly into the `curl` call.
