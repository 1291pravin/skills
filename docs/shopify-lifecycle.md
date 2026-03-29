# Shopify Theme Development Lifecycle — Full Guide

Complete onboarding guide for the AI-powered Shopify theme development workflow at Colgate. This document covers the end-to-end flow from "Work on ticket" to "Deploy release", including all skills, GitHub Actions, and manual steps.

---

## Architecture Overview

Three layers work together:

| Layer | What | Who triggers |
|-------|------|-------------|
| **Skills** (AI in Windsurf) | Developer/Lead talks to AI, AI does the work | Human command in IDE |
| **GitHub Actions** | Automated on git events (PRs, pushes, tags) | Git events |
| **Manual** | Human decisions, testing, and sign-offs | QA / Business / Lead |

```
Skills:          work-on-ticket → create-release → deploy-release → release-notes
                 hotfix (when needed)

GitHub Actions:  branch-check → pr-preview → pr-cleanup
                 release-preview (deploys + cleans up old themes)

Manual:          Test features → Sign off → Smoke test release → Sign off → Publish theme
```

---

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: DEVELOPMENT                                       │
│                                                             │
│  Developer: "Work on ticket ABC-123"                        │
│      │                                                      │
│      ▼                                                      │
│  [Skill: work-on-ticket]                                    │
│    → Fetch Jira details                                     │
│    → (Optional) Fetch Figma design via MCP                  │
│    → (Optional) Fetch Shopify docs via MCP                  │
│    → Create feature/ABC-123-* branch from dev               │
│    → Write code, build, test                                │
│    → Create PR targeting dev                                │
│    → Update Jira: "In Review" + PR link                     │
│      │                                                      │
│      ▼                                                      │
│  [GitHub Action: branch-check]                              │
│    → Verify branch name contains ticket ID                  │
│      │                                                      │
│      ▼                                                      │
│  [GitHub Action: pr-preview]                                │
│    → Create preview themes on all Shopify stores            │
│    → Post preview links on PR + Jira                        │
│      │                                                      │
│      ▼                                                      │
│  [Manual] QA / Merchant tests on preview theme              │
│    → Approves PR                                            │
│      │                                                      │
│      ▼                                                      │
│  PR merged to dev                                           │
│      │                                                      │
│      ▼                                                      │
│  [GitHub Action: pr-cleanup]                                │
│    → Delete preview themes from all stores                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  PHASE 2: RELEASE PLANNING                                  │
│                                                             │
│  Lead: "Create release with ABC-101, ABC-102 minor"         │
│      │                                                      │
│      ▼                                                      │
│  [Skill: create-release]                                    │
│    → Determine version: v1.2.0 → v1.3.0                    │
│    → Verify all tickets merged to dev                       │
│    → Create Jira version + release ticket                   │
│    → Link all feature tickets                               │
│    → Cut release/v1.3.0 branch from dev                     │
│    → Bump version, push                                     │
│      │                                                      │
│      ▼                                                      │
│  [GitHub Action: release-preview]                           │
│    → Deploy "Release v1.3.0" theme to all stores            │
│    → Clean up old release themes (keep published + 1        │
│      rollback)                                              │
│      │                                                      │
│      ▼                                                      │
│  [Manual] Business smoke tests on release theme             │
│    → Bugs logged as subtasks on release ticket              │
│    → Fixes pushed to release branch (action re-deploys)     │
│    → All clear → sign-off                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  PHASE 3: FINALIZE RELEASE                                  │
│                                                             │
│  Lead: "Deploy RELEASE-123"                                 │
│      │                                                      │
│      ▼                                                      │
│  [Skill: deploy-release]                                    │
│    → Check for open bugs (warn if found)                    │
│    → Tag v1.3.0                                             │
│    → Merge release/v1.3.0 → main → dev                     │
│    → Update Jira: release + feature tickets → Done          │
│      │                                                      │
│      ▼                                                      │
│  [Skill: release-notes]                                     │
│    → Generate structured release notes                      │
│    → Push to Confluence                                     │
│      │                                                      │
│      ▼                                                      │
│  [Manual] Business publishes "Release v1.3.0" theme         │
│    in Shopify admin                                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  HOTFIX (when needed)                                       │
│                                                             │
│  Developer/Lead: "Hotfix ABC-999"                           │
│      │                                                      │
│      ▼                                                      │
│  [Skill: hotfix]                                            │
│    → Branch from main                                       │
│    → Fix, test, PR to main                                  │
│    → Sync PR to dev                                         │
│    → Update Jira                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Setup

### Required for all skills (Jira)

```bash
export JIRA_URL=https://company.atlassian.net
export JIRA_EMAIL=your-email@company.com
export JIRA_API_TOKEN=your-jira-api-token
export JIRA_PROJECT_KEY=ENG
```

Get your Jira API token: https://id.atlassian.com/manage-profile/security/api-tokens

### Required for GitHub Actions (Shopify)

```bash
export SHOPIFY_STORES_JSON='[
  {"name":"US","url":"store-us.myshopify.com","token":"shpat_xxx"},
  {"name":"CA","url":"store-ca.myshopify.com","token":"shpat_yyy"}
]'
```

Get Shopify access tokens: Store admin → Apps → Develop apps → Create/configure app with `write_themes` scope.

### Required for release-notes (Confluence)

```bash
export CONFLUENCE_URL=https://company.atlassian.net
export CONFLUENCE_SPACE_KEY=DEV
export CONFLUENCE_EMAIL=your-email@company.com
export CONFLUENCE_TOKEN=your-confluence-api-token
```

### Optional: MCP Servers (for work-on-ticket)

Configure in your Claude Code MCP settings for automatic Figma design fetching and Shopify documentation lookup. See `work-on-ticket/references/mcp-setup.md` for setup instructions.

---

## Skills Reference

### For Developers

| Skill | Command | What it does |
|-------|---------|-------------|
| `work-on-ticket` | "Work on ticket ABC-123" | Fetches Jira, creates branch, writes code, creates PR, updates Jira |
| `hotfix` | "Hotfix ABC-999" | Creates hotfix from main, fixes, PRs to main + dev |

### For Leads

| Skill | Command | What it does |
|-------|---------|-------------|
| `create-release` | "Create release with ABC-101, ABC-102 minor" | Verifies tickets, creates Jira version, cuts release branch |
| `deploy-release` | "Deploy RELEASE-123" | Tags release, merges branches, updates Jira (theme already on stores) |
| `release-notes` | "Generate release notes for v1.3.0" | Creates structured notes, pushes to Confluence |

---

## GitHub Actions Installation

### Quick setup

Copy all workflows to your theme repo:

```bash
mkdir -p .github/workflows
cp skills/github-actions/branch-check/workflow.yml .github/workflows/branch-check.yml
cp skills/github-actions/pr-preview/workflow.yml .github/workflows/pr-preview.yml
cp skills/github-actions/pr-cleanup/workflow.yml .github/workflows/pr-cleanup.yml
cp skills/github-actions/release-preview/workflow.yml .github/workflows/release-preview.yml
```

### Required secrets

Add these in your theme repo: Settings → Secrets → Actions.

| Secret | Required by |
|--------|-------------|
| `SHOPIFY_STORES_JSON` | pr-preview, pr-cleanup, release-preview |
| `JIRA_URL` | pr-preview (optional) |
| `JIRA_EMAIL` | pr-preview (optional) |
| `JIRA_API_TOKEN` | pr-preview (optional) |

See `github-actions/README.md` for full details.

---

## Branch Strategy

```
main          ←── production-ready, tagged releases
  ↑
  │ merge (release branch after deploy)
  │
release/v1.3.0  ←── cut from dev, tested, deployed, then merged to main
  ↑
  │ cut from dev
  │
dev           ←── integration branch, all feature PRs merge here
  ↑
  │ merge (feature PRs)
  │
feature/ENG-123-*  ←── individual ticket branches
```

**Hotfixes:** branch from `main`, merge to `main` + cherry-pick to `dev`.

---

## How Release Themes Work

The `release-preview` GitHub Action handles Shopify theme lifecycle automatically:

1. **Deploy**: When code is pushed to `release/*`, the action creates/updates an unpublished theme named `Release v1.3.0` on all stores
2. **Update**: Subsequent pushes to the release branch update the same theme (bug fixes during smoke testing)
3. **Cleanup**: Each time a new release theme is created, old release themes are cleaned up — keeping the currently published theme and one rollback
4. **Publish**: The business publishes the theme manually in Shopify admin when ready

There is no separate "deploy to Shopify" step. The theme that the business tested is the same theme they publish.

---

## Manual Steps Checklist

These are human decisions that remain in the workflow:

| Step | Who | When |
|------|-----|------|
| Review PR code | Developer / Lead | After PR is created |
| Test on preview theme | QA / Merchant | After pr-preview creates themes |
| Approve and merge PR | Lead | After review + QA pass |
| Plan which tickets go into a release | Lead | When features are ready |
| Smoke test release theme | Business / QA | After create-release triggers release-preview |
| Log bugs on release ticket | QA | During smoke testing |
| Sign off on release | Business | After smoke test passes |
| Trigger deploy-release | Lead | After sign-off (tags, merges, closes Jira) |
| Publish theme in Shopify admin | Business | After deploy-release completes |

---

## Shared References

These files contain common API patterns used across multiple skills:

| File | Contents |
|------|----------|
| `references/jira-api.md` | Jira REST API patterns (search, create, comment, transition, versions) |
| `references/shopify-api.md` | Shopify Admin API + CLI patterns (themes, multi-store iteration) |
| `references/git-conventions.md` | Branch naming, commit format, PR templates |

---

## Troubleshooting

### "Jira API returns 404"
The skill tried v3 API but your instance uses v2 (Jira Server/Data Center). The skills automatically fall back to v2.

### "SHOPIFY_STORES_JSON is not valid JSON"
Ensure the JSON is properly escaped in your shell. Use single quotes around the value. Validate with: `echo "$SHOPIFY_STORES_JSON" | jq .`

### "gh CLI not found"
Install GitHub CLI: https://cli.github.com/ — required for PR creation in skills.

### "MCP server not available"
MCP servers are optional. Skills degrade gracefully without them. See `work-on-ticket/references/mcp-setup.md` for setup.

### "Merge conflict during deploy"
The deploy-release skill stops and asks you to resolve manually. Never auto-resolves conflicts on main or dev.

### "Preview theme not created"
Check that `SHOPIFY_STORES_JSON` has the correct store URL (must be `store.myshopify.com` format) and that the access token has `write_themes` scope.
