---
name: apiiro-fix
description: >
  Fetch and fix all Apiiro security findings for the current repository.
  Handles SCA (vulnerable packages), SAST (code vulnerabilities), secrets
  exposure, misconfigurations, PII detection, and supply chain issues.
  Installs Apiiro CLI if missing, authenticates, detects the package manager,
  remediates all issues, builds, tests, and creates a PR. Use this skill
  whenever the user mentions Apiiro, security alerts, vulnerability
  remediation, dependency updates for security, or wants to fix security
  issues flagged by Apiiro, even if they don't explicitly say "apiiro-fix".
---

# Apiiro Security Remediation

Automate the full Apiiro security remediation workflow: detect issues, fix them, verify the fixes, and create a PR. Follow each step in order.

**Re-run behavior:** Before starting, check if a branch matching `fix/apiiro-security-remediation-chunk-*` already exists for today's date. If it does, ask the user whether to continue from where the previous run left off (next chunk) or start fresh on a new branch.

## Step 1: Check & Install Apiiro CLI

Run `apiiro --version` to check if the Apiiro CLI is installed.

**If not installed:**

1. Detect the platform:
   - **macOS / Linux**: Run `brew tap apiiro/tap && brew install apiiro`
   - **Windows**: Tell the user:
     > Apiiro CLI is not installed. Please download it from https://github.com/apiiro/cli-releases/releases — pick the Windows binary, extract it, and add it to your PATH.
     > Once installed, let me know and I'll continue.
2. After installation, verify with `apiiro --version`
3. If installation fails, stop and ask the user for help — do not proceed without a working CLI

## Step 2: Authenticate

Run `apiiro auth status` to check if the user is logged in.

**If not authenticated:**

Tell the user:
> You need to log in to Apiiro. Please run `apiiro login` in your terminal — it will open a browser for OAuth authentication.
>
> In Claude Code, you can type `! apiiro login` to run it directly in this session.

Wait for the user to confirm they have logged in before proceeding. Do not skip this step.

## Step 3: Detect Package Manager

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

## Step 4: Detect Current Repository

Identify which repo to query in Apiiro:

1. Run `git remote get-url origin` to get the remote URL
2. Extract the `org/repo` name from the URL — handle all formats:
   - `https://github.com/org/repo.git`
   - `git@github.com:org/repo.git`
   - GitLab, Bitbucket, and other hosts
3. Use this identifier to scope all Apiiro queries to this repo only

**If the remote URL can't be determined** (no git remote, or not a git repo), ask the user:
> I couldn't detect the repository. What is the repo name or identifier in Apiiro?

## Step 5: Fetch & Categorize Findings

Run the Apiiro CLI to get all security findings for this repo:

```bash
apiiro risks --repo <repo-identifier> --output json
```

If the command fails or the repo isn't found in Apiiro, ask the user for the correct Apiiro repo identifier and retry.

If the command times out or returns partial/truncated results, retry once. If it fails again, inform the user of the error and ask whether to proceed with partial results or stop.

Parse the JSON output and categorize findings into:
- **SCA**: Vulnerable open-source packages
- **SAST**: Code-level security vulnerabilities (OWASP Top 10)
- **Secrets**: Exposed API keys, tokens, passwords, credentials
- **Misconfigurations**: Insecure defaults, missing security headers, permissive CORS
- **PII/PHI/PCI**: Personal or sensitive data exposure in code
- **Supply Chain**: CI/CD misconfigs, weak branch protections
- **Other**: Anything that doesn't fit the above

**Sort all findings by severity** (Critical → High → Medium → Low) and within the same severity, order by category: Secrets → Vulnerabilities (SAST) → Package Vulnerabilities (SCA) → Misconfigurations → PII → Other.

Display a summary to the user before proceeding:
> Found **N** total findings: **X** package vulnerabilities, **Y** code issues, **Z** exposed secrets, and **W** other findings.
>
> This run will fix issues **1–20** (highest severity first). Run `/apiiro-fix` again to continue with the next chunk.

If there are zero findings, tell the user and stop — there is nothing to fix.

**Chunking:** Process up to **20 findings per run** to keep PRs focused and reviewable. If there are 20 or fewer total findings, fix them all in one run.

## Step 6: Baseline Test Snapshot

**Run this BEFORE making any code changes.**

1. Run the test command for the detected package manager and capture full output
2. Record every failing test by name/path → store as the **baseline failures list**
3. If the build itself fails before tests can run → record the build error as a baseline failure too
4. Inform the user:
   > Baseline captured: **B** tests already failing before any changes. These will not be attributed to this run.

This baseline is used in Step 11 to distinguish pre-existing failures from regressions you introduce.

## Step 7: Remediate — Package Vulnerabilities (SCA)

For each vulnerable package identified:

1. Note the current installed version and the recommended safe version from the Apiiro finding
2. Update the package using the detected package manager (see Step 3 table)
3. If the update requires a **major version bump**:
   - Look up the package's changelog or migration guide (check the package's GitHub releases page or documentation)
   - Identify breaking changes that affect this project
   - Update code to accommodate the breaking changes
4. After updating, verify the lock file was regenerated correctly

## Step 8: Remediate — Code Vulnerabilities (SAST)

For each SAST finding:

1. Read the flagged file at the line number specified in the finding
2. Identify the vulnerability type (XSS, SQL injection, path traversal, command injection, insecure deserialization, etc.)
3. Apply the appropriate fix based on the vulnerability:
   - **XSS**: Sanitize/escape user input before rendering
   - **SQL Injection**: Use parameterized queries or prepared statements
   - **Path Traversal**: Validate and sanitize file paths, use allowlists
   - **Command Injection**: Avoid shell execution with user input, use safe APIs
   - **Insecure Deserialization**: Validate input before deserializing
   - **Other OWASP Top 10**: Follow the corresponding OWASP remediation guidance
4. Ensure the fix preserves the intended functionality — don't break the feature

## Step 9: Remediate — Secrets

For each exposed secret:

1. **Remove** the hardcoded secret from the source code
2. **Replace** with an environment variable reference (e.g., `process.env.API_KEY`) or a secrets manager lookup
3. **Add** a placeholder entry to `.env.example` (create the file if it does not exist) so other developers know the variable is needed
4. **Update** `.gitignore` to include `.env` if not already present
5. **Warn the user** prominently:
   > **ACTION REQUIRED**: The secret `<name>` was found in source code (and likely in git history). You must **rotate this credential immediately** — changing it in code alone is not enough since the old value is in the commit history.

Do not attempt to rewrite git history to remove secrets — that is a manual decision for the user.

## Step 10: Remediate — Misconfigurations & Other Findings

For each remaining finding:

- **Insecure defaults**: Fix configuration values (e.g., enable HTTPS, set secure cookie flags, restrict CORS origins)
- **Missing security headers**: Add headers like `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`
- **PII exposure**: Move personal data to encrypted storage, redact from logs, ensure compliance
- **Supply chain issues**: Flag to the user with recommended manual actions (e.g., "Enable branch protection on the main branch") — these typically require admin access and can't be auto-fixed
- **License compliance**: Flag packages with incompatible licenses for user review

For any findings that **cannot be auto-fixed**, clearly list them with recommended manual actions at the end.

## Step 11: Build & Test

After all remediations:

1. **Build** the project using the detected package manager's build command
   - If the build fails: compare the error to the baseline
   - If build was already broken before this run → note it in the PR, do not attempt to fix it
   - If the build failure is new (introduced by this run) → identify the cause, fix it, and rebuild (max 3 attempts)
2. **Test** the project and diff results against the baseline:
   - **New failures** (were passing before, fail now) → caused by this run → fix the source code and retry (max 3 attempts)
   - **Pre-existing failures** (already in baseline) → do NOT touch; list them in the PR under "Pre-existing failures"
   - **Never modify tests** to make them pass — only fix the source code being tested
3. If you cannot resolve a new failure after 3 attempts, offer to roll back all changes with `git checkout -- .` and inform the user which specific findings caused the failures. Otherwise, stop and ask the user for help

## Step 12: Create Pull Request

1. **Create a branch**: `fix/apiiro-security-remediation-chunk-N-YYYY-MM-DD` (N = chunk number starting from 1; use today's date)
2. **Stage all changes**: `git add` the modified files (be specific — don't add unrelated files)
3. **Commit** with a descriptive message:
   ```
   fix(security): remediate Apiiro security findings

   - Updated X vulnerable packages
   - Fixed Y code vulnerabilities (SAST)
   - Removed Z exposed secrets
   - Fixed W misconfigurations
   ```
4. **Push** the branch to the remote
5. **Create a PR** with a comprehensive body:

   ```markdown
   ## Security Remediation — Apiiro Findings (Chunk N of ~M)

   **Severity range fixed in this chunk:** Critical → High (issues 1–20 of N total)

   ### Summary
   | Category | Found | Fixed | Manual Action Needed |
   |----------|-------|-------|---------------------|
   | Package Vulnerabilities (SCA) | X | X | 0 |
   | Code Vulnerabilities (SAST) | Y | Y | 0 |
   | Exposed Secrets | Z | Z | Z (rotate credentials) |
   | Misconfigurations | W | W | 0 |
   | Other | N | N | N |

   ### Package Updates
   | Package | Old Version | New Version | CVE/Issue |
   |---------|-------------|-------------|-----------|
   | example-pkg | 1.2.3 | 1.2.5 | CVE-2024-XXXX |

   ### Code Changes
   - `src/api/handler.ts`: Fixed SQL injection vulnerability (parameterized query)
   - `src/utils/render.ts`: Fixed XSS by escaping user input

   ### Action Items (Manual)
   - [ ] Rotate exposed credential: `API_KEY` (was in `src/config.ts`)
   - [ ] Enable branch protection on `main` branch
   - [ ] Review license compliance for `some-package`

   ### Remaining Issues
   **N - 20** issues remain. Run `/apiiro-fix` again to fix the next chunk.

   ### Build & Test Status
   - Build: PASSING
   - Tests: PASSING (X new failures fixed; B pre-existing failures unchanged — not caused by this run)
   - Pre-existing failures (do not review): `test/legacy/foo.test.ts`, ...
   ```

6. Share the PR URL with the user
7. If issues remain, remind the user how many are left and prompt them to run `/apiiro-fix` again for the next chunk
