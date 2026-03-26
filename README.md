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

## Adding New Skills

Each skill is a folder with a `SKILL.md` file:

```
skill-name/
└── SKILL.md
```

See the [Vercel Skills docs](https://vercel.com/docs/agent-resources/skills) for the full authoring guide.

## License

MIT
