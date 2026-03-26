---
name: sonarqube-fix
description: >
  Fetch and fix SonarQube issues (Bugs, Vulnerabilities, Security Hotspots,
  Code Smells) for the current repository on a self-hosted SonarQube instance.
  Processes up to 20 issues per run in severity order (BLOCKER → CRITICAL →
  MAJOR → MINOR → INFO), creates a focused PR per chunk, and repeats until
  all issues are resolved. Use this skill whenever the user mentions SonarQube,
  code quality issues, static analysis findings, or wants to fix issues flagged
  by SonarQube, even if they don't explicitly say "sonarqube-fix".
---

# SonarQube Issue Remediation

Automate the full SonarQube remediation workflow: connect to your self-hosted SonarQube instance, fetch all open issues, fix them in severity order (20 per run), and create a focused PR per chunk. Follow each step in order.

**Re-run behavior:** Before starting, check if a branch matching `fix/sonarqube-chunk-*` already exists for today's date. If it does, ask the user whether to continue from where the previous run left off (next chunk) or start fresh on a new branch.

## Step 1: Check & Install sonar-scanner CLI

Run `sonar-scanner --version` to check if the sonar-scanner CLI is installed.

**If not installed:**

1. Detect the platform:
   - **macOS / Linux**: Run `brew install sonar-scanner`
     After install, verify the binary path: `which sonar-scanner`
     Confirm it points to a Homebrew-managed path (e.g. `/opt/homebrew/bin/sonar-scanner` or `/usr/local/bin/sonar-scanner`).
     If it points somewhere unexpected, warn the user — a non-Homebrew binary could be a supply-chain risk.
   - **Windows**: Tell the user:
     > sonar-scanner is not installed. Please download it from the official SonarSource docs — extract the archive and add the `bin` folder to your PATH.
     > Once installed, let me know and I'll continue.
2. After installation, verify with `sonar-scanner --version`
3. If installation fails, stop and ask the user for help — do not proceed without a working CLI

**Security note — CLI integrity:**
Homebrew verifies SHA256 checksums automatically. For enterprise/air-gapped environments, download the official `.zip` directly from SonarSource and verify the checksum manually before extracting.

## Step 2: Resolve Server URL & Token

1. Resolve the **SonarQube server URL** in this order:
   - Check `SONAR_HOST_URL` environment variable
   - Fall back to `sonar.host.url` in `sonar-project.properties`
   - If still missing, ask the user:
     > What is the URL of your SonarQube server? (e.g. `http://sonarqube.mycompany.com`)

2. Resolve the **authentication token** in this order:
   - Check `SONAR_TOKEN` environment variable ✅ preferred
   - Check `sonar.token` in `sonar-project.properties` ⚠️ only if the file is gitignored (see security note)
   - If still missing, ask the user to generate a token in SonarQube (My Account → Security → Generate Token) with **"Execute Analysis"** permission only (least-privilege), then set it safely:
     > To avoid saving the token in your shell history, run:
     > `read -s SONAR_TOKEN && export SONAR_TOKEN`
     > Paste the token and press Enter. Let me know when done.

3. **Security check — prevent token leakage:**
   - Check whether `sonar-project.properties` is tracked by git: `git ls-files sonar-project.properties`
   - If it IS tracked AND it contains `sonar.token`, **stop immediately** and tell the user:
     > **SECURITY RISK**: `sonar-project.properties` is committed to git and contains a `sonar.token` value. This token is now in your git history.
     > **You must:**
     > 1. Revoke the token immediately in SonarQube (My Account → Security)
     > 2. Remove `sonar.token` from `sonar-project.properties`
     > 3. Add `sonar-project.properties` to `.gitignore` (or move the token to an env var)
     > 4. Generate a new token and set it via `export SONAR_TOKEN=<new-token>`
     > Let me know when done and I will continue.
   - If `sonar-project.properties` is NOT tracked, ensure `.gitignore` includes it or the `sonar.token` line.

4. Verify connectivity:
   ```bash
   curl -s -u "$SONAR_TOKEN:" "$SONAR_HOST_URL/api/system/status"
   ```
   Expected response: `{"status":"UP"}`. If it fails, check URL and token and retry.

**Security note — token best practices:**
- Use a **project-scoped "Execute Analysis" token** — never an admin or global token
- Tokens are stored by SonarQube as bcrypt hashes; you cannot retrieve a token after creation — if lost, revoke and regenerate
- In CI/CD (GitHub Actions, GitLab CI, Jenkins): store as a masked/protected secret variable, never in code or `sonar-project.properties`
- Tokens do not expire by default — set an expiry date in SonarQube if your version supports it

## Step 3: Detect Project Key

1. Read `sonar.projectKey` from `sonar-project.properties` if the file exists
2. If not found, derive from the git remote:
   - Run `git remote get-url origin`
   - Use the repository name (last path segment, without `.git`) as the project key
3. Confirm the project exists in SonarQube:
   ```
   GET $SONAR_HOST_URL/api/projects/search?projects=<key>
   Authorization: Basic base64($SONAR_TOKEN:)
   ```
   If the project is not found, ask the user to confirm the correct project key.

## Step 4: Detect Package Manager

Determine which package manager the project uses. Check in this order (first match wins):

1. `package.json` → `packageManager` field (e.g., `"packageManager": "pnpm@9.0.0"`)
2. `bun.lockb` or `bun.lock` exists → **bun**
3. `pnpm-lock.yaml` exists → **pnpm**
4. `yarn.lock` exists → **yarn**
   - If `.yarnrc.yml` also exists or `packageManager` contains `yarn@4` or higher → **Yarn 4 (Berry)**
   - Otherwise → **Yarn Classic (v1)**
5. `package-lock.json` exists → **npm**

If no lock file is found, ask the user which package manager to use.

Use the detected package manager for ALL commands throughout the workflow:

| Action | npm | yarn v1 | yarn v4 | pnpm | bun |
|--------|-----|---------|---------|------|-----|
| Install deps | `npm ci` | `yarn install --frozen-lockfile` | `yarn install --immutable` | `pnpm install --frozen-lockfile` | `bun install --frozen-lockfile` |
| Update pkg | `npm install <pkg>@<ver>` | `yarn upgrade <pkg>@<ver>` | `yarn up <pkg>@<ver>` | `pnpm update <pkg>` | `bun add <pkg>@<ver>` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

## Step 5: Baseline Test Snapshot

**Run this BEFORE making any code changes.**

1. Run the test command for the detected package manager and capture full output
2. Record every failing test by name/path → store as the **baseline failures list**
3. If the build itself fails before tests run → record the build error as a baseline failure too
4. Inform the user:
   > Baseline captured: **B** tests already failing before any changes. These will not be attributed to this run.

This baseline is used in Step 8 to distinguish pre-existing failures from regressions introduced by fixes.

## Step 6: Fetch & Prioritize Issues

**Fetch all open issues** (paginate until all pages are retrieved):

```
GET $SONAR_HOST_URL/api/issues/search
  ?componentKeys=<project-key>
  &types=BUG,VULNERABILITY,CODE_SMELL
  &statuses=OPEN
  &severities=BLOCKER,CRITICAL,MAJOR,MINOR,INFO
  &ps=500&p=1
```

Increment `p` until `total <= p * ps`. Also fetch Security Hotspots:

```
GET $SONAR_HOST_URL/api/hotspots/search
  ?projectKey=<project-key>
  &status=TO_REVIEW
  &ps=500&p=1
```

**Sort all issues by priority:**
1. BLOCKER
2. CRITICAL
3. MAJOR
4. MINOR
5. INFO

Within the same severity, order by type: Vulnerabilities → Security Hotspots → Bugs → Code Smells.

**Note:** Security Hotspots use `vulnerabilityProbability` (HIGH/MEDIUM/LOW) instead of the standard `severity` field. Map them as follows for sorting: HIGH → between CRITICAL and MAJOR, MEDIUM → MAJOR, LOW → MINOR.

**Display the full inventory** before fixing:

> Found **N** total issues:
>
> | Severity | Bugs | Vulnerabilities | Hotspots | Code Smells |
> |----------|------|-----------------|----------|-------------|
> | BLOCKER  | ...  | ...             | ...      | ...         |
> | CRITICAL | ...  | ...             | ...      | ...         |
> | MAJOR    | ...  | ...             | ...      | ...         |
> | MINOR    | ...  | ...             | ...      | ...         |
> | INFO     | ...  | ...             | ...      | ...         |
>
> This run will fix issues **1–20** (highest severity first). Run `/sonarqube-fix` again to continue with the next chunk.

If zero issues are found, tell the user and stop — there is nothing to fix.

## Step 7: Remediate the Chunk (issues 1–20)

Process each issue in priority order. Read the flagged file at the line number specified in each finding before applying any fix.

For any issue that **cannot be auto-fixed** (requires architectural change, admin access, or is genuinely ambiguous), add it to a "manual action needed" list and move on — do not block the run.

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
- **Hardcoded Credentials**: Remove secret from source code; replace with `process.env.SECRET_NAME` (or equivalent); add a placeholder to `.env.example` (create the file if it does not exist); ensure `.env` is in `.gitignore`; **warn the user prominently**:
  > **ACTION REQUIRED**: The credential `<name>` was found hardcoded. You must **rotate it immediately** — it is likely already in git history. Changing it in code alone is not sufficient.
- **Insecure Deserialization**: Validate and sanitize data before deserializing

### Security Hotspots

Review each hotspot and apply the appropriate fix:
- **Weak cryptography**: Replace weak algorithms (MD5, SHA-1, DES) with AES-256, SHA-256 or stronger
- **Insecure random**: Replace `Math.random()` / `Random` with `crypto.randomBytes()` / `SecureRandom`
- **LDAP/NoSQL injection**: Sanitize and escape inputs before building queries
- **Open redirect**: Validate redirect URLs against an allowlist of trusted domains
- **SSRF**: Validate and restrict outbound request URLs; block internal IP ranges

### Code Smells (MAJOR and above)

Only fix Code Smells of MAJOR severity or higher unless this chunk has no higher-priority issues:
- **Dead / unused code**: Remove unused variables, imports, functions, and classes
- **Cognitive complexity**: Split overly large or deeply nested functions into smaller ones
- **Naming violations**: Rename identifiers to follow the project's naming conventions
- **Commented-out code**: Remove code that has been commented out
- **Duplicated blocks**: Extract shared logic into a reusable function

Limit refactoring strictly to what SonarQube flagged — do not clean up surrounding code.

## Step 8: Build & Test

After applying all fixes in the chunk:

1. **Build** the project
   - If the build fails: compare the error to the baseline captured in Step 5
   - If the build was already broken before this run → note it in the PR, do not attempt to fix it
   - If the build failure is new (introduced by this run) → investigate and fix, retry up to 3 times

2. **Run tests** and diff results against the baseline:
   - **New failures** (were passing before, fail now) → caused by this run → fix the source code and retry (max 3 attempts per failure)
   - **Pre-existing failures** (already in baseline) → do NOT modify; list them in the PR
   - **Never modify tests** to make them pass — only fix the source code being tested

3. If a new failure cannot be resolved after 3 attempts, offer to roll back all changes with `git checkout -- .` and inform the user which specific findings caused the failures. Otherwise, stop and ask the user for help before proceeding

## Step 9: Create Pull Request

1. **Branch name**: `fix/sonarqube-chunk-N-YYYY-MM-DD`
   (N = chunk number starting from 1; use today's date)
2. **Stage** only the files modified during remediation — do not add unrelated files
3. **Commit** with a descriptive message:
   ```
   fix(quality): remediate SonarQube issues — chunk N

   - Fixed X bugs
   - Fixed Y vulnerabilities
   - Reviewed Z security hotspots
   - Resolved W code smells
   Severity range: BLOCKER/CRITICAL
   ```
4. **Push** the branch to the remote
5. **Create a PR** with the following body:

   ```markdown
   ## SonarQube Remediation — Chunk N of ~M

   **Severity range fixed in this chunk:** BLOCKER → CRITICAL (issues 1–20 of N total)

   ### Summary
   | Category | Found in chunk | Fixed | Manual Action Needed |
   |----------|----------------|-------|---------------------|
   | Bugs | X | X | 0 |
   | Vulnerabilities | Y | Y | 0 |
   | Security Hotspots | Z | Z | Z |
   | Code Smells | W | W | 0 |

   ### Files Changed
   - `src/api/db.ts:42` — Fixed SQL injection (parameterized query)
   - `src/utils/render.ts:17` — Fixed XSS (escaped user output before rendering)

   ### Manual Actions Required
   - [ ] Rotate credential: `API_KEY` (was hardcoded in `src/config.ts`)
   - [ ] Architectural refactor needed: `UserService.processAll()` complexity > 30 (exceeds auto-fix threshold)

   ### Remaining Issues
   **N - 20** issues remain. Run `/sonarqube-fix` again to fix the next chunk (issues 21–40).

   ### Build & Test
   - Build: PASSING
   - Tests: PASSING (X new failures fixed; B pre-existing failures unchanged — not caused by this run)
   - Pre-existing failures (do not review): `test/legacy/foo.test.ts`, `test/integration/bar.test.ts`
   ```

6. Share the PR URL with the user
7. Remind the user how many issues remain and ask them to run `/sonarqube-fix` again for the next chunk
