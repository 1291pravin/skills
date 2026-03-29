---
name: hotfix
description: >
  Hotfix a Shopify theme issue end-to-end: parse a Jira ticket key from user
  input, fetch ticket details via the Jira REST API, create a hotfix branch
  from main, implement the minimal fix, verify with build and tests, create a
  PR to main and a sync PR to dev, and update the Jira ticket with both PR
  links. Use this skill whenever the user mentions hotfix, urgent fix, prod
  fix, production hotfix, emergency fix, quick fix to main, or provides a
  ticket key with urgency context, even if they don't explicitly say "hotfix".
---

# Hotfix — Jira Ticket to Production Fix to PR

Parse a Jira ticket, create a hotfix branch from main, implement a minimal targeted fix, verify with build and tests, open PRs to both main and dev, and update the Jira ticket. Follow each step in order.

For full Jira API patterns, read `../../references/jira-api.md`
For branch naming conventions, read `../../references/git-conventions.md`

## Step 1: Validate Environment Variables

Check all required environment variables at once. Do not stop at the first missing one — collect all missing vars and report them together.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Jira instance URL (e.g., `https://company.atlassian.net`) — no trailing slash |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |

If any are missing, tell the user exactly which ones and provide copy-paste `export` commands:

> The following environment variables are missing:
> ```bash
> export JIRA_URL=https://company.atlassian.net
> export JIRA_EMAIL=your-email@company.com
> export JIRA_API_TOKEN=your-token-here
> export JIRA_PROJECT_KEY=ENG
> ```
> Set them and let me know when ready.

Do not proceed until all required variables are set.

## Step 2: Parse Ticket Key

Extract the Jira ticket key from the user's input. Support these input formats:

- `Hotfix ABC-123`
- `hotfix ABC-123`
- `ABC-123`
- `Fix ENG-99 urgently`
- Any string containing a pattern matching `[A-Z]+-\d+` (e.g., `ENG-123`, `ABC-99`, `SHOP-4567`)

If the input contains multiple ticket keys, use the first one found.

If no ticket key is found, ask the user:
> I couldn't find a Jira ticket key in your message. Please provide one (e.g., `ENG-123`).

Store the extracted key as `<TICKET_KEY>` for use in all subsequent steps.

## Step 3: Fetch Jira Ticket

Fetch the full issue details via the Jira REST API v3:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/` (Jira Server/Data Center uses v2):

```bash
curl -s \
  "$JIRA_URL/rest/api/2/issue/<TICKET_KEY>" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Extract from the response:

1. **Summary** — the ticket title
2. **Description** — full description body (parse ADF for v3, plain text for v2)
3. **Acceptance Criteria** — look for a custom field or a section labeled "Acceptance Criteria" in the description
4. **Priority** — the ticket priority (Critical, High, Medium, Low)

If the ticket is not found on either API version, tell the user:
> Could not find ticket `<TICKET_KEY>`. Please verify the ticket key and that your Jira credentials have access.

Display a summary before proceeding:
> **Ticket:** <TICKET_KEY> — <summary>
> **Priority:** <priority>
> **Description:** <first 2-3 sentences>

## Step 4: Create Hotfix Branch

Create a hotfix branch from main using the ticket key and a slug derived from the ticket summary.

1. **Check for an existing hotfix branch** (resume detection):
   ```bash
   git branch -a --list '*hotfix/<TICKET_KEY>*'
   ```

   If a matching branch exists:
   > Found existing hotfix branch `hotfix/<TICKET_KEY>-<slug>`. Resuming work on this branch.

   Check out that branch and skip to Step 5.

2. **Create a new branch** if none exists:
   ```bash
   git fetch origin main
   git checkout -b hotfix/<TICKET_KEY>-<slug> origin/main
   ```

   Generate `<slug>` by taking the ticket summary, lowercasing it, replacing spaces and special characters with hyphens, and truncating to 40 characters. Example: `hotfix/ENG-123-fix-cart-page-crash`.

## Step 5: Implement the Fix

Analyze the ticket details from Step 3 and implement the fix:

1. **Understand the issue** — read the summary, description, and acceptance criteria to identify what needs to change
2. **Find relevant code** — search the repository for files related to the issue (Shopify theme files in `sections/`, `snippets/`, `templates/`, `assets/`, `layout/`, `config/`, etc.)
3. **Write the fix** — make the minimal set of changes needed to resolve the issue
4. **Keep changes focused** — do not refactor surrounding code, do not add unrelated improvements, do not change formatting outside the fix scope

If the ticket description is vague or insufficient, ask the user for clarification before making changes:
> The ticket description doesn't provide enough detail to determine the fix. Can you clarify what the expected behavior should be?

## Step 6: Build & Test

Detect the package manager and run build and test commands.

### Detect Package Manager

Check in this order (first match wins):

1. `package.json` `packageManager` field (e.g., `"packageManager": "pnpm@9.0.0"`)
2. `bun.lockb` or `bun.lock` exists — **bun**
3. `pnpm-lock.yaml` exists — **pnpm**
4. `yarn.lock` exists — **yarn**
   - If `.yarnrc.yml` also exists or `packageManager` contains `yarn@4` or higher — **Yarn 4 (Berry)**
   - Otherwise — **Yarn Classic (v1)**
5. `package-lock.json` exists — **npm**

Use the detected package manager for all commands:

| Action | npm | yarn v1 | yarn v4 | pnpm | bun |
|--------|-----|---------|---------|------|-----|
| Install deps | `npm ci` | `yarn install --frozen-lockfile` | `yarn install --immutable` | `pnpm install --frozen-lockfile` | `bun install --frozen-lockfile` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

### Baseline Snapshot

Before verifying the fix, capture a baseline:

1. Stash the fix changes: `git stash`
2. Run the build and test commands, capture full output
3. Record every failing test by name/path as the **baseline failures list**
4. Restore the fix: `git stash pop`

### Verify the Fix

1. Run the build command
2. If the build fails and the error is new (not in baseline), attempt to fix it — max 3 attempts
3. Run the test command and compare results against the baseline:
   - Tests failing before AND still failing — **pre-existing, not caused by this fix**
   - Tests passing before AND now failing — **regression introduced by the fix, must be addressed**
   - Tests failing before AND now passing — **bonus improvement**
4. If there are regressions, attempt to fix them (max 3 attempts)
5. If still failing after 3 attempts, ask the user for help:
   > The fix introduced test failures that I couldn't resolve:
   > - `<test name>` — <failure description>
   > Would you like to review and fix manually, or should I revert the changes?
6. **NEVER modify existing tests** to make them pass — only fix the source code

## Step 7: Create PR to Main

Stage, commit, push, and create a pull request targeting main.

1. **Stage only the modified files** (do not stage unrelated changes):
   ```bash
   git add <file1> <file2> ...
   ```

2. **Commit** with a message referencing the Jira ticket:
   ```bash
   git commit -m "hotfix(<area>): <short description>

   Resolves <TICKET_KEY>
   "
   ```

3. **Push and create PR:**
   ```bash
   git push -u origin hotfix/<TICKET_KEY>-<slug>

   gh pr create \
     --base main \
     --title "hotfix(<area>): <short description> [<TICKET_KEY>]" \
     --body "$(cat <<'EOF'
   ## Summary

   Hotfix for <TICKET_KEY>: <ticket summary>

   **Jira:** <JIRA_URL>/browse/<TICKET_KEY>

   ## Changes

   - <list each file changed and what was changed>

   ## Test Results

   - Build: PASS
   - Tests: PASS (<N> passing, <B> pre-existing failures)
   EOF
   )"
   ```

If `gh` is not installed, provide the push command and tell the user to create the PR manually.

Store the PR URL as `<MAIN_PR_URL>` for use in later steps.

## Step 8: Create Sync PR to Dev

Keep the dev branch in sync by cherry-picking the hotfix into a new branch targeting dev.

### Option A: Cherry-pick (preferred)

1. **Create a sync branch from dev:**
   ```bash
   git fetch origin dev
   git checkout -b hotfix/<TICKET_KEY>-<slug>-sync-dev origin/dev
   ```

2. **Cherry-pick the hotfix commit:**
   ```bash
   git cherry-pick <hotfix-commit-sha>
   ```

3. **If the cherry-pick succeeds**, push and create a PR:
   ```bash
   git push -u origin hotfix/<TICKET_KEY>-<slug>-sync-dev

   gh pr create \
     --base dev \
     --title "sync: cherry-pick hotfix <TICKET_KEY> to dev" \
     --body "$(cat <<'EOF'
   ## Summary

   Cherry-pick of hotfix <TICKET_KEY> from main to keep dev in sync.

   **Main PR:** <MAIN_PR_URL>
   **Jira:** <JIRA_URL>/browse/<TICKET_KEY>

   ## Changes

   Same changes as <MAIN_PR_URL> — cherry-picked to dev.
   EOF
   )"
   ```

### Option B: Merge PR (if cherry-pick has conflicts)

If the cherry-pick fails due to conflicts, abort and create a merge PR instead:

```bash
git cherry-pick --abort
git checkout -b sync/main-to-dev-<TICKET_KEY> origin/dev
git merge origin/main --no-edit
```

If the merge also has conflicts, tell the user:
> Cherry-pick and merge both have conflicts. Please resolve them manually on branch `sync/main-to-dev-<TICKET_KEY>`.

If the merge succeeds, push and create the PR targeting dev:

```bash
git push -u origin sync/main-to-dev-<TICKET_KEY>

gh pr create \
  --base dev \
  --title "sync: merge main to dev (includes hotfix <TICKET_KEY>)" \
  --body "$(cat <<'EOF'
## Summary

Merge main into dev to sync hotfix <TICKET_KEY>.

**Main PR:** <MAIN_PR_URL>
**Jira:** <JIRA_URL>/browse/<TICKET_KEY>
EOF
)"
```

Store the dev PR URL as `<DEV_PR_URL>`.

## Step 9: Update Jira Ticket

After both PRs are created, update the Jira ticket with comments and transition the status.

### 9a: Add Comment with Both PR URLs

Post a comment with links to both PRs using the v3 ADF format:

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
          "content": [
            {"type": "text", "text": "Hotfix PRs created:"}
          ]
        },
        {
          "type": "bulletList",
          "content": [
            {
              "type": "listItem",
              "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Main: <MAIN_PR_URL>"}]}]
            },
            {
              "type": "listItem",
              "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dev sync: <DEV_PR_URL>"}]}]
            }
          ]
        }
      ]
    }
  }'
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/` using plain text body:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/2/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": "Hotfix PRs created:\n- Main: <MAIN_PR_URL>\n- Dev sync: <DEV_PR_URL>"}'
```

### 9b: Transition Ticket to "In Review"

Fetch available transitions:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Look for a transition named "In Review", "Code Review", "In Progress", or similar. If found, apply it:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/transitions" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"transition": {"id": "<transition_id>"}}'
```

If no suitable transition is found, tell the user:
> Could not find a matching transition. Available transitions are: <list>. Would you like me to apply one of these?

### Final Output

Report the completed hotfix:

```
## Hotfix Complete

| Item | Details |
|------|---------|
| Ticket | <TICKET_KEY>: <summary> |
| Priority | <priority> |
| Branch | hotfix/<TICKET_KEY>-<slug> |
| Files Changed | <list of files> |
| Main PR | <MAIN_PR_URL> |
| Dev Sync PR | <DEV_PR_URL> |
| Build | PASS |
| Tests | PASS (<N> passing, <B> pre-existing failures) |
| Jira Status | Transitioned to In Review |
```
