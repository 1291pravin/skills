---
name: triage-errors
description: >
  Fetch errors from GCP Cloud Logging and Sentry (self-hosted) for the last 24
  hours, deduplicate across sources, check existing Jira tickets to avoid
  duplicates, and create new Jira tickets with full error context. Outputs a
  summary of new and existing tickets. Use this skill whenever the user mentions
  triage errors, check errors, check logs, fetch error logs, create tickets for
  errors, what errors happened, daily error check, or error monitoring, even if
  they don't explicitly say "triage-errors".
---

# Error Triage — GCP + Sentry → Jira

Automate the daily error triage workflow: fetch errors from GCP Cloud Logging and self-hosted Sentry (last 24 hours), deduplicate across sources, check existing Jira tickets, create new tickets for untracked errors, and output a summary. Follow each step in order.

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

If any are missing, tell the user exactly which ones and provide copy-paste `export` commands:

> The following environment variables are missing:
> ```bash
> export SENTRY_URL=https://sentry.company.com
> export SENTRY_AUTH_TOKEN=your-token-here
> ```
> Set them and let me know when ready.

Do not proceed until all required variables are set.

## Step 2: Check CLI Availability

Check which CLI tools are installed. Each tool has an API fallback, so none are required — just record which path to use.

```bash
command -v gcloud && echo "gcloud: available" || echo "gcloud: not found"
command -v sentry-cli && echo "sentry-cli: available" || echo "sentry-cli: not found"
command -v acli && echo "acli: available" || echo "acli: not found"
```

If `acli` is not available, also check for Jira API fallback credentials:

| Variable | Purpose |
|----------|---------|
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |

If `acli` is not installed and `JIRA_EMAIL` + `JIRA_API_TOKEN` are also missing, stop and ask the user:
> Neither `acli` CLI nor Jira API credentials (`JIRA_EMAIL`, `JIRA_API_TOKEN`) are available. Please install acli or set the API credentials.

Report which tools will use CLI vs API fallback and proceed.

## Step 3: Fetch GCP Errors (Last 24h)

Calculate the timestamp for 24 hours ago in RFC 3339 format.

**If gcloud CLI is available:**

```bash
gcloud logging read \
  "severity>=ERROR AND timestamp>=\"$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')\"" \
  --project="$GCLOUD_PROJECT_ID" \
  --format=json \
  --limit=500
```

On macOS, use `date -u -v-24H '+%Y-%m-%dT%H:%M:%SZ'` instead.

**If gcloud CLI is not available but `gcloud auth print-access-token` works (gcloud installed but not in PATH properly):**

```bash
ACCESS_TOKEN=$(gcloud auth print-access-token)

curl -s -X POST \
  "https://logging.googleapis.com/v2/entries:list" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceNames": ["projects/'"$GCLOUD_PROJECT_ID"'"],
    "filter": "severity>=ERROR AND timestamp>=\"'"$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')"'\"",
    "orderBy": "timestamp desc",
    "pageSize": 500
  }'
```

**If gcloud is completely unavailable:**

Tell the user:
> gcloud CLI is not installed. I need it at minimum for authentication. Please install gcloud SDK or provide a GCP service account key file path via `GOOGLE_APPLICATION_CREDENTIALS`.

If `GOOGLE_APPLICATION_CREDENTIALS` is set, obtain an access token via the service account and use the curl approach above.

Store all fetched log entries for analysis in Step 5.

## Step 4: Fetch Sentry Issues (Unresolved, Last 24h)

**Preferred approach — API** (more reliable filtering than sentry-cli):

```bash
curl -s \
  "$SENTRY_URL/api/0/projects/$SENTRY_ORG/$SENTRY_PROJECT/issues/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  -G \
  --data-urlencode "query=is:unresolved" \
  --data-urlencode "statsPeriod=24h" \
  --data-urlencode "sort=freq"
```

This returns issues sorted by frequency. Paginate if the `Link` header contains `rel="next"; results="true"`.

**For each issue, fetch the latest event** to get the full stacktrace:

```bash
curl -s \
  "$SENTRY_URL/api/0/issues/{issue_id}/events/latest/" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN"
```

**If sentry-cli is available and preferred:**

```bash
sentry-cli --url "$SENTRY_URL" issues list --project "$SENTRY_PROJECT" --status unresolved
```

Note: sentry-cli output may be limited. The API approach provides richer data (stacktraces, tags, event counts). Prefer API when both are available.

Store all fetched issues and their latest events for analysis in Step 5.

## Step 5: Analyze & Deduplicate

This is a pure analysis step — no CLI or API calls.

### 5a: Group GCP Logs

Group GCP log entries by error signature. To create the signature:

1. Extract the error message from `textPayload` or `jsonPayload.message`
2. Normalize by stripping:
   - Timestamps and dates
   - UUIDs, request IDs, session IDs
   - Memory addresses and hex values
   - Line numbers (these vary across deployments)
   - Numeric identifiers (user IDs, order IDs, etc.)
3. Group entries with identical normalized messages
4. For each group, record: normalized signature, raw count, first/last occurrence timestamp, one representative full log entry

### 5b: Cross-Source Matching

Sentry issues are already deduplicated (Sentry groups events into issues).

Match GCP error groups against Sentry issues:

1. For each GCP error group, compare the normalized signature against each Sentry issue's `title` and `culprit` fields
2. If a GCP group matches a Sentry issue (substring match or high similarity), merge them into a single unified error entry
3. Mark the unified entry's source as "Both"
4. Unmatched GCP groups → source "GCP only"
5. Unmatched Sentry issues → source "Sentry only"

**Important:** Err on the side of NOT merging when uncertain. Creating two separate tickets is better than missing an error. Only merge when the error message clearly indicates the same root cause.

### 5c: Build Unified Error List

For each unified error, record:

- **Error signature** (normalized message, max 200 chars)
- **Frequency** (GCP log count + Sentry event count)
- **Source(s)**: GCP / Sentry / Both
- **Representative stacktrace** (from Sentry event or GCP log)
- **Sentry issue URL** (if from Sentry): `$SENTRY_URL/organizations/$SENTRY_ORG/issues/{issue_id}/`
- **Sentry issue ID** (for Jira ticket description)
- **First occurrence** timestamp
- **Last occurrence** timestamp

Sort by frequency (highest first).

## Step 6: Check Existing Jira Tickets

For each unified error, check if a Jira ticket already exists to avoid duplicates.

**If acli CLI is available:**

For each error signature, search:

```bash
acli issue list -p "$JIRA_PROJECT_KEY" -q "labels = auto-triage AND status != Done AND summary ~ \"<first 50 chars of error signature>\""
```

**If using API fallback:**

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND labels = auto-triage AND status != Done AND summary ~ \"<first 50 chars of error signature>\"",
    "maxResults": 5,
    "fields": ["summary", "status", "key"]
  }'
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/` (Jira Server/Data Center uses v2).

For each error:
- If a matching ticket is found → mark as **"already tracked"** and record the existing ticket key
- If no match → mark as **"new"**

## Step 7: Create Jira Tickets for New Errors

For each error marked as "new" in Step 6, create a Jira ticket.

**Ticket fields:**

- **Project**: `$JIRA_PROJECT_KEY`
- **Type**: Bug
- **Summary**: First 200 chars of the error signature
- **Labels**: `auto-triage`
- **Description** (use this exact template):

```
h2. Error Details

*Error Signature:* {noformat}<full normalized error message>{noformat}

*Frequency:* <count> occurrences in the last 24 hours
*Source:* <GCP / Sentry / Both>
*First Seen:* <timestamp>
*Last Seen:* <timestamp>

h2. Stacktrace

{code}
<first 30 lines of representative stacktrace>
{code}

h2. Links

**Sentry Issue:** <SENTRY_URL/organizations/ORG/issues/ISSUE_ID/>
**GCP Log Filter:** severity>=ERROR AND textPayload:"<key part of error message>"

h2. Notes

Created automatically by /triage-errors on <today's date>.
```

**If acli CLI is available:**

```bash
acli issue create \
  -P "$JIRA_PROJECT_KEY" \
  --type Bug \
  --summary "<error signature>" \
  --description "<description from template above>" \
  --labels auto-triage
```

**If using API fallback:**

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "fields": {
      "project": {"key": "'"$JIRA_PROJECT_KEY"'"},
      "issuetype": {"name": "Bug"},
      "summary": "<error signature>",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [...]
      },
      "labels": ["auto-triage"]
    }
  }'
```

Note: Jira Cloud API v3 uses Atlassian Document Format (ADF) for description. Jira Server API v2 uses plain text/wiki markup. If v3 fails, fall back to v2 with wiki markup.

Record the created ticket key for each new error.

## Step 8: Output Summary

Display a summary table to the user:

```
## Triage Summary — <today's date>

| Metric | Count |
|--------|-------|
| Total errors found | <N> |
| — from GCP only | <N> |
| — from Sentry only | <N> |
| — from both sources | <N> |
| New tickets created | <N> |
| Already tracked | <N> |

### New Tickets Created
| Ticket | Error Signature | Frequency | Source |
|--------|----------------|-----------|--------|
| ENG-123 | NullPointerException in UserService.get... | 47 | Both |
| ENG-124 | Connection timeout to redis-primary:6379 | 12 | GCP |

### Already Tracked
| Ticket | Error Signature | Status |
|--------|----------------|--------|
| ENG-100 | OutOfMemoryError in BatchProcessor | In Progress |
```

If no new errors were found, tell the user:
> No new errors in the last 24 hours. All existing errors are already tracked in Jira.
