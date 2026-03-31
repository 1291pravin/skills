---
name: ship-ticket
description: >
  Commit local changes, create a pull request, push to GitHub, and update the
  Jira ticket status to "In Review". Use after /work-on-ticket has applied
  changes and tests pass locally. Use this skill whenever the user says
  "ship ticket", "ship it", "create PR", "push changes", "I'm done with
  the ticket", "submit ticket", or wants to finalize their work on a ticket,
  even if they don't explicitly say "ship-ticket".
---

# Ship Ticket — Commit, PR, Push, Jira Update

Finalize work on a ticket: stage and commit changes, push the branch, create a pull request, and update the Jira ticket. This skill is the final step after `/work-on-ticket` has applied changes and the user has tested locally. Follow each step in order.

## Step 1: Detect Current Context

1. Get the current branch name:
   ```bash
   git branch --show-current
   ```
2. Extract the Jira ticket key from the branch name using regex `[A-Z]+-\d+` (e.g., `fix/apiiro-ENG-123` → `ENG-123`, `feature/ENG-456-add-cart` → `ENG-456`)
3. If no ticket key is found in the branch name, ask the user:
   > I couldn't detect a Jira ticket key from the branch name `<branch>`. What is the ticket key? (e.g., ENG-123)
4. Detect the ticket type from the branch prefix:
   - `fix/apiiro-*` → label: `apiiro`, commit prefix: `fix(security)`
   - `fix/aqa-*` → label: `aqa`, commit prefix: `fix(a11y)`
   - `fix/sonarqube-*` → label: `sonarqube`, commit prefix: `fix(quality)`
   - `fix/error-*` → label: `errors`, commit prefix: `fix(<area>)`
   - `feature/*` → label: none (regular ticket), commit prefix: `feat(<area>)`

## Step 2: Validate Environment

### 2a: Check for Changes

Run `git status` to check for uncommitted changes.

- If **no changes** and **no unpushed commits** (`git log origin/<branch>..HEAD` is empty or branch has no upstream), tell the user:
  > No changes to ship. Make sure you've run `/work-on-ticket` first to apply changes.
  Stop here.
- If there are **unstaged changes**, show them and ask:
  > The following files have changes. Stage all, or select specific files?
  >
  > ```
  > M  src/components/cart.liquid
  > M  assets/cart.js
  > A  snippets/cart-drawer.liquid
  > ```

### 2b: Validate Jira Environment Variables

Confirm the following environment variables are set:

| Variable           | Required | Purpose                          |
|--------------------|----------|----------------------------------|
| `JIRA_URL`         | Yes      | Jira instance base URL           |
| `JIRA_EMAIL`       | Yes      | Email for Jira basic auth        |
| `JIRA_API_TOKEN`   | Yes      | Jira API token                   |

If any required variable is missing, print the export commands the user needs:

```bash
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="you@company.com"
export JIRA_API_TOKEN="your-api-token"
```

Do not proceed until all required variables are set.

## Step 3: Detect Package Manager & Run Pre-Ship Checks

Refer to `../references/package-manager-detection.md` for package manager detection logic.

Run a final build and test to confirm everything passes before shipping:

1. Run the build command for the detected package manager
2. Run `shopify theme check` if the Shopify CLI is available
3. Run the test command

If tests fail:
> Pre-ship checks failed:
> ```
> <test output>
> ```
> Would you like to ship anyway, or fix the issues first?

Wait for user confirmation before proceeding if checks fail.

## Step 4: Stage & Commit

1. **Stage files** — based on user's choice from Step 2a (all or selected files):
   ```bash
   git add <file1> <file2> ...
   ```
   Do not stage files that likely contain secrets (`.env`, `credentials.json`, etc.). Warn the user if such files appear in the changes.

2. **Generate commit message** based on the ticket type detected in Step 1:

   For `apiiro` tickets:
   ```
   fix(security): remediate Apiiro security findings

   Resolves <TICKET_KEY>
   ```

   For `aqa` tickets:
   ```
   fix(a11y): remediate UsableNet AQA violations

   Resolves <TICKET_KEY>
   ```

   For `sonarqube` tickets:
   ```
   fix(quality): remediate SonarQube issues

   Resolves <TICKET_KEY>
   ```

   For `errors` tickets:
   ```
   fix(<area>): <short description of the error fix>

   Resolves <TICKET_KEY>

   Root cause: <1-2 sentence explanation from the changes>
   ```

   For regular `feature` tickets:
   ```
   feat(<area>): <short description from ticket summary>

   Resolves <TICKET_KEY>
   ```

   Where `<area>` is derived from the primary directory or component being changed (e.g., `cart`, `checkout`, `auth`).

3. **Commit** the staged changes:
   ```bash
   git commit -m "<generated message>"
   ```

## Step 5: Push Branch

Push the branch to the remote:

```bash
git push -u origin HEAD
```

If the push fails (e.g., branch protection, authentication error), report the error and ask the user for guidance:
> Push failed:
> ```
> <error output>
> ```
> Please resolve the issue and let me know when ready.

## Step 6: Fetch Ticket Details for PR

Fetch the Jira ticket details to populate the PR body:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>?fields=summary,description,labels,acceptance_criteria"
```

If the v3 API returns a 404, retry with `/rest/api/2/`.

Extract: summary, description (parse ADF to plain text), labels, and acceptance criteria.

## Step 7: Create Pull Request

Determine the PR base branch:
- Default: `dev`
- If `dev` doesn't exist on the remote, use `main`

Create the PR using `gh`:

```bash
gh pr create --base dev --title "<TICKET_KEY>: <Summary>" --body "$(cat <<'EOF'
## Summary

<Ticket summary and brief description of what was implemented/fixed>

**Jira:** [<TICKET_KEY>](<JIRA_URL>/browse/<TICKET_KEY>)

## Changes

- <change 1>
- <change 2>
- <change 3>

## Test Plan

- [ ] Build passes
- [ ] Tests pass
- [ ] <acceptance criteria items from ticket>
EOF
)"
```

For specialized ticket types, enrich the PR body:

**Apiiro tickets** — add a summary table of security findings fixed:
```markdown
### Security Fixes
| Category | Fixed |
|----------|-------|
| Package Vulnerabilities (SCA) | X |
| Code Vulnerabilities (SAST) | Y |
| Exposed Secrets | Z |

### Action Items (Manual)
- [ ] Rotate exposed credentials (if any)
```

**AQA tickets** — add accessibility fix summary:
```markdown
### Accessibility Fixes
| Rule | WCAG | Count |
|------|------|-------|
| color-contrast | 1.4.3 | X |
| image-alt | 1.1.1 | Y |
```

**SonarQube tickets** — add code quality fix summary:
```markdown
### Code Quality Fixes
| Category | Fixed |
|----------|-------|
| Bugs | X |
| Vulnerabilities | Y |
| Security Hotspots | Z |
| Code Smells | W |
```

If `gh` is not installed, provide the push command and tell the user to create the PR manually in the browser.

## Step 8: Update Jira

### 8a: Add Comment with PR URL

Post a comment using ADF (Atlassian Document Format):

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "version": 1,
      "type": "doc",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {"type": "text", "text": "Pull request opened: "},
            {
              "type": "text",
              "text": "<PR_URL>",
              "marks": [{"type": "link", "attrs": {"href": "<PR_URL>"}}]
            }
          ]
        }
      ]
    }
  }' \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/comment"
```

If the v3 comment format fails (HTTP 400), fall back to v2:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"body": "Pull request opened: <PR_URL>"}' \
  "$JIRA_URL/rest/api/2/issue/<TICKET_KEY>/comment"
```

### 8b: Transition to "In Review"

Fetch the available transitions:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions"
```

Find a transition whose name contains "In Review", "Code Review", or "Review" (case-insensitive). Apply it:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"transition":{"id":"<TRANSITION_ID>"}}' \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions"
```

If no suitable transition is found, list available transitions and ask the user which one to use.

## Step 9: Final Summary

Print a summary table:

```
============================================
  Ticket Shipped — Summary
============================================
  Ticket:       ENG-123
  Branch:       fix/apiiro-ENG-123
  PR:           https://github.com/org/repo/pull/42
  Jira Status:  In Review
  Build:        Passed
  Tests:        Passed
============================================
```

---

## References

- For full Jira API patterns, read `../references/jira-api.md`
- For branch naming conventions, read `../references/git-conventions.md`
