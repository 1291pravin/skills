# Release Preview Cleanup

Deletes release preview themes from all Shopify stores after deployment.

## Trigger
- **Tag push**: Automatically triggered when a version tag (e.g., `v1.3.0`) is pushed
- **Manual dispatch**: Can be triggered manually with a version input

## What it does
- Finds and deletes themes named `release-preview-{version}` from all stores
- Logs success/failure per store

## Required Secrets
| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | Same JSON array as other actions |

## Setup
1. Copy `workflow.yml` to `.github/workflows/release-cleanup.yml` in your theme repo
2. `SHOPIFY_STORES_JSON` secret should already be configured

## Manual Trigger
Go to Actions tab → "Release Preview Cleanup" → "Run workflow" → enter version (e.g., `v1.3.0`)
