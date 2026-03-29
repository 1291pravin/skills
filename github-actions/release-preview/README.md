# Release Preview Themes

Creates release themes on all Shopify stores when code is pushed to a release branch, and cleans up old release themes automatically.

## Trigger
- Push to any `release/**` branch

## What it does
- Extracts version from branch name (e.g., `release/v1.3.0` -> `v1.3.0`)
- For each store: creates or updates an unpublished theme named `Release {version}`
- Subsequent pushes to the release branch update the existing theme
- Cleans up old release themes: keeps the published (live) theme + 1 rollback, deletes the rest

## Theme lifecycle
1. `create-release` cuts a `release/v1.3.0` branch → this action deploys `Release v1.3.0` theme
2. Bug fixes pushed to the release branch → this action updates the same theme
3. Business smoke tests and publishes the theme in Shopify admin
4. Next release creates a new theme → this action cleans up old ones

## Required Secrets
| Secret | Purpose |
|--------|---------|
| `SHOPIFY_STORES_JSON` | JSON array of store configs |

## Setup
1. Copy `workflow.yml` to `.github/workflows/release-preview.yml` in your theme repo
2. `SHOPIFY_STORES_JSON` secret should already be configured
