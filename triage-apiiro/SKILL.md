---
name: triage-apiiro
description: >
  Scan the current repository for Apiiro security findings, categorize them
  by type and severity, and create Jira tickets with full finding context
  (one ticket per chunk of ~20 findings). Checks existing Jira tickets to
  avoid duplicates. Use this skill whenever the user mentions triage Apiiro,
  scan Apiiro, check Apiiro findings, create tickets for security issues,
  or wants to triage security findings from Apiiro, even if they don't
  explicitly say "triage-apiiro".
---

# Apiiro Security Triage — Scan & Create Jira Tickets

Scan the current repository for Apiiro security findings, categorize and prioritize them, and create Jira tickets (one per chunk of ~20 findings) for tracking. Follow each step in order.

## Step 1: Check & Install Apiiro CLI

Run `apiiro --version` to check if the Apiiro CLI is installed.

**If not installed:**

1. Detect the platform:
   - **macOS / Linux**: Run `brew tap apiiro/tap && brew install apiiro`
   - **Windows**: Tell the user:
     > Apiiro CLI is not installed. Please download it from https://github.com/apiiro/cli-releases/releases — pick the Windows binary, extract it, and add it to your PATH.
     > Once installed, let me know and I'll continue.
2. After installation, verify with `apiiro --version`
3. If installation fails, stop and ask the user for help — do not proceed without a working CLI

## Step 2: Authenticate

Run `apiiro auth status` to check if the user is logged in.

**If not authenticated:**

Tell the user:
> You need to log in to Apiiro. Please run `apiiro login` in your terminal — it will open a browser for OAuth authentication.
>
> In Claude Code, you can type `! apiiro login` to run it directly in this session.

Wait for the user to confirm they have logged in before proceeding. Do not skip this step.

## Step 3: Validate Jira Environment Variables

Check all required environment variables at once. Do not stop at the first missing one — collect all missing vars and report them together.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Jira instance URL (e.g., `https://company.atlassian.net`) — no trailing slash |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |

If any are missing, tell the user exactly which ones and provide copy-paste `export` commands. Do not proceed until all required variables are set.

## Step 4: Detect Current Repository

Identify which repo to query in Apiiro:

1. Run `git remote get-url origin` to get the remote URL
2. Extract the `org/repo` name from the URL — handle all formats:
   - `https://github.com/org/repo.git`
   - `git@github.com:org/repo.git`
   - GitLab, Bitbucket, and other hosts
3. Use this identifier to scope all Apiiro queries to this repo only

**If the remote URL can't be determined**, ask the user:
> I couldn't detect the repository. What is the repo name or identifier in Apiiro?

## Step 5: Fetch & Categorize Findings

Run the Apiiro CLI to get all security findings for this repo:

```bash
apiiro risks --repo <repo-identifier> --output json
```

If the command fails or the repo isn't found in Apiiro, ask the user for the correct Apiiro repo identifier and retry.

Parse the JSON output and categorize findings into:
- **SCA**: Vulnerable open-source packages
- **SAST**: Code-level security vulnerabilities (OWASP Top 10)
- **Secrets**: Exposed API keys, tokens, passwords, credentials
- **Misconfigurations**: Insecure defaults, missing security headers, permissive CORS
- **PII/PHI/PCI**: Personal or sensitive data exposure in code
- **Supply Chain**: CI/CD misconfigs, weak branch protections
- **Other**: Anything that doesn't fit the above

**Sort all findings by priority:**
1. Secrets (immediate risk)
2. Vulnerabilities — SCA (CRITICAL → HIGH → MEDIUM → LOW)
3. Vulnerabilities — SAST (CRITICAL → HIGH → MEDIUM → LOW)
4. Misconfigurations
5. PII/PHI/PCI
6. Supply Chain
7. Other

Display a summary to the user:

> Found **N** total Apiiro findings:
>
> | Category | Count | Severity Range |
> |----------|-------|----------------|
> | SCA | ... | CRITICAL-LOW |
> | SAST | ... | HIGH-MEDIUM |
> | Secrets | ... | — |
> | Misconfigurations | ... | — |
> | Other | ... | — |

## Step 6: Check Existing Jira Tickets

For each chunk of 20 findings, check if a Jira ticket already exists to avoid duplicates.

Search via JQL:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND labels = apiiro AND labels = auto-triage AND status != Done",
    "maxResults": 50,
    "fields": ["summary", "status", "key"]
  }'
```

If the API returns a 404 on `/rest/api/3/`, retry with `/rest/api/2/`.

Count existing tickets — each existing ticket represents ~20 findings already triaged. Calculate how many findings to skip based on existing ticket count.

Mark chunks that already have tickets as **"already tracked"**.

## Step 7: Create Jira Tickets for New Chunks

Group the remaining (non-tracked) findings into chunks of 20. For each chunk, create a Jira ticket.

**Ticket fields:**

- **Project**: `$JIRA_PROJECT_KEY`
- **Type**: Bug
- **Summary**: `Apiiro security findings — chunk N (<severity range>)` (max 200 chars)
- **Labels**: `["apiiro", "auto-triage"]`
- **Description** — use the following structured format so `/work-on-ticket` can parse it:

```
h2. Apiiro Security Findings — Chunk N

*Total Findings in Chunk:* 20
*Severity Range:* CRITICAL — HIGH
*Scanned Repository:* <org/repo>
*Triage Date:* <today's date>

h2. Findings Summary

|| Category || Count || Severity Range ||
| SCA | X | CRITICAL-HIGH |
| SAST | Y | HIGH-MEDIUM |
| Secrets | Z | — |
| Misconfigurations | W | — |

h2. Finding Details

{code:json}
[
  {
    "id": "<finding-id>",
    "category": "SCA",
    "severity": "CRITICAL",
    "package": "lodash",
    "currentVersion": "4.17.15",
    "safeVersion": "4.17.21",
    "cve": "CVE-2021-23337",
    "filePath": "package.json",
    "description": "Prototype pollution vulnerability"
  },
  {
    "id": "<finding-id>",
    "category": "SAST",
    "severity": "HIGH",
    "type": "SQL Injection",
    "filePath": "src/api/users.ts",
    "lineNumber": 42,
    "description": "User input concatenated into SQL query"
  }
]
{code}

h2. Notes

Created automatically by /triage-apiiro on <today's date>.
Run `/work-on-ticket <TICKET_KEY>` to remediate these findings.
```

Create the ticket via the Jira REST API:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "fields": {
      "project": {"key": "'"$JIRA_PROJECT_KEY"'"},
      "issuetype": {"name": "Bug"},
      "summary": "Apiiro security findings — chunk N (CRITICAL/HIGH)",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [...]
      },
      "labels": ["apiiro", "auto-triage"]
    }
  }'
```

If v3 fails, fall back to v2 with wiki markup. Record the created ticket key for each chunk.

## Step 8: Output Summary

Display a summary table to the user:

```
## Apiiro Triage Summary — <today's date>

| Metric | Count |
|--------|-------|
| Total findings scanned | <N> |
| — SCA (packages) | <N> |
| — SAST (code) | <N> |
| — Secrets | <N> |
| — Misconfigurations | <N> |
| — Other | <N> |
| Chunks created | <N> |
| Already tracked | <N> |

### New Tickets Created
| Ticket | Findings | Severity Range |
|--------|----------|----------------|
| ENG-200 | 20 | CRITICAL — HIGH |
| ENG-201 | 15 | MEDIUM — LOW |

### Already Tracked
| Ticket | Status |
|--------|--------|
| ENG-190 | In Progress |
```

If no new findings were found:
> No new Apiiro findings. All existing findings are already tracked in Jira.

Remind the user:
> Run `/work-on-ticket <TICKET_KEY>` to start fixing a chunk, then `/ship-ticket` when ready to create the PR.

---

## References

- For full Jira API patterns, read `../references/jira-api.md`
- For the structured ticket description format, read `../references/ticket-description-formats.md`
