# Fix Strategy: Apiiro Security Findings

This strategy is loaded by `/work-on-ticket` when the ticket has the `apiiro` label. It contains the remediation logic for Apiiro security findings.

## Prerequisites

The Apiiro CLI must be installed and authenticated (for verifying fixes). The ticket description contains a JSON block with the finding details.

## Parse Ticket Description

Extract the finding list from the ticket description. Look for the `{code:json}` block containing an array of findings. Each finding has:

- `id` — Apiiro finding ID
- `category` — SCA, SAST, Secrets, Misconfigurations, PII, Supply Chain
- `severity` — CRITICAL, HIGH, MEDIUM, LOW
- `filePath` — file where the issue was found
- `lineNumber` — line number (for SAST findings)
- For SCA: `package`, `currentVersion`, `safeVersion`, `cve`
- For SAST: `type` (e.g., SQL Injection, XSS), `description`

If the structured data cannot be parsed (e.g., ticket was manually edited), fall back to re-scanning:
```bash
apiiro risks --repo <repo-identifier> --output json
```

## Detect Package Manager

Refer to `../../references/package-manager-detection.md` for detection logic.

## Baseline Test Snapshot

**Run this BEFORE making any code changes.**

1. Run the test command for the detected package manager and capture full output
2. Record every failing test by name/path → store as the **baseline failures list**
3. If the build itself fails before tests can run → record the build error as a baseline failure too
4. Inform the user:
   > Baseline captured: **B** tests already failing before any changes. These will not be attributed to this run.

## Remediate — Package Vulnerabilities (SCA)

For each SCA finding in the ticket:

1. Note the current installed version and the recommended safe version
2. Update the package using the detected package manager:
   - npm: `npm install <pkg>@<ver>`
   - yarn v1: `yarn upgrade <pkg>@<ver>`
   - yarn v4: `yarn up <pkg>@<ver>`
   - pnpm: `pnpm update <pkg>`
   - bun: `bun add <pkg>@<ver>`
3. If the update requires a **major version bump**:
   - Look up the package's changelog or migration guide
   - Identify breaking changes that affect this project
   - Update code to accommodate the breaking changes
4. After updating, verify the lock file was regenerated correctly

## Remediate — Code Vulnerabilities (SAST)

For each SAST finding in the ticket:

1. Read the flagged file at the line number specified
2. Identify the vulnerability type and apply the appropriate fix:
   - **XSS**: Sanitize/escape user input before rendering
   - **SQL Injection**: Use parameterized queries or prepared statements
   - **Path Traversal**: Validate and sanitize file paths, use allowlists
   - **Command Injection**: Avoid shell execution with user input, use safe APIs
   - **Insecure Deserialization**: Validate input before deserializing
   - **Other OWASP Top 10**: Follow the corresponding OWASP remediation guidance
3. Ensure the fix preserves the intended functionality

## Remediate — Secrets

For each exposed secret:

1. **Remove** the hardcoded secret from the source code
2. **Replace** with an environment variable reference (e.g., `process.env.API_KEY`)
3. **Add** a placeholder entry to `.env.example`
4. **Update** `.gitignore` to include `.env` if not already present
5. **Warn the user** prominently:
   > **ACTION REQUIRED**: The secret `<name>` was found in source code (and likely in git history). You must **rotate this credential immediately**.

## Remediate — Misconfigurations & Other Findings

For each remaining finding:

- **Insecure defaults**: Fix configuration values (enable HTTPS, set secure cookie flags, restrict CORS origins)
- **Missing security headers**: Add headers like `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`
- **PII exposure**: Move personal data to encrypted storage, redact from logs
- **Supply chain issues**: Flag to the user with recommended manual actions — these typically require admin access
- **License compliance**: Flag packages with incompatible licenses for user review

For findings that **cannot be auto-fixed**, clearly list them with recommended manual actions.

## Build & Test Verification

After all remediations:

1. **Build** the project using the detected package manager
   - If the build fails: compare to baseline
   - New failure → fix and rebuild (max 3 attempts)
   - Pre-existing failure → note, do not fix
2. **Test** and diff against baseline:
   - **New failures** → fix source code and retry (max 3 attempts)
   - **Pre-existing failures** → do NOT touch
   - **Never modify tests** to make them pass
3. If a new failure cannot be resolved after 3 attempts, stop and ask the user for help
