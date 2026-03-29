---
name: work-on-ticket
description: >
  Work on a Jira ticket end-to-end: fetch ticket details, optionally pull
  Figma design specs via MCP and Shopify developer documentation via MCP,
  create a feature branch, implement the changes, run builds and tests,
  create a pull request, and update Jira status throughout. Use this skill
  whenever the user says "work on ticket", "pick up ticket", "start ticket",
  "work on ABC-123", "implement ABC-123", or references a Jira ticket key
  they want to start working on, even if they don't explicitly say
  "work-on-ticket".
---

# Work on Jira Ticket

Automate the full developer workflow for a Jira ticket: fetch context, create a branch, implement changes, test, open a PR, and keep Jira up to date. Follow each step in order.

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
- **Description** — `fields.description` (ADF format). Parse the ADF JSON into readable plain text. Preserve headings, lists, and code blocks.
- **Acceptance Criteria** — look in the description for a heading called "Acceptance Criteria" or check `fields.customfield_*` fields that contain acceptance criteria.
- **Story Points** — `fields.story_points` or `fields.customfield_10016` (common default)
- **Linked Issues** — `fields.issuelinks` (list related tickets)
- **Attachments** — `fields.attachment` (note filenames and URLs)
- **Comments** — `fields.comment.comments` (latest 5)

Display a formatted summary to the developer:

```
Ticket:    ENG-123
Summary:   Add size selector to product page
Points:    3
Status:    To Do
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

## Step 4: Fetch Design Specs (Optional — MCP)

Check if the **Figma MCP server** is available.

**If available:**

1. Scan the ticket description and attachments for Figma URLs (e.g. `https://www.figma.com/file/...` or `https://www.figma.com/design/...`).
2. Use the Figma MCP to fetch design specs:
   - Component properties and variants
   - Colors (hex values, design tokens)
   - Spacing and padding values
   - Typography (font family, size, weight, line-height)
   - Auto-layout and responsive behavior
3. Store the extracted specs for use in Step 8.

**If not available:**

Skip this step and print:

> Tip: Configure the Figma MCP server for automatic design spec fetching. See `references/mcp-setup.md`

## Step 5: Fetch Shopify Documentation (Optional — MCP)

Check if the **shopify-dev-mcp** server is available.

**If available:**

Based on the ticket context, determine relevant Shopify topics and fetch documentation:

- **Liquid templates** — if the ticket involves template changes
- **Section schema** — if building or modifying sections
- **Metafields** — if the ticket references custom data
- **Cart API / AJAX API** — if cart functionality is involved
- **Theme architecture** — for structural changes (layouts, templates, snippets)
- **Shopify Functions / Extensions** — if extending checkout or storefront

Store the fetched documentation for use in Step 8.

**If not available:**

Skip this step and print:

> Tip: Configure the shopify-dev-mcp server for automatic Shopify documentation fetching. See `references/mcp-setup.md`

## Step 6: Create Feature Branch

Create a feature branch from `dev`:

1. Fetch the latest from the remote:
   ```bash
   git fetch origin
   ```
2. Generate a branch name: `feature/<TICKET_KEY>-<slug>` where `<slug>` is the ticket summary lowercased, spaces replaced with hyphens, truncated to 40 characters, special characters removed.
   Example: `feature/ENG-123-add-size-selector-to-product-page`
3. Check if the branch already exists locally or on the remote:
   ```bash
   git branch --list "feature/<TICKET_KEY>-*"
   git branch -r --list "origin/feature/<TICKET_KEY>-*"
   ```
   - **If it exists**: Ask the user — "Branch `feature/ENG-123-...` already exists. Continue working on it, or create a fresh branch?"
     - Continue: check out the existing branch and pull latest.
     - Fresh: delete the old branch and create a new one.
   - **If it does not exist**: Create and check out:
     ```bash
     git checkout -b feature/<TICKET_KEY>-<slug> origin/dev
     ```

## Step 7: Transition Jira to "In Progress"

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

If the ticket is already "In Progress" (check `fields.status.name`), skip this step and print:

> Ticket is already In Progress — skipping transition.

## Step 8: Implement Changes

Use all gathered context to implement the ticket:

- **Jira details** — summary, description, acceptance criteria
- **Figma specs** (if fetched in Step 4) — colors, spacing, typography, component structure
- **Shopify docs** (if fetched in Step 5) — correct Liquid syntax, section schema patterns, API usage

Follow Shopify theme development best practices:

- Use **Liquid** for templates and rendering logic
- Build reusable **sections** and **snippets**
- Define settings via **settings_schema** with proper types and defaults
- For JavaScript: follow existing patterns in the codebase (check `assets/` for conventions)
- Keep CSS scoped to the component or section
- Use semantic HTML and ensure accessibility (ARIA attributes, alt text)

Work through each acceptance criterion. After implementing, review the diff to verify nothing was missed.

## Step 9: Build & Test

1. Detect the package manager (check `package.json`, lock files).
2. Install dependencies if needed.
3. Run the build:
   ```bash
   npm run build   # or yarn build / pnpm build
   ```
4. Run `shopify theme check` if the Shopify CLI is available — fix any errors or warnings.
5. Run tests if a test script exists:
   ```bash
   npm test
   ```
6. Compare results against the baseline. If there are regressions:
   - Attempt to fix the issue.
   - Re-run the build and tests.
   - Retry up to **3 attempts**. If regressions persist after 3 attempts, stop and report the failures to the developer.

## Step 10: Create Pull Request

Stage and commit changes, then create a PR targeting `dev`:

```bash
gh pr create --base dev --title "<TICKET_KEY>: <Summary>" --body "$(cat <<'EOF'
## Summary
<Ticket summary and brief description of what was implemented>

**Jira:** [<TICKET_KEY>](<JIRA_URL>/browse/<TICKET_KEY>)

## Changes
- <change 1>
- <change 2>
- <change 3>

## Screenshots
<!-- Add screenshots here if this is a UI change -->

## Figma
<!-- Link to Figma design if available -->
<Figma URL from ticket, or "N/A">

## Test Plan
- [ ] Build passes
- [ ] Theme check passes (no new errors)
- [ ] Acceptance criteria verified
- [ ] Responsive behavior tested
- [ ] Cross-browser tested (Chrome, Safari, Firefox)
EOF
)"
```

Push the branch first if it has not been pushed:

```bash
git push -u origin HEAD
```

## Step 11: Update Jira

### Add a comment with the PR URL

Post a comment using ADF (Atlassian Document Format) v3:

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

### Transition to "In Review"

Fetch transitions again and find one whose name contains "In Review", "Code Review", or "Review" (case-insensitive). Apply it the same way as Step 7.

### Final Summary

Print a summary table:

```
============================================
  Ticket Complete — Summary
============================================
  Ticket:       ENG-123
  Branch:       feature/ENG-123-add-size-selector
  PR:           https://github.com/org/repo/pull/42
  Jira Status:  In Review
  Build:        Passed
  Tests:        Passed
  Theme Check:  Passed (0 errors)
============================================
```

---

## References

- For full Jira API patterns, read `../../references/jira-api.md`
- For branch naming conventions, read `../../references/git-conventions.md`
