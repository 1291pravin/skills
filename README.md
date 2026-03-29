# Skills

Distributable AI agent skills for security remediation and developer workflows.

## Installation

```bash
npx skills add 1291pravin/skills
```

Or install a specific skill:

```bash
npx skills add 1291pravin/skills --skill apiiro-fix
```

Works with **Claude Code, Windsurf, Cursor, Codex, Copilot**, and [40+ other AI agents](https://github.com/vercel-labs/skills).

## Available Skills

### apiiro-fix

Automated Apiiro security remediation. Fetches all security findings for your repo and fixes them end-to-end.

**What it does:**

1. Installs Apiiro CLI if missing (Homebrew on Mac/Linux, binary on Windows)
2. Authenticates with Apiiro (OAuth via browser)
3. Detects your package manager (npm, yarn v1/v4, pnpm, bun)
4. Identifies the current repo from git remote
5. Fetches all Apiiro findings scoped to your repo
6. Remediates:
   - **SCA** — Updates vulnerable packages, handles breaking changes
   - **SAST** — Fixes code vulnerabilities (OWASP Top 10)
   - **Secrets** — Removes hardcoded secrets, warns to rotate credentials
   - **Misconfigurations** — Fixes insecure defaults and missing security headers
   - **PII/PHI/PCI** — Addresses personal data exposure
   - **Supply Chain** — Flags issues requiring manual action
7. Builds and tests the project
8. Creates a PR with a full remediation summary

**Usage:**

Run `/apiiro-fix` in your AI coding agent, or just ask:

> "Fix all Apiiro security findings in this repo"

### sonarqube-fix

Automated SonarQube issue remediation. Fetches issues from a self-hosted SonarQube instance and fixes them in severity order — 20 per run, one focused PR per chunk.

**What it does:**

1. Installs sonar-scanner CLI if missing (Homebrew on Mac/Linux, manual on Windows)
2. Connects to your self-hosted SonarQube (`SONAR_HOST_URL` + `SONAR_TOKEN`)
3. Detects the project key from `sonar-project.properties` or git remote
4. Takes a baseline test snapshot before touching any code
5. Fetches all open issues: Bugs, Vulnerabilities, Security Hotspots, Code Smells
6. Prioritizes by severity: BLOCKER → CRITICAL → MAJOR → MINOR → INFO
7. Remediates:
   - **Bugs** — Null dereferences, off-by-one errors, resource leaks, wrong conditions
   - **Vulnerabilities** — SQL injection, XSS, path traversal, command injection, hardcoded secrets
   - **Security Hotspots** — Weak crypto, insecure random, open redirect, SSRF
   - **Code Smells** — Dead code, high complexity, naming issues (MAJOR+ only)
8. Fixes up to 20 issues per run (keeps PRs focused and reviewable)
9. Builds and tests, comparing against baseline to avoid attributing pre-existing failures
10. Creates one PR per chunk with a summary table and manual action checklist
11. Reports remaining issue count and prompts you to run again

**Usage:**

Run `/sonarqube-fix` in your AI coding agent, or just ask:

> "Fix all SonarQube issues in this repo"

### triage-errors

Automated error triage across GCP Cloud Logging and Sentry. Fetches errors from the last 24 hours, deduplicates across sources, and creates Jira tickets for untracked issues.

**What it does:**

1. Validates environment variables (`GCLOUD_PROJECT_ID`, `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, `JIRA_URL`, etc.)
2. Checks CLI availability (gcloud, sentry-cli, acli) — falls back to API when CLIs are missing
3. Fetches GCP Cloud Logging errors (severity >= ERROR, last 24h)
4. Fetches unresolved Sentry issues (last 24h) with full stacktraces
5. Deduplicates errors across sources (groups GCP logs, cross-matches with Sentry issues)
6. Checks existing Jira tickets to avoid creating duplicates
7. Creates Jira tickets for new errors with full context (stacktrace, frequency, Sentry link, GCP log filter)
8. Outputs a summary table of new and existing tickets

**Setup:**

```bash
export GCLOUD_PROJECT_ID=my-project
export SENTRY_URL=https://sentry.company.com
export SENTRY_ORG=my-org
export SENTRY_PROJECT=my-project
export SENTRY_AUTH_TOKEN=your-token
export JIRA_URL=https://company.atlassian.net
export JIRA_PROJECT_KEY=ENG
```

**Usage:**

Run `/triage-errors` in your AI coding agent, or just ask:

> "Check for new errors in the last 24 hours"

### fix-errors

Automated error resolution from Jira ticket to PR. Picks up tickets created by `/triage-errors`, pulls full error context from Sentry and GCP, finds the relevant code, applies a fix, and creates a PR.

**What it does:**

1. Validates environment variables (same as triage-errors)
2. Fetches open Jira tickets labeled `auto-triage` (created by `/triage-errors`)
3. Lets you pick which ticket to work on
4. Extracts error context from the ticket (Sentry URL, stacktrace, error signature)
5. Fetches full error details from Sentry (stacktrace, tags, breadcrumbs) and GCP logs
6. Analyzes root cause — identifies affected files, functions, and error type
7. Finds the relevant code in the current repository
8. Proposes a fix with diff preview and risk assessment — waits for your confirmation
9. Applies the fix, runs build and tests (with baseline comparison)
10. Creates a PR referencing the Jira ticket
11. Updates the Jira ticket with the PR link and transitions status

**Setup:**

Same environment variables as `triage-errors` (see above). Also requires `gh` CLI for PR creation.

**Usage:**

Run `/fix-errors` in your AI coding agent, or just ask:

> "Fix the error tickets from triage"

### package-version-update

Automated dependency updates with a tiered approach. Scans all project dependencies, categorizes updates by risk level, and applies them with build/test verification at each stage.

**What it does:**

1. Detects your package manager (npm, yarn v1/v4, pnpm, bun)
2. Takes a baseline test snapshot before touching any code
3. Scans all dependencies and devDependencies for available updates
4. Categorizes into three tiers:
   - **Tier 1: EOL/Deprecated** — Auto-updates packages that are deprecated or target EOL runtimes
   - **Tier 2: Patch/Minor** — Auto-applies semver-safe updates (no breaking changes)
   - **Tier 3: Major** — Fetches changelogs from npm registry and GitHub, analyzes breaking changes against your codebase, presents a migration plan for your approval (max 5 per run)
5. Builds and tests after Tier 1+2, and after each Tier 3 update
6. Reverts any update that causes test failures (added to "deferred" list)
7. Creates a PR with a comprehensive summary table, migration details, and manual action items

**Usage:**

Run `/package-version-update` in your AI coding agent, or just ask:

> "Update all dependencies in this repo"

### work-on-ticket

End-to-end Jira ticket workflow. Fetches ticket details, optionally pulls Figma designs and Shopify docs via MCP, creates a feature branch, implements the changes, creates a PR, and updates Jira.

**What it does:**

1. Fetches full Jira ticket details (summary, description, acceptance criteria)
2. (Optional) Fetches Figma design specs via MCP server
3. (Optional) Fetches relevant Shopify documentation via MCP server
4. Creates `feature/<TICKET_KEY>-<slug>` branch from dev
5. Implements the changes based on ticket requirements
6. Builds and tests (including Shopify theme check)
7. Creates a PR targeting dev with structured body
8. Updates Jira ticket: adds PR link, transitions to "In Review"

**Usage:**

Run `/work-on-ticket` in your AI coding agent, or just ask:

> "Work on ticket ENG-123"

### create-release

Release planning and branch creation. Takes a list of tickets and version bump type, verifies all are merged, creates Jira release artifacts, and cuts the release branch.

**What it does:**

1. Parses ticket list and version bump type (major/minor/patch)
2. Determines new version via semver bump
3. Verifies all listed tickets are merged to dev
4. Creates Jira version and release ticket, links all feature tickets
5. Cuts `release/<version>` branch from dev
6. Bumps version in package.json and pushes

**Usage:**

Run `/create-release` in your AI coding agent, or just ask:

> "Create release with ENG-101, ENG-102, ENG-103 as minor"

### deploy-release

Deploys a tested release to all Shopify stores. Tags the version, deploys as unpublished themes, merges branches, and updates all Jira tickets.

**What it does:**

1. Validates release ticket and checks for open bugs
2. Tags the release version
3. Deploys to all Shopify stores as unpublished themes
4. Merges release branch to main, then main to dev
5. Marks Jira version as released, transitions all tickets to Done
6. Outputs deployment summary table

**Usage:**

Run `/deploy-release` in your AI coding agent, or just ask:

> "Deploy RELEASE-123"

### release-notes

Generates structured release notes from Jira tickets and PR descriptions, then pushes to Confluence.

**What it does:**

1. Fetches all tickets in a Jira release version
2. Enriches with PR descriptions from GitHub
3. Categorizes into Features, Bug Fixes, Improvements, Breaking Changes
4. Generates formatted markdown release notes
5. Creates a Confluence page with the release notes
6. Comments on the Jira release ticket with the Confluence link

**Usage:**

Run `/release-notes` in your AI coding agent, or just ask:

> "Generate release notes for v1.3.0"

### hotfix

Emergency hotfix workflow. Branches from main, applies the fix, creates PRs to both main and dev.

**What it does:**

1. Fetches Jira ticket details
2. Creates `hotfix/<TICKET_KEY>-<slug>` branch from main
3. Implements the fix with minimal changes
4. Builds and tests with baseline comparison
5. Creates PR targeting main
6. Creates sync PR to dev (cherry-pick or merge)
7. Updates Jira with both PR links

**Usage:**

Run `/hotfix` in your AI coding agent, or just ask:

> "Hotfix ENG-999"

---

## GitHub Actions

Ready-to-use workflow templates for Shopify theme preview automation. Copy to your theme repo's `.github/workflows/` directory.

| Action | Trigger | Purpose |
|--------|---------|---------|
| **branch-check** | PR opened → dev | Block PRs without Jira ticket ID in branch name |
| **pr-preview** | PR opened → dev | Create preview themes on all Shopify stores |
| **pr-cleanup** | PR closed → dev | Delete preview themes |
| **release-preview** | Push to release/* | Create release preview themes |
| **release-cleanup** | Tag push or manual | Delete release preview themes |

See `github-actions/README.md` for installation instructions and required secrets.

---

## Full Lifecycle Guide

For a complete walkthrough of the end-to-end development workflow — from ticket to production — see **[docs/shopify-lifecycle.md](./docs/shopify-lifecycle.md)**.

---

## Adding New Skills

Each skill is a folder with a `SKILL.md` file:

```
skill-name/
└── SKILL.md
```

See the [Vercel Skills docs](https://vercel.com/docs/agent-resources/skills) for the full authoring guide.

## License

MIT
