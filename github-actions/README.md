# GitHub Actions — Shopify Theme Lifecycle

Ready-to-use GitHub Actions workflows for automating Shopify theme previews and branch validation. These are **templates** — copy them into your theme repo's `.github/workflows/` directory.

## Actions Overview

| Action | Trigger | Purpose |
|--------|---------|---------|
| [branch-check](./branch-check/) | PR opened/updated → dev | Block PRs without Jira ticket ID in branch name |
| [pr-preview](./pr-preview/) | PR opened/updated → dev | Create preview themes on all Shopify stores |
| [pr-cleanup](./pr-cleanup/) | PR closed/merged → dev | Delete preview themes from all stores |
| [release-preview](./release-preview/) | Push to `release/*` | Deploy release themes to all stores + clean up old ones |

## Installation

### Step 1: Copy workflows to your theme repo

```bash
# From your theme repo root
mkdir -p .github/workflows

# Copy the workflows you need
cp path/to/skills/github-actions/branch-check/workflow.yml .github/workflows/branch-check.yml
cp path/to/skills/github-actions/pr-preview/workflow.yml .github/workflows/pr-preview.yml
cp path/to/skills/github-actions/pr-cleanup/workflow.yml .github/workflows/pr-cleanup.yml
cp path/to/skills/github-actions/release-preview/workflow.yml .github/workflows/release-preview.yml
```

### Step 2: Configure secrets

Go to your theme repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Required by | Format |
|--------|-------------|--------|
| `SHOPIFY_STORES_JSON` | pr-preview, pr-cleanup, release-preview | JSON array (see below) |
| `JIRA_URL` | pr-preview (optional) | `https://company.atlassian.net` |
| `JIRA_EMAIL` | pr-preview (optional) | `dev@company.com` |
| `JIRA_API_TOKEN` | pr-preview (optional) | Jira API token |

### SHOPIFY_STORES_JSON format

```json
[
  {
    "name": "US",
    "url": "store-us.myshopify.com",
    "token": "shpat_xxxxxxxxxxxxxxxx"
  },
  {
    "name": "CA",
    "url": "store-ca.myshopify.com",
    "token": "shpat_yyyyyyyyyyyyyyyy"
  }
]
```

### Step 3: Verify

1. Create a feature branch with a ticket ID (e.g., `feature/ENG-123-test`)
2. Open a PR to `dev`
3. Check the Actions tab — branch-check and pr-preview should run
4. Merge or close the PR — pr-cleanup should run

## Theme Naming Conventions

| Context | Theme Name | Created by | Cleaned up by |
|---------|------------|------------|---------------|
| PR preview | `preview-pr-{NUMBER}` | pr-preview | pr-cleanup |
| Release theme | `Release {VERSION}` | release-preview | release-preview (auto-cleans old themes) |

## Customization

- **Change target branch**: Edit `branches: [dev]` in the workflow files
- **Add stores**: Update `SHOPIFY_STORES_JSON` secret
- **Skip Jira updates**: Leave Jira secrets unconfigured — pr-preview will skip gracefully
- **Ignore files**: Add patterns to `--ignore` flag in Shopify CLI commands (default: `config/settings_data.json`)
