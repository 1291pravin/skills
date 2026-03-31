---
name: triage-aqa
description: >
  Run a UsableNet AQA accessibility scan on a suite, fetch all WCAG violations,
  and create Jira tickets with full issue context (one ticket per chunk of ~20
  issues). Checks existing Jira tickets to avoid duplicates. Use this skill
  whenever the user mentions triage accessibility, scan accessibility, triage
  AQA, check AQA issues, create tickets for accessibility violations, WCAG
  triage, or wants to triage accessibility findings, even if they don't
  explicitly say "triage-aqa".
---

# AQA Accessibility Triage — Scan & Create Jira Tickets

Run a UsableNet AQA accessibility scan, fetch all WCAG violations, and create Jira tickets (one per chunk of ~20 issues) for tracking. Follow each step in order.

## Step 1: Validate Environment Variables

Check all required environment variables at once.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `AQA_API_KEY` | API key, sent as `X-Team` header |
| `AQA_TEAM_SLUG` | Team identifier in the URL path (e.g., `acme`) |
| `JIRA_URL` | Jira instance URL — no trailing slash |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |

If any are missing, provide copy-paste `export` commands. Do not proceed until all are set.

**Base URL**: `https://api-aqa.usablenet.com/v3.1/{AQA_TEAM_SLUG}`

**Common headers** for every AQA API request:
```
Accept: application/json
X-Team: {AQA_API_KEY}
Content-Type: application/json  (for POST requests with body)
```

**Connectivity check** — verify the AQA API is reachable:
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/suites"
```

## Step 2: Resolve Target Suite

Determine which suite to scan based on user input:

**Given a site name** (e.g., "example.com"):
1. List suites → search names for case-insensitive match
2. If one match → use it. If multiple → ask user. If none → show all suites.

**Given a suite ID** (e.g., "TS612"):
1. Get suite details directly.

**Given a test ID** (e.g., "A3687-0"):
1. Get test details directly — includes suite reference.

**If no target specified**, list all suites and ask the user to pick one.

## Step 3: Get Suite Details

Fetch suite details to collect all flow IDs and crawler IDs:

```bash
curl -s -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/suites/$SUITE_ID"
```

Extract `flows[]` and `crawlers[]` arrays. Collect all flow IDs and crawler IDs.

Display suite info:
> **Suite:** <name> (ID: <suite_id>)
> **Flows:** <count> | **Crawlers:** <count>

## Step 4: Create Test & Trigger Scan

Create an accessibility test using all flows and crawlers:

```bash
curl -s -X POST -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "suiteId": "'"$SUITE_ID"'",
    "name": "triage-scan-'"$(date +%Y-%m-%d-%H-%M)"'",
    "rulesetPackId": "v2",
    "rulesetId": "wcag22",
    "flowIds": '"$FLOW_IDS_JSON"',
    "crawlerIds": '"$CRAWLER_IDS_JSON"'
  }' \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/create"
```

Extract the test ID from the response. Then trigger the run:

```bash
curl -s -X POST -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/$TEST_ID/run"
```

## Step 5: Poll Until Complete

Poll the run status every 10 seconds until `status === "ready"`:

```bash
curl -s -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID"
```

Timeout after 30 minutes. If the run times out or fails, tell the user and stop.

Update the user periodically:
> Scan in progress... (<elapsed> elapsed)

## Step 6: Fetch Issues

After the run completes, fetch issues for every flow and page:

**Flow issues:**
```bash
curl -s -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID/flows/$FLOW_ID/issues?changeIndex=-1&manual=false&stepIndex=0"
```

**Page issues (crawler results):**
```bash
# First, list pages
curl -s -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID/pages"

# Then, for each page
curl -s -H "Accept: application/json" -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID/pages/$PAGE_ID/issues"
```

**Sort all issues by severity**: critical > serious > moderate > minor. Within the same severity, group by `ruleId`.

Display the inventory:

> Found **N** accessibility issues:
>
> | Severity | Count |
> |----------|-------|
> | Critical | ... |
> | Serious | ... |
> | Moderate | ... |
> | Minor | ... |

## Step 7: Check Existing Jira Tickets

Search for existing AQA triage tickets via JQL:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND labels = aqa AND labels = auto-triage AND status != Done",
    "maxResults": 50,
    "fields": ["summary", "status", "key"]
  }'
```

If the API returns a 404 on `/rest/api/3/`, retry with `/rest/api/2/`.

Count existing tickets — each represents ~20 issues already triaged. Calculate findings to skip.

## Step 8: Create Jira Tickets for New Chunks

Group the remaining (non-tracked) issues into chunks of 20. For each chunk, create a Jira ticket.

**Ticket fields:**

- **Project**: `$JIRA_PROJECT_KEY`
- **Type**: Bug
- **Summary**: `AQA accessibility violations — chunk N (<severity range>)` (max 200 chars)
- **Labels**: `["aqa", "auto-triage"]`
- **Description** — structured format for `/work-on-ticket` to parse:

```
h2. AQA Accessibility Violations — Chunk N

*Total Issues in Chunk:* 20
*Severity Range:* critical — serious
*Suite:* <suite_name> (<suite_id>)
*Run ID:* <run_id>
*Triage Date:* <today's date>

h2. Issues Summary

|| Rule ID || WCAG || Impact || Count ||
| color-contrast | 1.4.3 | serious | 5 |
| image-alt | 1.1.1 | critical | 3 |
| label | 1.3.1 | serious | 4 |

h2. Issue Details

{code:json}
[
  {
    "ruleId": "color-contrast",
    "impact": "serious",
    "wcagCriteria": ["1.4.3"],
    "needFixTitle": "Elements must meet minimum color contrast ratio thresholds",
    "selectors": ["#header > .nav-link"],
    "tagName": "a",
    "html": "<a class=\"nav-link\" href=\"/about\">About</a>",
    "flowId": "T4143",
    "flowUrl": "https://example.com/about",
    "solutions": ["Increase text color contrast ratio to at least 4.5:1"]
  }
]
{code}

h2. Notes

Created automatically by /triage-aqa on <today's date>.
Run `/work-on-ticket <TICKET_KEY>` to remediate these violations.
```

Create via Jira REST API (v3 with ADF, fall back to v2 with wiki markup).

## Step 9: Output Summary

Display a summary table:

```
## AQA Triage Summary — <today's date>

| Metric | Count |
|--------|-------|
| Total issues found | <N> |
| — Critical | <N> |
| — Serious | <N> |
| — Moderate | <N> |
| — Minor | <N> |
| Chunks created | <N> |
| Already tracked | <N> |

### New Tickets Created
| Ticket | Issues | Severity Range |
|--------|--------|----------------|
| ENG-300 | 20 | critical — serious |
| ENG-301 | 12 | moderate — minor |

### Already Tracked
| Ticket | Status |
|--------|--------|
| ENG-290 | In Progress |
```

Remind the user:
> Run `/work-on-ticket <TICKET_KEY>` to start fixing a chunk, then `/ship-ticket` when ready to create the PR.

---

## References

- For the AQA API reference, read `../aqa-usablenet/references/api-reference.md`
- For full Jira API patterns, read `../references/jira-api.md`
- For the structured ticket description format, read `../references/ticket-description-formats.md`
