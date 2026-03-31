---
name: work-on-ticket
description: >
  Work on a Jira ticket: fetch ticket details, detect the ticket type via
  labels (apiiro, aqa, sonarqube, errors, or regular feature), load the
  appropriate fix strategy, create a branch, implement changes, and run
  builds and tests. Does NOT create a PR or push — use /ship-ticket for
  that. Optionally pulls Figma design specs and Shopify docs via MCP for
  regular feature tickets. Use this skill whenever the user says "work on
  ticket", "pick up ticket", "start ticket", "work on ABC-123", "implement
  ABC-123", or references a Jira ticket key they want to start working on,
  even if they don't explicitly say "work-on-ticket".
---

# Work on Jira Ticket

Automate the developer workflow for a Jira ticket: fetch context, detect ticket type, create a branch, load the right fix strategy, implement changes, and test. Follow each step in order.

**Important:** This skill does NOT create a PR or push to GitHub. After changes are applied and tested, the user should test locally and then run `/ship-ticket` to finalize.

## Step 1: Validate Environment Variables

Confirm the following environment variables are set:

| Variable           | Required | Purpose                          |
|--------------------|----------|----------------------------------|
| `JIRA_URL`         | Yes      | Jira instance base URL           |
| `JIRA_EMAIL`       | Yes      | Email for Jira basic auth        |
| `JIRA_API_TOKEN`   | Yes      | Jira API token                   |
| `JIRA_PROJECT_KEY` | Yes      | Default project key (e.g. `ENG`) |

If any required variable is missing, print the export commands the user needs:

```bash
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="you@company.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="ENG"
```

Do not proceed until all required variables are set.

## Step 2: Parse Ticket Key

Extract the Jira ticket key from the user's input. Support these formats:

- `Work on ticket ABC-123`
- `ABC-123` (bare key)
- `pick up ENG-456`
- `https://company.atlassian.net/browse/ENG-123` (URL — extract key from path)

If no key is found, ask the user to provide one. Normalize the key to uppercase (e.g. `eng-123` becomes `ENG-123`).

## Step 3: Fetch Jira Ticket Details

Fetch the issue details from the Jira REST API:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>?expand=renderedFields"
```

Extract the following fields:

- **Summary** — `fields.summary`
- **Description** — `fields.description` (ADF format). Parse the ADF JSON into readable plain text.
- **Labels** — `fields.labels[]` (used for routing in Step 4)
- **Acceptance Criteria** — look in the description for a heading called "Acceptance Criteria" or check `fields.customfield_*` fields
- **Story Points** — `fields.story_points` or `fields.customfield_10016`
- **Linked Issues** — `fields.issuelinks`
- **Attachments** — `fields.attachment`
- **Comments** — `fields.comment.comments` (latest 5)

Display a formatted summary to the developer:

```
Ticket:    ENG-123
Summary:   Add size selector to product page
Points:    3
Status:    To Do
Labels:    apiiro, auto-triage
---
Description:
  <parsed description text>
---
Acceptance Criteria:
  - <criterion 1>
  - <criterion 2>
---
Attachments: design-spec.png, mockup.fig
Linked Issues: ENG-100 (blocked by), ENG-110 (relates to)
```

## Step 4: Detect Fix Strategy via Labels

Read the ticket's `fields.labels[]` array and route to the appropriate fix strategy.

**Routing table** (check in this order — first match wins):

| Label Found | Strategy File | Branch Prefix | Description |
|-------------|--------------|---------------|-------------|
| `apiiro` | `fix-strategies/apiiro.md` | `fix/apiiro-<KEY>` | Apiiro security finding remediation |
| `aqa` | `fix-strategies/aqa.md` | `fix/aqa-<KEY>` | AQA accessibility violation remediation |
| `sonarqube` | `fix-strategies/sonarqube.md` | `fix/sonarqube-<KEY>` | SonarQube issue remediation |
| `errors` or `auto-triage` | `fix-strategies/errors.md` | `fix/error-<KEY>` | Production error fix |
| *(none of the above)* | `fix-strategies/default.md` | `feature/<KEY>-<slug>` | Standard feature implementation |

Tell the user which strategy was detected:

> Detected label **apiiro** — loading Apiiro security fix strategy.

Or if no specialized label:

> No specialized label found — using default implementation strategy.

### Validate Strategy-Specific Environment Variables

Some strategies require additional environment variables:

- **errors strategy**: Also requires `GCLOUD_PROJECT_ID`, `SENTRY_URL`, `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_AUTH_TOKEN`
- **apiiro strategy**: Requires Apiiro CLI to be installed and authenticated
- **sonarqube strategy**: Requires `SONAR_HOST_URL`, `SONAR_TOKEN`
- **aqa strategy**: Requires `AQA_API_KEY`, `AQA_TEAM_SLUG`

Check the required variables for the detected strategy and report any missing ones before proceeding.

## Step 5: Create Branch

Create a branch based on the detected strategy:

1. Fetch the latest from the remote:
   ```bash
   git fetch origin
   ```

2. Generate a branch name using the prefix from Step 4:
   - For fix strategies: `<prefix>-<TICKET_KEY>` (e.g., `fix/apiiro-ENG-123`)
   - For default: `feature/<TICKET_KEY>-<slug>` where `<slug>` is the ticket summary lowercased, spaces replaced with hyphens, truncated to 40 characters, special characters removed

3. Check if the branch already exists:
   ```bash
   git branch --list "<branch-pattern>"
   git branch -r --list "origin/<branch-pattern>"
   ```
   - **If it exists**: Ask the user — continue working on it, or create a fresh branch?
   - **If it does not exist**: Create and check out:
     ```bash
     git checkout -b <branch-name> origin/dev
     ```

## Step 6: Transition Jira to "In Progress"

Fetch the available transitions for the ticket:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions"
```

Find a transition whose name contains "In Progress", "Start Progress", or "In Development" (case-insensitive). Apply it:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"transition":{"id":"<TRANSITION_ID>"}}' \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions"
```

If the ticket is already "In Progress", skip and print:
> Ticket is already In Progress — skipping transition.

## Step 7: Execute Fix Strategy

Read the fix strategy file identified in Step 4 and follow its instructions to implement the changes.

Each strategy file contains:
- How to parse the ticket description for structured data
- Specific remediation guidance for that type of issue
- Build and test verification steps

**Read the strategy file** from the `fix-strategies/` directory relative to this skill and follow it step by step.

## Step 8: Report Results

After the fix strategy completes (including build/test verification), print a summary:

```
============================================
  Work Complete — Ready for Testing
============================================
  Ticket:       ENG-123
  Strategy:     apiiro (security remediation)
  Branch:       fix/apiiro-ENG-123
  Build:        Passed
  Tests:        Passed
  Jira Status:  In Progress
============================================

  Review the changes locally, then run
  /ship-ticket to create the PR and
  update Jira.
============================================
```

**Do NOT** create a PR, push to the remote, or update Jira status beyond "In Progress". The user should:
1. Test the changes locally
2. Run `/ship-ticket` when satisfied

---

## References

- For full Jira API patterns, read `../references/jira-api.md`
- For branch naming conventions, read `../references/git-conventions.md`
- For ticket description formats (data contract), read `../references/ticket-description-formats.md`
- For package manager detection, read `../references/package-manager-detection.md`
