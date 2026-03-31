# Fix Strategy: Error Ticket (GCP/Sentry)

This strategy is loaded by `/work-on-ticket` when the ticket has the `errors` or `auto-triage` label. It contains the remediation logic for production errors triaged from GCP Cloud Logging and Sentry.

## Additional Environment Variables

This strategy requires additional environment variables beyond the standard Jira ones:

| Variable | Required | Purpose |
|----------|----------|---------|
| `GCLOUD_PROJECT_ID` | Yes | GCP project to query logs from |
| `SENTRY_URL` | Yes | Self-hosted Sentry base URL — no trailing slash |
| `SENTRY_ORG` | Yes | Sentry organization slug |
| `SENTRY_PROJECT` | Yes | Sentry project slug |
| `SENTRY_AUTH_TOKEN` | Yes | Sentry API auth token |

If any are missing, tell the user which ones and provide `export` commands.

## Parse Ticket Description

Extract error context from the Jira ticket description:

1. **Error signature** — from the `Error Signature:` field
2. **Sentry issue URL** — look for a line matching `**Sentry Issue:**` followed by a URL
3. **Sentry issue ID** — extract the numeric issue ID from the Sentry URL
4. **Stacktrace snippet** — content between `{code}` blocks
5. **Frequency** — from the `Frequency:` field
6. **Source** — from the `Source:` field (GCP / Sentry / Both)

If the ticket doesn't follow the expected format, extract whatever context is available and note what's missing.

## Fetch Full Error Details

### Sentry Details (if Sentry issue URL/ID was found)

Fetch the latest event for the full stacktrace:

```bash
curl -s \
  "$SENTRY_URL/api/0/issues/{issue_id}/events/latest/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN"
```

Extract: full stacktrace, tags, request context, user context, breadcrumbs.

Also fetch issue metadata:

```bash
curl -s \
  "$SENTRY_URL/api/0/issues/{issue_id}/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN"
```

Extract: total event count, first/last seen, affected users count.

### GCP Logs

Fetch recent related log entries using the error message as a filter:

**If gcloud CLI is available:**

```bash
gcloud logging read \
  "textPayload:\"<key part of error message>\" AND severity>=ERROR" \
  --project="$GCLOUD_PROJECT_ID" \
  --format=json \
  --limit=20 \
  --freshness=7d
```

**API fallback:**

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

Look for patterns: timing, correlated request paths, preceding warnings.

## Analyze Error Context

Analyze all collected information:

1. **Parse the full stacktrace** — identify every file and function in the call chain
2. **Identify the root cause frame** — the deepest frame in application code (not library/framework)
3. **Determine the error type**: null reference, type error, timeout, resource exhaustion, auth failure, data validation, race condition
4. **Note trigger conditions** — what inputs, request patterns, or environmental conditions cause the error
5. **Assess severity** — based on frequency, affected users, and impact

Present a brief analysis:

> **Root Cause Analysis:**
> - **Error**: NullPointerException in `UserService.getProfile()` at line 42
> - **Cause**: `user.address` is null when the user has no address on file
> - **Trigger**: GET /api/users/{id}/profile for users who haven't set an address
> - **Impact**: 47 occurrences in 24h, affecting ~30 users
> - **Type**: Null reference — missing null check

## Find Relevant Code

Search the current repository for the files and functions from the stacktrace:

1. Search for files using exact paths from stacktrace frames
2. If paths don't match (compiled vs source), search by filename
3. Read those files and locate the exact functions/methods
4. Read surrounding context — callers, error handling, data models
5. Identify the exact code path that produces the error

If the stacktrace references files not in this repository, tell the user:
> The stacktrace points to files not in this repository. This error may need to be fixed in a different repo.

## Propose Fix

Show the user:

1. **Root cause summary** (2-3 sentences)
2. **Proposed changes** — show the diff for each file
3. **Risk assessment**: other affected code paths, potential new edge cases, related patterns with the same bug
4. **Alternative approaches** (if applicable)

Ask for confirmation:
> Does this fix look correct? Should I apply it?

**Do NOT apply any changes until the user confirms.**

## Apply Fix

After user confirmation:
- Modify only the files discussed in the proposal
- Do not refactor surrounding code
- Do not modify tests

## Build & Test Verification

Refer to `../../references/package-manager-detection.md` for detection logic.

1. Run build and tests
2. Compare results against baseline (stash changes to capture baseline if needed):
   - **New failures** → fix and retry (max 3 attempts)
   - **Pre-existing failures** → do NOT touch
   - **Never modify tests** to make them pass
3. If a new failure cannot be resolved after 3 attempts, ask the user for help
