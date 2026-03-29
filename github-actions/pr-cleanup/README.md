# PR Preview Cleanup

Deletes preview themes from all Shopify stores when a PR is closed or merged.

## Trigger
- Pull request closed (merged or not) targeting `dev`

## What it does
- For each store in `SHOPIFY_STORES_JSON`: finds and deletes the theme named `preview-pr-{PR_NUMBER}`
- Logs success/failure per store

## Required Secrets
| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | Same JSON array as pr-preview |

## Setup
1. Copy `workflow.yml` to `.github/workflows/pr-cleanup.yml` in your theme repo
2. `SHOPIFY_STORES_JSON` secret should already be configured from pr-preview setup
