---
name: release-notes
description: >
  Generate structured release notes from Jira tickets and linked PR descriptions,
  then publish them to Confluence. Fetches all tickets in a Jira release version,
  categorizes them by type (features, bug fixes, improvements, breaking changes),
  enriches entries with PR context from GitHub, and pushes the formatted notes as
  a Confluence page. Use this skill whenever the user mentions release notes,
  changelog, what's in the release, generate notes, summarize the release, or
  prepare release documentation, even if they don't explicitly say "release-notes".
---

# Release Notes — Jira Tickets + PRs → Confluence

Gather all tickets in a Jira release version, enrich with PR descriptions from GitHub, generate categorized release notes, and publish to Confluence. Follow each step in order.

## Step 1: Validate Environment Variables

Check all required environment variables at once. Do not stop at the first missing one — collect all missing vars and report them together.

**Required variables:**

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Jira instance URL (e.g., `https://company.atlassian.net`) — no trailing slash |
| `JIRA_EMAIL` | Jira user email (for Basic auth) |
| `JIRA_API_TOKEN` | Jira API token |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `ENG`) |
| `CONFLUENCE_URL` | Confluence instance URL (e.g., `https://company.atlassian.net`) — no trailing slash |
| `CONFLUENCE_SPACE_KEY` | Confluence space key to publish into |
| `CONFLUENCE_EMAIL` | Confluence user email (for Basic auth) |
| `CONFLUENCE_TOKEN` | Confluence API token |

If any are missing, tell the user exactly which ones and provide copy-paste `export` commands:

> The following environment variables are missing:
> ```bash
> export JIRA_URL=https://company.atlassian.net
> export JIRA_API_TOKEN=your-token-here
> export CONFLUENCE_URL=https://company.atlassian.net
> export CONFLUENCE_TOKEN=your-token-here
> ```
> Set them and let me know when ready.

Do not proceed until all required variables are set.

## Step 2: Identify Release

Ask the user for the version string (e.g., `v1.3.0`) or Jira release/version name.

Fetch all versions for the project:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/project/$JIRA_PROJECT_KEY/versions" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Find the matching version by `name` field. Match against the user-provided string (try both with and without a `v` prefix).

If no exact match is found, list available versions and ask the user to pick:

> I found these versions for **$JIRA_PROJECT_KEY**:
>
> | # | Version | Status | Release Date |
> |---|---------|--------|--------------|
> | 1 | v1.3.0  | Released | 2026-03-28 |
> | 2 | v1.2.1  | Released | 2026-03-15 |
> | 3 | v1.4.0  | Unreleased | — |
>
> Which version would you like to generate release notes for?

Store the matched version `name` and `id` for subsequent steps.

## Step 3: Fetch Release Tickets

Search Jira for all tickets in this release using JQL:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{
    "jql": "project = '"$JIRA_PROJECT_KEY"' AND fixVersion = \"<version_name>\" ORDER BY issuetype ASC, priority DESC",
    "maxResults": 100,
    "fields": ["summary", "issuetype", "description", "priority", "labels", "assignee", "status"]
  }'
```

If the API returns a 404 or error on `/rest/api/3/`, retry with `/rest/api/2/`.

For each ticket, extract:
- **Key** (e.g., `ENG-101`)
- **Summary**
- **Issue type** (Story, Bug, Task, etc.)
- **Priority**
- **Labels** (check for `breaking-change`)
- **Assignee** (for the contributors list)

If no tickets are found, tell the user:
> No tickets found with fixVersion = "<version_name>". Verify that tickets are assigned to this version in Jira.

## Step 4: Fetch PR Descriptions

For each ticket, look for linked PR URLs in two places:

1. **Issue links** — check the ticket's `issuelinks` field for remote links pointing to GitHub
2. **Comments** — scan comments for GitHub PR URLs matching `https://github.com/.*/pull/\d+`

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

Also check remote links:

```bash
curl -s \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/remotelink" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
```

For each discovered PR URL, extract `{owner}`, `{repo}`, and `{number}` from the URL, then fetch PR details:

```bash
gh api repos/{owner}/{repo}/pulls/{number} --jq '{title: .title, body: .body, number: .number, user: .user.login}'
```

If `gh` is not installed or the command fails, skip PR enrichment gracefully and continue with Jira data only. Inform the user:
> GitHub CLI not available — skipping PR description enrichment. Release notes will use Jira ticket data only.

Store the PR number and author for each ticket that has a linked PR.

## Step 5: Categorize Changes

Group tickets into categories based on issue type and labels:

| Category | Issue Types |
|----------|-------------|
| **Features** | Story, New Feature |
| **Bug Fixes** | Bug |
| **Improvements** | Task, Improvement, Enhancement, Sub-task |
| **Breaking Changes** | Any ticket with label `breaking-change` |

A ticket with the `breaking-change` label appears in **Breaking Changes** instead of its type-based category.

Tickets with unrecognized issue types go into **Improvements** as a fallback.

Build each entry in the format: `[TICKET_KEY] Summary (#PR_NUMBER)` — omit the PR number if no linked PR was found.

## Step 6: Generate Release Notes

Generate structured markdown release notes. Use today's date if no release date is set on the Jira version:

```markdown
# Release v1.3.0 — 2026-03-29

## Breaking Changes
- [ENG-110] Remove deprecated cart API endpoints (#50)

## Features
- [ENG-101] Add cart drawer component (#42)
- [ENG-105] Implement wishlist functionality (#46)

## Bug Fixes
- [ENG-102] Fix null price on checkout (#43)
- [ENG-107] Resolve duplicate order creation on retry (#48)

## Improvements
- [ENG-103] Optimize collection page rendering (#44)
- [ENG-108] Consolidate logging configuration (#49)

## Contributors
- @dev1, @dev2, @dev3
```

Omit any category section that has zero entries. Build the contributors list from ticket assignees and PR authors (deduplicated).

**Show the generated release notes to the user and ask for confirmation before pushing to Confluence:**

> Here are the release notes for **v1.3.0**. Review and let me know if you'd like any changes before I publish to Confluence.

Wait for user approval. Apply any requested edits before proceeding.

## Step 7: Push to Confluence

Convert the release notes from markdown to Atlassian storage format (XHTML). Map:
- `#` headings → `<h1>`, `<h2>`, etc.
- Bullet lists → `<ul><li>...</li></ul>`
- Ticket keys → links to Jira: `<a href="$JIRA_URL/browse/ENG-101">ENG-101</a>`
- PR numbers → links to GitHub: `<a href="https://github.com/{owner}/{repo}/pull/42">#42</a>`

Create the Confluence page using the REST API v2:

```bash
curl -s -X POST \
  "$CONFLUENCE_URL/wiki/api/v2/pages" \
  -H "Content-Type: application/json" \
  -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  -d '{
    "spaceId": "<space_id>",
    "status": "current",
    "title": "Release Notes — v1.3.0",
    "body": {
      "representation": "storage",
      "value": "<h1>Release v1.3.0 — 2026-03-29</h1><h2>Features</h2><ul><li><a href=\"'"$JIRA_URL"'/browse/ENG-101\">ENG-101</a> Add cart drawer component (<a href=\"https://github.com/org/repo/pull/42\">#42</a>)</li></ul><h2>Bug Fixes</h2><ul><li><a href=\"'"$JIRA_URL"'/browse/ENG-102\">ENG-102</a> Fix null price on checkout (<a href=\"https://github.com/org/repo/pull/43\">#43</a>)</li></ul>"
    },
    "parentId": "<parent_page_id>"
  }'
```

To get the `spaceId`, fetch it from the space key:

```bash
curl -s \
  "$CONFLUENCE_URL/wiki/api/v2/spaces?keys=$CONFLUENCE_SPACE_KEY" \
  -H "Content-Type: application/json" \
  -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN"
```

If the user does not provide a parent page ID, use the space homepage as the parent. Fetch it from the space response's `homepageId` field.

**If the page already exists (409 conflict)**, fetch the existing page by title and update it:

```bash
curl -s \
  "$CONFLUENCE_URL/wiki/api/v2/pages?title=Release+Notes+—+v1.3.0&spaceKey=$CONFLUENCE_SPACE_KEY" \
  -H "Content-Type: application/json" \
  -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN"
```

Then update via PUT with the incremented version number:

```bash
curl -s -X PUT \
  "$CONFLUENCE_URL/wiki/api/v2/pages/<page_id>" \
  -H "Content-Type: application/json" \
  -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  -d '{
    "id": "<page_id>",
    "status": "current",
    "title": "Release Notes — v1.3.0",
    "body": {
      "representation": "storage",
      "value": "<updated storage format content>"
    },
    "version": {
      "number": <current_version + 1>,
      "message": "Updated release notes"
    }
  }'
```

## Step 8: Output Summary

Report the completed work:

```
## Release Notes Published

| Item | Details |
|------|---------|
| Version | v1.3.0 |
| Confluence Page | <page_url> |
| Features | <count> |
| Bug Fixes | <count> |
| Improvements | <count> |
| Breaking Changes | <count> |
| Contributors | <count> |
```

Post a comment on the Jira release version's tickets (or on a release-tracking ticket if one exists) with the Confluence link:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/3/issue/<RELEASE_TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Release notes published: <confluence_page_url>"}]}]}}'
```

If the comment API returns a 404 on `/rest/api/3/`, retry with `/rest/api/2/` using plain text body:

```bash
curl -s -X POST \
  "$JIRA_URL/rest/api/2/issue/<RELEASE_TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -d '{"body": "Release notes published: <confluence_page_url>"}'
```

For full Jira API patterns, read `../../references/jira-api.md`.
