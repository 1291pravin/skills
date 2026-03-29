# Suggested Skills for AI OS

Organized by dev lifecycle stage.

## Code Quality & Security
- **eslint-fix** — Auto-fix ESLint violations across the Shopify theme (Liquid/JS/TS)
- **dependency-audit** — Scan and fix vulnerable dependencies (npm audit / Snyk integration)

## Jira & Project Management
- **jira-triage** — Auto-triage new Jira tickets (assign priority, labels, components based on content)
- **jira-update** — Update Jira ticket status/comments from code changes (link PRs, move to "In Review" on PR creation)
- **jira-create** — Create Jira tickets from error logs, SonarQube findings, or Apiiro alerts

## Shopify Theme Development
- **shopify-theme-check** — Run and auto-fix Shopify Theme Check linting violations
- **liquid-refactor** — Refactor Liquid templates (extract snippets, optimize renders)
- **shopify-deploy** — Automate theme deployment to dev/staging/production environments
- **shopify-perf** — Lighthouse/Core Web Vitals audit with auto-fix suggestions for theme performance

## CI/CD & DevOps
- **pr-review** — Auto-review PRs against team standards (Shopify best practices, accessibility, security)
- **pr-create** — Create well-formatted PRs with Jira linking, test plans, and changelog entries
- **release-notes** — Generate release notes from merged PRs and Jira tickets

## Testing
- **test-gen** — Generate unit/integration tests for Shopify theme JS and Liquid sections
- **visual-regression** — Screenshot comparison for theme changes across breakpoints

## Documentation & Onboarding
- **doc-gen** — Auto-generate docs from code (component catalog, section schemas, settings)
- **onboard-dev** — Interactive skill that walks new devs through the codebase and tooling setup

## Monitoring & Observability
- **incident-triage** — Pull error logs/alerts and create categorized Jira tickets
- **health-check** — Scheduled skill to verify theme health (broken links, missing assets, API status)

## Priority
Start with **jira-triage**, **shopify-theme-check**, **pr-review**, and **shopify-deploy** — they cover the highest-friction points in a Shopify team's daily workflow.
