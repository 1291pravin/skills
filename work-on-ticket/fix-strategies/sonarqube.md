# Fix Strategy: SonarQube Issues

This strategy is loaded by `/work-on-ticket` when the ticket has the `sonarqube` label. It contains the remediation logic for SonarQube issues.

## Parse Ticket Description

Extract the issue list from the ticket description. Look for the `{code:json}` block containing an array of issues. Each issue has:

- `key` — SonarQube issue key (e.g., `proj:src/api/db.ts:42`)
- `type` — BUG, VULNERABILITY, CODE_SMELL, or SECURITY_HOTSPOT
- `severity` — BLOCKER, CRITICAL, MAJOR, MINOR, INFO
- `rule` — SonarQube rule ID (e.g., `typescript:S3649`)
- `message` — description of the issue
- `component` — file path
- `line` — line number
- `effort` — estimated fix time

If the structured data cannot be parsed, fall back to fetching directly from SonarQube (requires `SONAR_HOST_URL` and `SONAR_TOKEN` env vars):
```
GET $SONAR_HOST_URL/api/issues/search?componentKeys=<project-key>&statuses=OPEN&ps=20
```

## Detect Package Manager

Refer to `../../references/package-manager-detection.md` for detection logic.

## Baseline Test Snapshot

**Run this BEFORE making any code changes.**

1. Run the test command for the detected package manager and capture full output
2. Record every failing test by name/path → store as the **baseline failures list**
3. If the build itself fails before tests run → record the build error as a baseline failure too
4. Inform the user:
   > Baseline captured: **B** tests already failing before any changes.

## Remediate Issues

Process issues in priority order (BLOCKER → CRITICAL → MAJOR → MINOR → INFO). Within same severity: Vulnerabilities → Security Hotspots → Bugs → Code Smells. Read the flagged file at the line number specified in each finding before applying any fix.

For any issue that **cannot be auto-fixed** (requires architectural change, admin access, or is genuinely ambiguous), add it to a "manual action needed" list and move on.

### Bugs

Fix incorrect program behavior:
- **Null/undefined dereference**: Add null checks or optional chaining
- **Off-by-one errors**: Correct loop bounds and index arithmetic
- **Resource leaks**: Ensure file handles, connections, streams are closed (use `try/finally` or `using`)
- **Unreachable code**: Remove or fix the logic that makes it unreachable
- **Wrong conditions**: Correct boolean logic, operator precedence errors

### Vulnerabilities

Apply OWASP-aligned fixes:
- **SQL Injection**: Replace string concatenation with parameterized queries / prepared statements
- **XSS**: Escape or sanitize user-supplied content before rendering in HTML
- **Path Traversal**: Validate and normalize file paths; use an allowlist of permitted directories
- **Command Injection**: Avoid passing user input to shell commands; use safe language APIs
- **Hardcoded Credentials**: Remove from source code; replace with `process.env.SECRET_NAME`; add placeholder to `.env.example`; ensure `.env` is in `.gitignore`; **warn the user prominently**:
  > **ACTION REQUIRED**: The credential `<name>` was found hardcoded. You must **rotate it immediately**.
- **Insecure Deserialization**: Validate and sanitize data before deserializing

### Security Hotspots

Review each hotspot and apply the appropriate fix:
- **Weak cryptography**: Replace weak algorithms (MD5, SHA-1, DES) with AES-256, SHA-256 or stronger
- **Insecure random**: Replace `Math.random()` / `Random` with `crypto.randomBytes()` / `SecureRandom`
- **LDAP/NoSQL injection**: Sanitize and escape inputs before building queries
- **Open redirect**: Validate redirect URLs against an allowlist of trusted domains
- **SSRF**: Validate and restrict outbound request URLs; block internal IP ranges

### Code Smells (MAJOR and above)

Only fix Code Smells of MAJOR severity or higher unless the chunk has no higher-priority issues:
- **Dead / unused code**: Remove unused variables, imports, functions, and classes
- **Cognitive complexity**: Split overly large or deeply nested functions into smaller ones
- **Naming violations**: Rename identifiers to follow the project's naming conventions
- **Commented-out code**: Remove code that has been commented out
- **Duplicated blocks**: Extract shared logic into a reusable function

Limit refactoring strictly to what SonarQube flagged — do not clean up surrounding code.

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
