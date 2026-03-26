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

## Adding New Skills

Each skill is a folder with a `SKILL.md` file:

```
skill-name/
└── SKILL.md
```

See the [Vercel Skills docs](https://vercel.com/docs/agent-resources/skills) for the full authoring guide.

## License

MIT
