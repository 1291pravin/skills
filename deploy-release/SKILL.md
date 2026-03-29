---
name: deploy-release
description: >
  Deploy a tested release to all Shopify stores as unpublished themes, tag the
  version in git, merge the release branch to main and dev, and transition all
  Jira tickets to Done. This is the most operationally critical skill in the
  workflow and is used by the lead to ship releases end-to-end. Use this skill
  whenever the user says "deploy release", "deploy RELEASE-123", "push release
  to production", "ship release", "deploy v1.3.0", or otherwise indicates they
  want to deploy a release to Shopify stores, even if they don't explicitly say
  "deploy-release".
---

# Deploy Release to Shopify Stores

Deploy a tested release to all Shopify stores as unpublished themes, tag the version, merge the release branch, and close out Jira. Follow each step in order.

## Step 1: Validate Environment Variables

Verify that all required environment variables are set:

| Variable | Purpose |
|----------|---------|
| `JIRA_URL` | Jira instance base URL (e.g., `https://colgate.atlassian.net`) |
| `JIRA_EMAIL` | Jira account email for API authentication |
| `JIRA_API_TOKEN` | Jira API token (generated at https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Jira project key (e.g., `RELEASE`) |
| `SHOPIFY_STORES_JSON` | JSON array of store objects (see below) |

`SHOPIFY_STORES_JSON` format:

```json
[
  {"name": "US", "url": "store-us.myshopify.com", "token": "shpat_xxx"},
  {"name": "CA", "url": "store-ca.myshopify.com", "token": "shpat_yyy"}
]
```

For any missing variable, provide the user with the export command:

```bash
export JIRA_URL="https://colgate.atlassian.net"
export JIRA_EMAIL="your-email@colgate.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="RELEASE"
export SHOPIFY_STORES_JSON='[{"name":"US","url":"store-us.myshopify.com","token":"shpat_xxx"}]'
```

Validate `SHOPIFY_STORES_JSON` is valid JSON:

```bash
echo "$SHOPIFY_STORES_JSON" | jq .
```

If `jq` reports a parse error, stop and ask the user to fix the JSON.

## Step 2: Identify Release

Parse the user input to determine the release:

- **Ticket key** (e.g., "Deploy RELEASE-123"): Fetch the ticket from Jira and extract the version from the summary or description.

  ```bash
  curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
    "$JIRA_URL/rest/api/3/issue/RELEASE-123" | jq '.fields.summary, .fields.description'
  ```

- **Version string** (e.g., "Deploy v1.3.0"): Find the release branch `release/v1.3.0`.

Verify the release branch exists locally and remotely:

```bash
git branch --list "release/v1.3.0"
git ls-remote --heads origin "release/v1.3.0"
```

If the branch does not exist, stop and tell the user.

## Step 3: Fetch Release Details

Fetch the release Jira ticket and all linked feature tickets:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/issue/RELEASE-123?fields=summary,status,issuetype,issuelinks" \
  | jq '.fields.issuelinks'
```

For each linked ticket, fetch its details:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>?fields=summary,status,issuetype"
```

Build a table of what is being deployed:

```
| Ticket | Summary | Type | Status |
|--------|---------|------|--------|
| FEAT-101 | Add wishlist feature | Story | Ready for Release |
| FEAT-102 | Update cart drawer | Task | Ready for Release |
| RELEASE-123 | Release v1.3.0 | Release | In Progress |
```

Show this table to the user before proceeding.

## Step 4: Pre-Deploy Checks

Perform all three checks before deploying:

### 1. Check for open bugs

Query Jira for bugs linked to any feature ticket where status is not Done:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/search" \
  -H "Content-Type: application/json" \
  -d '{
    "jql": "issuetype = Bug AND issue in linkedIssues(\"FEAT-101\",\"FEAT-102\") AND status != Done",
    "fields": ["summary","status","priority"]
  }' | jq '.issues[] | {key, summary: .fields.summary, status: .fields.status.name}'
```

If bugs are found, warn the user:

> **Warning:** 2 open bugs found linked to this release. Deploy anyway?

Show the bug details and wait for confirmation. Do not proceed without a "yes."

### 2. Verify release branch is up to date with dev

```bash
git fetch origin
git log origin/dev..origin/release/v1.3.0 --oneline
git log origin/release/v1.3.0..origin/dev --oneline
```

If dev has commits not in the release branch, warn the user and ask whether to continue.

### 3. Run build

```bash
git checkout release/v1.3.0
npm run build
```

If the build fails, stop and show the error output. Do not deploy a broken build.

## Step 5: Tag the Release

Create and push an annotated git tag:

```bash
git checkout release/v1.3.0
git pull origin release/v1.3.0
git tag -a v1.3.0 -m "Release v1.3.0"
git push origin v1.3.0
```

If the tag already exists, inform the user and ask whether to overwrite or skip.

## Step 6: Deploy to Shopify Stores

Iterate over every store in `SHOPIFY_STORES_JSON`. For each store, deploy the theme as **unpublished**:

```bash
shopify theme push \
  --store="$STORE_URL" \
  --password="$STORE_TOKEN" \
  --unpublished \
  --theme="Release v1.3.0" \
  --ignore=config/settings_data.json
```

**Important rules:**

- Deploy as **UNPUBLISHED**. The business publishes manually in Shopify admin.
- If a store fails, log the error and continue with the remaining stores. Do not abort all deployments because one store failed.
- After all stores have been attempted, show a deployment status table:

```
| Store | Status | Error |
|-------|--------|-------|
| US | Deployed | — |
| CA | Failed | Connection timeout |
```

If any store failed, ask the user whether to retry the failed stores.

## Step 7: Verify Deployments

For each successfully deployed store, verify the theme was created via the Shopify API:

```bash
curl -s "https://$STORE_URL/admin/api/2024-01/themes.json" \
  -H "X-Shopify-Access-Token: $STORE_TOKEN" \
  | jq '.themes[] | select(.name == "Release v1.3.0") | {id, name, role}'
```

Show a verification table with theme IDs:

```
| Store | Theme Name | Theme ID | Role |
|-------|------------|----------|------|
| US | Release v1.3.0 | 12345 | unpublished |
| CA | Release v1.3.0 | 67890 | unpublished |
```

If a theme cannot be found for a store that reported success, flag it as a discrepancy and ask the user how to proceed.

## Step 8: Merge Release Branch

### 1. Merge release to main

```bash
git checkout main && git pull origin main
git merge release/v1.3.0 --no-ff -m "chore: merge release v1.3.0 to main"
git push origin main
```

### 2. Merge main to dev (sync)

```bash
git checkout dev && git pull origin dev
git merge main --no-ff -m "chore: merge main to dev (post-release v1.3.0)"
git push origin dev
```

### 3. Handle merge conflicts

If merge conflicts occur: **STOP**. Tell the user which files conflict. Do **NOT** auto-resolve conflicts on main or dev. Ask the user to resolve manually, then confirm before continuing.

## Step 9: Update Jira

### 1. Mark the Jira version as released

Find the version ID first:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/project/$JIRA_PROJECT_KEY/versions" \
  | jq '.[] | select(.name == "v1.3.0") | .id'
```

Then mark it released:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X PUT "$JIRA_URL/rest/api/3/version/<VERSION_ID>" \
  -H "Content-Type: application/json" \
  -d '{"released": true, "releaseDate": "'$(date +%Y-%m-%d)'"}'
```

### 2. Transition release ticket to Done

Fetch available transitions and find the "Done" transition ID:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/3/issue/RELEASE-123/transitions" \
  | jq '.transitions[] | select(.name == "Done") | .id'
```

Execute the transition:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST "$JIRA_URL/rest/api/3/issue/RELEASE-123/transitions" \
  -H "Content-Type: application/json" \
  -d '{"transition": {"id": "<DONE_TRANSITION_ID>"}}'
```

### 3. Transition all feature tickets to Done

Repeat the transition call for each linked feature ticket (FEAT-101, FEAT-102, etc.).

### 4. Add comment to release ticket

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST "$JIRA_URL/rest/api/3/issue/RELEASE-123/comment" \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Deployed to all stores. Theme name: Release v1.3.0. Business can publish in Shopify admin."}]}]
    }
  }'
```

### 5. Add comment to each feature ticket

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST "$JIRA_URL/rest/api/3/issue/<TICKET_KEY>/comment" \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Deployed in Release v1.3.0"}]}]
    }
  }'
```

## Step 10: Output Deployment Summary

Display the final summary:

```
## Deployment Complete

| Store | Status | Theme Name | Theme ID |
|-------|--------|------------|----------|
| US | Deployed | Release v1.3.0 | 12345 |
| CA | Deployed | Release v1.3.0 | 67890 |

| Item | Details |
|------|---------|
| Version | v1.3.0 |
| Tag | v1.3.0 |
| Main merge | Done |
| Dev sync | Done |
| Jira tickets | All transitioned to Done |
| Next step | Business publishes theme in Shopify admin |
```

If any stores failed or any Jira transitions failed, list them clearly in the summary so the user knows what needs manual follow-up.

## References

- For Jira API patterns, read `../../references/jira-api.md`
- For Shopify API patterns, read `../../references/shopify-api.md`
- For branch conventions, read `../../references/git-conventions.md`
