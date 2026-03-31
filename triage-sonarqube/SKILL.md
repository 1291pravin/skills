---
name: triage-sonarqube
description: >
  Connect to a self-hosted SonarQube instance, fetch all open issues (Bugs,
  Vulnerabilities, Security Hotspots, Code Smells), and create Jira tickets
  with full issue context (one ticket per chunk of ~20 issues). Checks existing
  Jira tickets to avoid duplicates. Use this skill whenever the user mentions
  triage SonarQube, scan SonarQube, check SonarQube issues, create tickets for
  code quality issues, or wants to triage findings from SonarQube, even if they
  don't explicitly say "triage-sonarqube".
---

# SonarQube Triage — Fetch Issues & Create Jira Tickets

Connect to your self-hosted SonarQube instance, fetch all open issues, prioritize by severity, and create Jira tickets (one per chunk of ~20 issues) for tracking. Follow each step in order.

## Step 1: Check & Install sonar-scanner CLI

Run `sonar-scanner --version` to check if the sonar-scanner CLI is installed.

**If not installed:**

1. Detect the platform:
   - **macOS / Linux**: Run `brew install sonar-scanner`
     After install, verify the binary path: `which sonar-scanner`
     Confirm it points to a Homebrew-managed path. If it points somewhere unexpected, warn the user.
   - **Windows**: Tell the user:
     > sonar-scanner is not installed. Please download it from the official SonarSource docs — extract the archive and add the `bin` folder to your PATH.
2. After installation, verify with `sonar-scanner --version`
3. If installation fails, stop and ask the user for help

## Step 2: Resolve Server URL & Token

1. Resolve the **SonarQube server URL** in this order:
   - Check `SONAR_HOST_URL` environment variable
   - Fall back to `sonar.host.url` in `sonar-project.properties`
   - If still missing, ask the user

2. Resolve the **authentication token** in this order:
   - Check `SONAR_TOKEN` environment variable (preferred)
   - Check `sonar.token` in `sonar-project.properties` (only if the file is gitignored)
   - If still missing, ask the user to generate a token:
     > To avoid saving the token in your shell history, run:
     > `read -s SONAR_TOKEN && export SONAR_TOKEN`

3. **Security check — prevent token leakage:**
   - Check whether `sonar-project.properties` is tracked by git: `git ls-files sonar-project.properties`
   - If it IS tracked AND contains `sonar.token`, **stop immediately** and warn the user about the security risk

4. Verify connectivity:
   ```bash
   curl -s -u "$SONAR_TOKEN:" "$SONAR_HOST_URL/api/system/status"
   ```
   Expected response: `{"status":"UP"}`.

## Step 3: Validate Jira Environment Variables

Check all required Jira environment variables:

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Jira instance URL — no trailing slash |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |

If any are missing, provide copy-paste `export` commands. Do not proceed until all are set.

## Step 4: Detect Project Key

1. Read `sonar.projectKey` from `sonar-project.properties` if the file exists
2. If not found, derive from the git remote:
   - Run `git remote get-url origin`
   - Use the repository name as the project key
3. Confirm the project exists in SonarQube:
   ```
   GET $SONAR_HOST_URL/api/projects/search?projects=<key>
   Authorization: Basic base64($SONAR_TOKEN:)
   ```
   If not found, ask the user for the correct project key.

## Step 5: Fetch & Prioritize Issues

**Fetch all open issues** (paginate until all pages are retrieved):

```
GET $SONAR_HOST_URL/api/issues/search
  ?componentKeys=<project-key>
  &types=BUG,VULNERABILITY,CODE_SMELL
  &statuses=OPEN
  &severities=BLOCKER,CRITICAL,MAJOR,MINOR,INFO
  &ps=500&p=1
```

Increment `p` until `total <= p * ps`. Also fetch Security Hotspots:

```
GET $SONAR_HOST_URL/api/hotspots/search
  ?projectKey=<project-key>
  &status=TO_REVIEW
  &ps=500&p=1
```

**Sort all issues by priority:**
1. BLOCKER
2. CRITICAL
3. MAJOR
4. MINOR
5. INFO

Within the same severity, order by type: Vulnerabilities → Security Hotspots → Bugs → Code Smells.

**Display the full inventory:**

> Found **N** total issues:
>
> | Severity | Bugs | Vulnerabilities | Hotspots | Code Smells |
> |----------|------|-----------------|----------|-------------|
> | BLOCKER  | ...  | ...             | ...      | ...         |
> | CRITICAL | ...  | ...             | ...      | ...         |
> | MAJOR    | ...  | ...             | ...      | ...         |
> | MINOR    | ...  | ...             | ...      | ...         |
> | INFO     | ...  | ...             | ...      | ...         |

## Step 6: Check Existing Jira Tickets

Search for existing SonarQube triage tickets via JQL:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND labels = sonarqube AND labels = auto-triage AND status != Done",
    "maxResults": 50,
    "fields": ["summary", "status", "key"]
  }'
```

If the API returns a 404 on `/rest/api/3/`, retry with `/rest/api/2/`.

Count existing tickets — each represents ~20 issues already triaged. Calculate issues to skip.

## Step 7: Create Jira Tickets for New Chunks

Group the remaining (non-tracked) issues into chunks of 20. For each chunk, create a Jira ticket.

**Ticket fields:**

- **Project**: `$JIRA_PROJECT_KEY`
- **Type**: Bug
- **Summary**: `SonarQube issues — chunk N (<severity range>)` (max 200 chars)
- **Labels**: `["sonarqube", "auto-triage"]`
- **Description** — structured format for `/work-on-ticket` to parse:

```
h2. SonarQube Issues — Chunk N

*Total Issues in Chunk:* 20
*Severity Range:* BLOCKER — CRITICAL
*Project Key:* <sonarqube-project-key>
*SonarQube Server:* <server-url>
*Triage Date:* <today's date>

h2. Issues Summary

|| Type || BLOCKER || CRITICAL || MAJOR || MINOR ||
| Bugs | X | Y | Z | W |
| Vulnerabilities | X | Y | Z | W |
| Security Hotspots | X | Y | Z | W |
| Code Smells | X | Y | Z | W |

h2. Issue Details

{code:json}
[
  {
    "key": "proj:src/api/db.ts:42",
    "type": "VULNERABILITY",
    "severity": "BLOCKER",
    "rule": "typescript:S3649",
    "message": "Make sure this SQL query is safe",
    "component": "src/api/db.ts",
    "line": 42,
    "effort": "30min"
  },
  {
    "key": "proj:src/utils/render.ts:17",
    "type": "BUG",
    "severity": "CRITICAL",
    "rule": "typescript:S2259",
    "message": "Null pointer dereference",
    "component": "src/utils/render.ts",
    "line": 17,
    "effort": "15min"
  }
]
{code}

h2. Notes

Created automatically by /triage-sonarqube on <today's date>.
Run `/work-on-ticket <TICKET_KEY>` to remediate these issues.
```

Create via Jira REST API (v3 with ADF, fall back to v2 with wiki markup).

## Step 8: Output Summary

Display a summary table:

```
## SonarQube Triage Summary — <today's date>

| Metric | Count |
|--------|-------|
| Total issues found | <N> |
| — Bugs | <N> |
| — Vulnerabilities | <N> |
| — Security Hotspots | <N> |
| — Code Smells | <N> |
| Chunks created | <N> |
| Already tracked | <N> |

### New Tickets Created
| Ticket | Issues | Severity Range |
|--------|--------|----------------|
| ENG-400 | 20 | BLOCKER — CRITICAL |
| ENG-401 | 18 | MAJOR — MINOR |

### Already Tracked
| Ticket | Status |
|--------|--------|
| ENG-390 | In Progress |
```

Remind the user:
> Run `/work-on-ticket <TICKET_KEY>` to start fixing a chunk, then `/ship-ticket` when ready to create the PR.

---

## References

- For full Jira API patterns, read `../references/jira-api.md`
- For the structured ticket description format, read `../references/ticket-description-formats.md`
