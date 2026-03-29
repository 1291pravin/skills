# PR Preview Themes

Creates preview themes on all Shopify stores when a PR is opened or updated.

## Trigger
- Pull request opened or synchronized targeting `dev`

## What it does
1. For each store in `SHOPIFY_STORES_JSON`: creates (or updates) an unpublished theme named `preview-pr-{PR_NUMBER}`
2. Comments on the PR with preview information
3. Posts a comment on the linked Jira ticket (extracted from branch name)

## Required Secrets
| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | JSON array: `[{"name":"US","url":"store.myshopify.com","token":"shpat_xxx"}]` |
| `JIRA_URL` | Jira instance URL (optional — skips Jira update if missing) |
| `JIRA_EMAIL` | Jira auth email (optional) |
| `JIRA_API_TOKEN` | Jira API token (optional) |

## Setup
1. Copy `workflow.yml` to `.github/workflows/pr-preview.yml` in your theme repo
2. Add `SHOPIFY_STORES_JSON` to repo secrets
3. Optionally add Jira secrets for automatic ticket updates
