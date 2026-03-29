# Release Preview Themes

Creates release preview themes on all Shopify stores when code is pushed to a release branch.

## Trigger
- Push to any `release/**` branch

## What it does
- Extracts version from branch name (e.g., `release/v1.3.0` -> `v1.3.0`)
- For each store: creates or updates an unpublished theme named `release-preview-{version}`
- Subsequent pushes to the release branch update the existing preview themes

## Required Secrets
| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | JSON array of store configs |

## Setup
1. Copy `workflow.yml` to `.github/workflows/release-preview.yml` in your theme repo
2. `SHOPIFY_STORES_JSON` secret should already be configured
