---
name: create-release
description: >
  Plan and create a release from a list of Jira tickets and a version bump type.
  Verifies all tickets are merged to dev, creates a Jira release version, creates
  a release ticket with linked feature tickets, cuts a release branch, and bumps
  the version in package.json. Use this skill whenever the user mentions creating
  a release, planning a release, cutting a release, preparing a release, or
  provides a list of tickets with a version bump (e.g., "release ABC-101 ABC-102
  minor"), even if they don't explicitly say "create-release".
---

# Create Release

Automate the full release creation workflow: validate tickets are merged, create a Jira release version and release ticket, link all feature tickets, cut a release branch, and bump the version. Follow each step in order.

## Step 1: Validate Environment Variables

Confirm the following environment variables are set:

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Base URL of the Jira instance (e.g., `https://mycompany.atlassian.net`) |
| `JIRA_EMAIL` | Email address for Jira API authentication |
| `JIRA_API_TOKEN` | Jira API token (generate at https://id.atlassian.net/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ABC`) |

For any missing variables, provide the user with export commands:

```bash
export JIRA_URL="https://mycompany.atlassian.net"
export JIRA_EMAIL="you@company.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="ABC"
```

Do not proceed until all four variables are set.

## Step 2: Parse Input

Extract the following from the user's message:

1. **Ticket keys** — a list of Jira ticket keys separated by commas or spaces (e.g., `ABC-101, ABC-102, ABC-103` or `ABC-101 ABC-102 ABC-103`)
2. **Version bump type** — `major`, `minor`, or `patch` (default to `minor` if not specified)
3. **Explicit version** — if the user provides a specific version like `v1.3.0`, use that directly and skip the semver bump logic in Step 3

Examples:
- `Create release with ABC-101, ABC-102 minor`
- `Release ABC-101 ABC-102 ABC-103 as patch`
- `Plan release v2.0.0 with ABC-101`
- `Cut release ABC-101 ABC-102` (defaults to minor)

## Step 3: Determine Version

Read the current version from one of these sources (in order of preference):

1. `package.json` — the `version` field
2. Git tags — the latest semver tag:
   ```bash
   git tag --sort=-v:refname | head -1
   ```
3. If neither source provides a version, ask the user for the base version

If the user provided an explicit version in Step 2, use that directly. Otherwise, apply the semver bump:

- **major**: increment the major number, reset minor and patch to 0 (e.g., `1.2.3` → `2.0.0`)
- **minor**: increment the minor number, reset patch to 0 (e.g., `1.2.3` → `1.3.0`)
- **patch**: increment the patch number (e.g., `1.2.3` → `1.2.4`)

Show the user the version change:

> Current version: **v1.2.0** → New version: **v1.3.0** (minor bump)

## Step 4: Verify Tickets Merged

For each ticket key provided:

1. Fetch the Jira ticket to confirm it exists and get its summary and status:
   ```bash
   curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
     -H "Content-Type: application/json" \
     "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>?fields=summary,status,issuelinks"
   ```

2. Check if the ticket has a linked PR that is merged to `dev`. Use one of:
   - `gh pr list --search "<TICKET_KEY>" --state merged --base dev`
   - Check Jira issue links for PR URLs and verify merge status via the GitHub API

3. If a ticket is NOT merged, warn the user and ask how to proceed:
   > `ABC-103` is not merged yet. Continue without it, or wait?

Present a verification table:

```
| Ticket  | Summary              | Status | PR   | Merged to dev? |
|---------|----------------------|--------|------|----------------|
| ABC-101 | Add search feature   | Done   | #42  | Yes            |
| ABC-102 | Fix login redirect   | Done   | #45  | Yes            |
| ABC-103 | Update footer layout | In Dev | #48  | No             |
```

Only proceed with tickets that are confirmed merged (unless the user explicitly overrides).

## Step 5: Create Jira Version

Create the release version in the Jira project:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_URL/rest/api/3/version" \
  -d '{
    "name": "v1.3.0",
    "project": "'$JIRA_PROJECT_KEY'",
    "released": false,
    "releaseDate": "'$(date +%Y-%m-%d)'"
  }'
```

If the version already exists (HTTP 400 with "already exists" message), skip creation and use the existing version. Retrieve its ID for use in subsequent steps.

## Step 6: Create Release Ticket

Create a new Jira ticket for tracking the release:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_URL/rest/api/3/issue" \
  -d '{
    "fields": {
      "project": {"key": "'$JIRA_PROJECT_KEY'"},
      "summary": "Release v1.3.0",
      "issuetype": {"name": "Task"},
      "labels": ["release"],
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [
              {"type": "text", "text": "Release v1.3.0 — '$(date +%Y-%m-%d)'"}
            ]
          },
          {
            "type": "paragraph",
            "content": [
              {"type": "text", "text": "Included tickets: ABC-101, ABC-102, ABC-103"}
            ]
          }
        ]
      }
    }
  }'
```

Link each feature ticket to the release ticket:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_URL/rest/api/3/issueLink" \
  -d '{
    "type": {"name": "Relates"},
    "inwardIssue": {"key": "<RELEASE_TICKET_KEY>"},
    "outwardIssue": {"key": "<FEATURE_TICKET_KEY>"}
  }'
```

Repeat the link request for each feature ticket.

## Step 7: Set Fix Version

Update each feature ticket to set its `fixVersion` to the new version:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>" \
  -d '{
    "update": {
      "fixVersions": [{"add": {"name": "v1.3.0"}}]
    }
  }'
```

Repeat for each feature ticket included in the release.

## Step 8: Cut Release Branch

Create the release branch from `dev`:

1. Check out and pull the latest `dev`:
   ```bash
   git checkout dev && git pull origin dev
   ```

2. Create the release branch:
   ```bash
   git checkout -b release/v1.3.0
   ```

3. Bump the version in `package.json` (if it exists). Update the `"version"` field to the new version and commit:
   ```bash
   git add package.json
   git commit -m "chore(release): bump version to v1.3.0"
   ```

4. Push the release branch:
   ```bash
   git push -u origin release/v1.3.0
   ```

## Step 9: Update Release Ticket

Add a comment to the release ticket indicating the branch is ready:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_URL/rest/api/3/issue/<RELEASE_TICKET_KEY>/comment" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {"type": "text", "text": "Release branch release/v1.3.0 created. Awaiting smoke test sign-off."}
          ]
        }
      ]
    }
  }'
```

Transition the release ticket to the appropriate status (e.g., "In Progress" or "Testing"). Fetch available transitions first:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/issue/<RELEASE_TICKET_KEY>/transitions"
```

Then apply the transition:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_URL/rest/api/3/issue/<RELEASE_TICKET_KEY>/transitions" \
  -d '{"transition": {"id": "<TRANSITION_ID>"}}'
```

## Step 10: Output Summary

Present a structured summary of everything created:

```
## Release Created

| Item | Details |
|------|---------|
| Version | v1.3.0 (minor) |
| Release Ticket | ABC-150 |
| Branch | release/v1.3.0 |
| Tickets Included | ABC-101, ABC-102, ABC-103 |
| Jira Version | Created ✓ |
| Next Step | Business smoke tests on release preview |
```

---

For full Jira API patterns, read `../../references/jira-api.md`.

For branch conventions, read `../../references/git-conventions.md`.
