# Jira REST API — Common Patterns

Shared reference for all skills that interact with Jira. Uses REST API with Basic auth.

## Authentication

All requests use HTTP Basic auth with `$JIRA_EMAIL:$JIRA_API_TOKEN`:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/<endpoint>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

**API version fallback:** Jira Cloud uses `/rest/api/3/`. Jira Server/Data Center uses `/rest/api/2/`. If a v3 call returns 404, retry with v2. The key difference: v3 uses Atlassian Document Format (ADF) for rich text fields; v2 uses wiki markup.

## Required Environment Variables

| Variable | Example |
|----------|---------|
| `JIRA_URL` | `https://company.atlassian.net` (no trailing slash) |
| `JIRA_EMAIL` | `dev@company.com` |
| `JIRA_API_TOKEN` | API token from https://id.atlassian.com/manage-profile/security/api-tokens |
| `JIRA_PROJECT_KEY` | `ENG` |

---

## Search Issues (JQL)

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND status = Open ORDER BY created DESC",
    "maxResults": 50,
    "fields": ["summary", "status", "priority", "created", "description", "issuetype", "fixVersions", "labels"]
  }'
```

Common JQL filters:
- By status: `status = "In Progress"`, `status != Done`
- By fix version: `fixVersion = "v1.3.0"`
- By label: `labels = auto-triage`
- By type: `issuetype = Bug`
- By linked issue: `issuekey in linkedIssues("RELEASE-123")`

## Get Issue Details

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Key response fields:
- `fields.summary` — ticket title
- `fields.description` — ADF document (v3) or wiki markup (v2)
- `fields.status.name` — current status
- `fields.issuetype.name` — Bug, Story, Task, etc.
- `fields.priority.name` — Critical, High, Medium, Low
- `fields.fixVersions[]` — linked release versions
- `fields.labels[]` — ticket labels
- `fields.issuelinks[]` — linked issues (blocks, relates to, etc.)

## Create Issue

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "fields": {
      "project": {"key": "'"$JIRA_PROJECT_KEY"'"},
      "issuetype": {"name": "Task"},
      "summary": "Release v1.3.0",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Release description here."}]
          }
        ]
      },
      "labels": ["release"]
    }
  }'
```

**v2 fallback** (plain text description):

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/2/issue" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "fields": {
      "project": {"key": "'"$JIRA_PROJECT_KEY"'"},
      "issuetype": {"name": "Task"},
      "summary": "Release v1.3.0",
      "description": "Release description here.",
      "labels": ["release"]
    }
  }'
```

Response: `{"id": "10001", "key": "ENG-456", "self": "..."}`

## Add Comment

**v3 (ADF format):**

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [{"type": "text", "text": "PR created: https://github.com/org/repo/pull/42"}]
        }
      ]
    }
  }'
```

**v2 fallback (plain text):**

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/2/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": "PR created: https://github.com/org/repo/pull/42"}'
```

## Transition Issue (Change Status)

### Step 1: Get available transitions

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Response: `{"transitions": [{"id": "21", "name": "In Progress"}, {"id": "31", "name": "Done"}]}`

### Step 2: Apply transition

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"transition": {"id": "<TRANSITION_ID>"}}'
```

Common transition names to search for:
- "In Progress", "Start Progress"
- "In Review", "Code Review"
- "Done", "Resolve Issue", "Close"
- "Ready for Testing", "QA"

If the exact name is not found, list available transitions and ask the user.

## Link Issues

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issueLink" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "type": {"name": "Relates"},
    "inwardIssue": {"key": "RELEASE-123"},
    "outwardIssue": {"key": "ENG-456"}
  }'
```

Link type names: `"Relates"`, `"Blocks"`, `"Cloners"`, `"Duplicate"`, `"Epic-Story Link"`

## Create Version (Release)

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/version" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "name": "v1.3.0",
    "description": "Minor release — ABC-101, ABC-102, ABC-103",
    "project": "'"$JIRA_PROJECT_KEY"'",
    "released": false,
    "startDate": "2026-03-29"
  }'
```

Response: `{"id": "10100", "name": "v1.3.0", "self": "..."}`

## Get Versions

```bash
curl -s \
  "$JIRA_URL/rest/api/3/project/$JIRA_PROJECT_KEY/versions" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

## Set Fix Version on Issue

```bash
curl -s -X PUT \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"fields": {"fixVersions": [{"name": "v1.3.0"}]}}'
```

## Release a Version (Mark as Released)

```bash
curl -s -X PUT \
  "$JIRA_URL/rest/api/3/version/<VERSION_ID>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "released": true,
    "releaseDate": "2026-03-29"
  }'
```
