---
name: fix-errors
description: >
  Fetch open Jira tickets created by /triage-errors (labeled auto-triage), let
  the user pick one, pull full error context from Sentry (self-hosted) and GCP
  Cloud Logging, find the relevant code in the current repository, propose and
  apply a fix, run build and tests, create a PR, and update the Jira ticket.
  Use this skill whenever the user mentions fix errors, fix error tickets, work
  on error tickets, fix triage tickets, fix production errors, or resolve error
  tickets, even if they don't explicitly say "fix-errors".
---

# Error Fix — Jira Ticket → Code Fix → PR

Pick an open error ticket from triage, pull full error context from Sentry and GCP, find and fix the root cause in the current repository, verify with build/tests, create a PR, and update the Jira ticket. Follow each step in order.

## Step 1: Validate Environment Variables

Check all required environment variables at once. Do not stop at the first missing one — collect all missing vars and report them together.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `GCLOUD_PROJECT_ID` | GCP project to query logs from |
| `SENTRY_URL` | Self-hosted Sentry base URL (e.g., `https://sentry.company.com`) — no trailing slash |
| `SENTRY_ORG` | Sentry organization slug |
| `SENTRY_PROJECT` | Sentry project slug |
| `SENTRY_AUTH_TOKEN` | Sentry API auth token |
| `JIRA_URL` | Jira instance URL (e.g., `https://company.atlassian.net`) — no trailing slash |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |

If any are missing, tell the user exactly which ones and provide copy-paste `export` commands:

> The following environment variables are missing:
> ```bash
> export SENTRY_URL=https://sentry.company.com
> export SENTRY_AUTH_TOKEN=your-token-here
> ```
> Set them and let me know when ready.

Do not proceed until all required variables are set.

## Step 2: Check CLI Availability

Check which CLI tools are installed. GCP and Sentry have CLI options; Jira uses the REST API directly.

```bash
command -v gcloud && echo "gcloud: available" || echo "gcloud: not found"
command -v sentry-cli && echo "sentry-cli: available" || echo "sentry-cli: not found"
command -v gh && echo "gh: available" || echo "gh: not found"
```

Report which tools are available and proceed. Jira operations always use the REST API.

## Step 3: Fetch Open Triage Tickets

Fetch all open Jira tickets with the `auto-triage` label (created by `/triage-errors`) via the Jira REST API:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND labels = auto-triage AND status != Done ORDER BY created DESC",
    "maxResults": 20,
    "fields": ["summary", "status", "priority", "created", "description"]
  }'
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/` (Jira Server/Data Center uses v2).

Display a numbered list to the user:

```
## Open Error Tickets

| # | Ticket | Summary | Priority | Created |
|---|--------|---------|----------|---------|
| 1 | ENG-123 | NullPointerException in UserService.get... | High | 2026-03-27 |
| 2 | ENG-124 | Connection timeout to redis-primary:6379 | Medium | 2026-03-27 |
| 3 | ENG-100 | OutOfMemoryError in BatchProcessor | Critical | 2026-03-26 |
```

If no tickets are found, tell the user:
> No open triage tickets found. Run `/triage-errors` first to fetch and create tickets for recent errors.

## Step 4: User Selects a Ticket

Ask the user to pick a ticket by number or ticket key:

> Which ticket would you like to work on? Enter a number from the list above or a ticket key (e.g., ENG-123).

Wait for the user's selection before proceeding.

If the user selects by number, map it to the corresponding ticket key from the list.

Fetch the full ticket description for the selected ticket via the Jira REST API:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

## Step 5: Extract Error Context from Ticket

Parse the Jira ticket description to extract:

1. **Error signature** — from the `Error Signature:` field in the description
2. **Sentry issue URL** — look for a line matching `**Sentry Issue:**` followed by a URL containing `$SENTRY_URL`
3. **Sentry issue ID** — extract the numeric issue ID from the Sentry URL (last path segment before trailing slash)
4. **Stacktrace snippet** — content between `{code}` blocks in the description
5. **Frequency** — from the `Frequency:` field
6. **Source** — from the `Source:` field (GCP / Sentry / Both)

If the ticket description does not follow the expected format (e.g., it was manually created), extract whatever context is available and note what's missing.

## Step 6: Fetch Full Error Details

### 6a: Sentry Details (if Sentry issue URL/ID was found)

Fetch the latest event for the Sentry issue to get the full stacktrace, tags, and context:

```bash
curl -s \
  "$SENTRY_URL/api/0/issues/{issue_id}/events/latest/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN"
```

Extract from the response:
- Full stacktrace (all frames, not just the snippet from the ticket)
- Tags (environment, server name, browser, OS, etc.)
- Request context (URL, method, headers if available)
- User context (if available)
- Breadcrumbs (recent actions leading to the error)

Also fetch issue metadata:

```bash
curl -s \
  "$SENTRY_URL/api/0/issues/{issue_id}/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN"
```

Extract: total event count, first/last seen, affected users count.

### 6b: GCP Logs (using error message as filter)

Fetch recent related log entries:

**If gcloud CLI is available:**

```bash
gcloud logging read \
  "textPayload:\"<key part of error message>\" AND severity>=ERROR" \
  --project="$GCLOUD_PROJECT_ID" \
  --format=json \
  --limit=20 \
  --freshness=7d
```

**If using API fallback:**

```bash
ACCESS_TOKEN=$(gcloud auth print-access-token)

curl -s -X POST \
  "https://logging.googleapis.com/v2/entries:list" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceNames": ["projects/'"$GCLOUD_PROJECT_ID"'"],
    "filter": "textPayload:\"<key part of error message>\" AND severity>=ERROR",
    "orderBy": "timestamp desc",
    "pageSize": 20
  }'
```

Look for patterns in the logs:
- Is the error happening at specific times? (cron jobs, peak traffic)
- Is it correlated with specific request paths or services?
- Are there warning-level logs immediately preceding the error?

## Step 7: Analyze Error Context

Analyze all collected information to understand the error:

1. **Parse the full stacktrace** — identify every file and function in the call chain
2. **Identify the root cause frame** — the deepest frame in application code (not library/framework code)
3. **Determine the error type**:
   - Null/undefined reference
   - Type error
   - Connection/timeout error
   - Resource exhaustion (memory, disk, connections)
   - Authentication/authorization failure
   - Data validation error
   - Race condition or concurrency issue
4. **Note trigger conditions** — what inputs, request patterns, or environmental conditions cause the error
5. **Assess severity** — based on frequency, affected users, and impact

Present a brief analysis to the user:

> **Root Cause Analysis:**
> - **Error**: NullPointerException in `UserService.getProfile()` at line 42
> - **Cause**: `user.address` is null when the user has no address on file
> - **Trigger**: GET /api/users/{id}/profile for users who haven't set an address
> - **Impact**: 47 occurrences in 24h, affecting ~30 users
> - **Type**: Null reference — missing null check

## Step 8: Find Relevant Code

Search the current repository for the files and functions identified in Step 7.

1. Search for files mentioned in the stacktrace:
   - Use exact file paths from stacktrace frames
   - If paths don't match the repo structure (e.g., compiled paths vs source paths), search by filename
2. Read those files and locate the exact functions/methods from the stacktrace
3. Read surrounding context — caller functions, related error handling, data models
4. Identify the exact code path that produces the error

If the stacktrace references files not in the current repository (e.g., the error is in a different service), tell the user:
> The stacktrace points to files not in this repository (e.g., `other-service/src/...`). This error may need to be fixed in a different repo. Would you like to continue with what's available here, or switch to the correct repo?

## Step 9: Propose Fix

Based on the root cause analysis and code review, propose a fix. Show the user:

1. **Root cause summary** (2-3 sentences)
2. **Proposed changes** — show the diff for each file that needs modification
3. **Risk assessment**:
   - What other code paths could this change affect?
   - Could this fix introduce new edge cases?
   - Are there related patterns elsewhere in the codebase that have the same bug?
4. **Alternative approaches** (if applicable) — briefly mention other ways to fix this

Ask for confirmation:
> Does this fix look correct? Should I apply it? (If you'd prefer a different approach, let me know.)

**Do NOT apply any changes until the user confirms.**

## Step 10: Apply Fix

After user confirmation, apply the proposed code changes.

- Modify only the files discussed in Step 9
- Do not refactor surrounding code or add unrelated improvements
- Do not modify tests — only fix the source code that causes the error

## Step 11: Detect Package Manager

Determine which package manager the project uses. Check in this order (first match wins):

1. `package.json` → `packageManager` field (e.g., `"packageManager": "pnpm@9.0.0"`)
2. `bun.lockb` or `bun.lock` exists → **bun**
3. `pnpm-lock.yaml` exists → **pnpm**
4. `yarn.lock` exists → **yarn**
   - If `.yarnrc.yml` also exists or `packageManager` contains `yarn@4` or higher → **Yarn 4 (Berry)**
   - Otherwise → **Yarn Classic (v1)**
5. `package-lock.json` exists → **npm**

If no lock file is found, ask the user which package manager to use.

Use the detected package manager for ALL commands throughout the workflow:

| Action | npm | yarn v1 | yarn v4 | pnpm | bun |
|--------|-----|---------|---------|------|-----|
| Install deps | `npm ci` | `yarn install --frozen-lockfile` | `yarn install --immutable` | `pnpm install --frozen-lockfile` | `bun install --frozen-lockfile` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

If the project is not a JavaScript/Node.js project (e.g., Python, Go, Java), use the appropriate build/test commands for that language/framework:

- **Python**: `pip install -r requirements.txt`, `pytest`
- **Go**: `go build ./...`, `go test ./...`
- **Java/Maven**: `mvn compile`, `mvn test`
- **Java/Gradle**: `./gradlew build`, `./gradlew test`

## Step 12: Baseline Test Snapshot

**Run this BEFORE verifying the fix (but after applying changes in Step 10 — this captures the pre-fix state if possible, or serves as a comparison point).**

If you were able to run tests before applying the fix (e.g., you ran them during Step 8 to understand the code), use that as the baseline. Otherwise:

1. Stash the fix changes: `git stash`
2. Run the test command for the detected package manager and capture full output
3. Record every failing test by name/path → store as the **baseline failures list**
4. If the build itself fails before tests run → record the build error as a baseline failure too
5. Restore the fix: `git stash pop`

Inform the user:
> Baseline captured: **B** tests already failing before the fix. These will not be attributed to this change.

## Step 13: Build & Test Verification

After the fix is applied:

1. Run the build command for the detected package manager
2. If the build fails and the error is new (not in baseline), attempt to fix the build error — max 3 attempts
3. Run the test command and capture full output
4. Compare test results against the baseline:
   - Tests that were failing before AND still fail → **pre-existing, not caused by this fix**
   - Tests that were passing before AND now fail → **regression introduced by the fix — must be addressed**
   - Tests that were failing before AND now pass → **bonus — the fix resolved additional issues**
5. If there are regressions:
   - Attempt to fix them (max 3 attempts)
   - If still failing after 3 attempts, ask the user for help:
     > The fix introduced test failures that I couldn't resolve:
     > - `test_user_profile_with_null_address` — expected 200 but got 500
     > Would you like to review and fix manually, or should I revert the changes?
6. **NEVER modify existing tests** to make them pass — only fix the source code

## Step 14: Create Pull Request

Create a branch, commit, and open a PR.

1. **Create branch:**
   ```bash
   git checkout -b fix/error-<JIRA_KEY>-$(date +%Y-%m-%d)
   ```

2. **Stage only the modified files** (do not stage unrelated changes):
   ```bash
   git add <file1> <file2> ...
   ```

3. **Commit** with a message referencing the Jira ticket:
   ```bash
   git commit -m "fix(<area>): <short description>

   Resolves <JIRA_KEY>

   Root cause: <1-2 sentence explanation>
   "
   ```

4. **Push and create PR:**
   ```bash
   git push -u origin fix/error-<JIRA_KEY>-$(date +%Y-%m-%d)

   gh pr create \
     --title "fix(<area>): <short description> [<JIRA_KEY>]" \
     --body "## Summary

   Fixes <JIRA_KEY>: <error signature>

   ## Root Cause

   <Root cause analysis from Step 7>

   ## Changes

   <List of changes made>

   ## Error Context

   - **Source:** <GCP / Sentry / Both>
   - **Frequency:** <count> occurrences in 24h
   - **Sentry Issue:** <URL>

   ## Test Results

   - Build: ✅ Pass
   - Tests: ✅ Pass (<N> passing, <B> pre-existing failures)
   "
   ```

If `gh` is not installed, provide the push command and tell the user to create the PR manually.

## Step 15: Update Jira Ticket

After the PR is created, update the Jira ticket.

### 15a: Add Comment with PR URL

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fix PR created: <PR_URL>"}]}]}}'
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/` using plain text body:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/2/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": "Fix PR created: <PR_URL>"}'
```

### 15b: Transition Ticket Status

First, get available transitions:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Look for a transition named "In Review", "In Progress", "Code Review", or similar. If found, apply it:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"transition": {"id": "<transition_id>"}}'
```

If no suitable transition is found, tell the user:
> I couldn't find a matching transition for the ticket. Available transitions are: <list>. Would you like me to apply one of these?

### Final Output

Report the completed work:

```
## Fix Complete

| Item | Details |
|------|---------|
| Ticket | <JIRA_KEY>: <summary> |
| Root Cause | <1 sentence> |
| Files Changed | <list of files> |
| PR | <PR_URL> |
| Build | ✅ Pass |
| Tests | ✅ Pass |
| Jira Status | Transitioned to In Review |
```
