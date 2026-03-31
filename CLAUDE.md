# Skills Project — AI Operating System for Developers

## Overview
This is a collection of Claude Code skills designed to build an **AI Operating System** for developers at **Colgate**. The goal is to automate repetitive workflows so developers can work faster and focus on high-value tasks.

## Context
- **Company**: Colgate
- **IDE**: Windsurf
- **Platform**: Shopify ecommerce theme development
- **Tooling**: Jira, Apiiro, SonarQube, AQA/UsableNet (accessibility), and more
- **Purpose**: Create reusable, composable skills that other developers can plug into their Claude Code workflow — forming an automation layer ("AI OS") across the dev lifecycle

## Architecture: Jira-Centric Workflow

All code quality/security/error fixes flow through Jira as the single source of truth:

```
Triage (scan + create tickets) → Work (fix locally) → Ship (PR + Jira update)
```

1. **Triage skills** scan external tools and create Jira tickets with structured data
2. **work-on-ticket** detects ticket type via labels and loads the right fix strategy
3. **ship-ticket** commits, creates PR, pushes, and updates Jira

Label-based routing in work-on-ticket:
| Label | Fix Strategy | Branch Prefix |
|-------|-------------|---------------|
| `apiiro` | Security remediation | `fix/apiiro-<KEY>` |
| `aqa` | Accessibility fixes | `fix/aqa-<KEY>` |
| `sonarqube` | Code quality fixes | `fix/sonarqube-<KEY>` |
| `errors` / `auto-triage` | Error fixes | `fix/error-<KEY>` |
| *(none)* | Feature implementation | `feature/<KEY>-<slug>` |

## Skills

### Triage (Scan & Create Jira Tickets)
- **triage-apiiro** — Scan Apiiro for security findings, create Jira tickets (label: `apiiro`)
- **triage-aqa** — Run AQA accessibility scan, create Jira tickets (label: `aqa`)
- **triage-sonarqube** — Fetch SonarQube issues, create Jira tickets (label: `sonarqube`)
- **triage-errors** — Fetch GCP/Sentry errors, create Jira tickets (label: `errors`)

### Core Workflow
- **work-on-ticket** — Detect ticket type via labels, load fix strategy, implement locally (no PR/push)
- **ship-ticket** — Commit, create PR, push to GitHub, update Jira to "In Review"

### Platform & API Management
- **aqa-usablenet** — Full AQA API integration: suites, flows, crawlers, tests, scheduling, evaluate HTML
- **package-version-update** — Update package versions across the project

### Release Management
- **create-release** — Plan releases: verify tickets merged, create Jira version, cut release branch
- **deploy-release** — Finalize release: tag, merge branches, update Jira (theme already on stores via release-preview action)
- **release-notes** — Generate structured release notes and push to Confluence
- **hotfix** — Hotfix from main with sync back to dev

### Deprecated (use triage → work-on-ticket → ship-ticket instead)
- **apiiro-fix** — *(deprecated)* Standalone scan+fix+PR for Apiiro
- **sonarqube-fix** — *(deprecated)* Standalone scan+fix+PR for SonarQube
- **fix-errors** — *(deprecated)* Standalone error fix+PR

### GitHub Actions (templates for theme repos)
- **branch-check** — Block PRs without Jira ticket ID in branch name
- **pr-preview** — Create Shopify preview themes on PR open
- **pr-cleanup** — Delete preview themes on PR close
- **release-preview** — Deploy release themes on push to release/*, clean up old themes automatically

See `docs/shopify-lifecycle.md` for the full end-to-end workflow guide.

## Conventions
- Each skill lives in its own directory with a `SKILL.md`
- Skills should use REST APIs directly (not CLIs) when possible
- Skills should be idempotent and safe to re-run
- Keep skills focused on a single responsibility
- Never use Claude username in git commits
