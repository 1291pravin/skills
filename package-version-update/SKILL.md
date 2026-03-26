---
name: package-version-update
description: >
  Scan and update all project dependencies using a tiered approach.
  Tier 1: auto-updates EOL and deprecated packages. Tier 2: auto-applies
  semver-safe patch and minor updates. Tier 3: guides the user through
  major version upgrades with changelog analysis and migration plans
  (max 5 per run). Uses npm registry metadata and targeted GitHub
  changelog sections to keep context lean — no external MCP dependencies.
  Detects the package manager (npm, yarn v1/v4, pnpm, bun), takes a
  baseline test snapshot, applies updates tier by tier with build/test
  verification after each stage, and creates a PR with a comprehensive
  summary. Use this skill whenever the user mentions updating dependencies,
  upgrading packages, checking for outdated packages, or wants to keep
  their project up-to-date, even if they don't explicitly say
  "package-version-update".
---

# Package Version Update

Keep project dependencies up-to-date using a tiered approach: auto-update safe changes, guide the user through breaking changes, build and test at every stage. Follow each step in order.

## Step 1: Detect Package Manager

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
| Check outdated | `npm outdated --json` | `yarn outdated --json` | `yarn outdated --json` | `pnpm outdated --json` | `bun outdated --json` |
| Update specific | `npm install <pkg>@<ver>` | `yarn upgrade <pkg>@<ver>` | `yarn up <pkg>@<ver>` | `pnpm update <pkg>@<ver>` | `bun add <pkg>@<ver>` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

**Note on Yarn v4:** If `yarn outdated --json` produces a different format or fails, fall back to `npm outdated --json` — npm can read `package.json` regardless of the active package manager.

## Step 2: Baseline Test Snapshot

**Run this BEFORE making any code changes.**

1. Run the test command for the detected package manager and capture full output
2. Record every failing test by name/path → store as the **baseline failures list**
3. If the build itself fails before tests can run → record the build error as a baseline failure too
4. Inform the user:
   > Baseline captured: **B** tests already failing before any changes. These will not be attributed to this run.

This baseline is used in later steps to distinguish pre-existing failures from regressions introduced by updates.

## Step 3: Scan Dependencies for Available Updates

1. Run the outdated command for the detected package manager (see Step 1 table)
2. Parse the JSON output to get for each package:
   - Package name
   - Current installed version
   - Wanted version (semver-compatible latest, respecting `^` / `~` ranges in `package.json`)
   - Latest version (absolute latest on the registry)
   - Whether it is a `dependency` or `devDependency`
3. Both `dependencies` and `devDependencies` must be scanned — the outdated commands already cover both

**If the outdated command fails with authentication errors** (common with private registries), check for `.npmrc` and inform the user:
> The outdated scan failed — this may be due to a private registry that requires authentication. Please check your `.npmrc` configuration and ensure you are logged in, then let me know to retry.

## Step 4: Categorize into Tiers

For each outdated package from Step 3, assign it to a tier:

### Tier 1 — EOL / Deprecated (auto-update)

A package is Tier 1 if ANY of these are true:

- **Deprecated on npm**: Run `npm view <pkg> deprecated` for each package. If the output is non-empty, the package is deprecated. The deprecation message often names a replacement (e.g., "use `@new/pkg` instead") — save this for Step 6.
- **Node.js runtime EOL**: Check `.nvmrc`, `.node-version`, or `engines.node` in `package.json`. If the specified Node.js version has reached End of Life, flag it. Known EOL versions (as of 2025):
  - Node.js 14.x — EOL April 2023
  - Node.js 16.x — EOL September 2023
  - Node.js 18.x — EOL April 2025
  - Node.js 19.x — EOL June 2023
  - Node.js 20.x — EOL April 2026
  - Node.js 21.x — EOL June 2024

**Important**: If a package is both deprecated (Tier 1) AND requires a major version bump (would otherwise be Tier 3), classify it as **Tier 1**. Deprecated packages are a security and support risk — they should not wait for user confirmation.

### Tier 2 — Patch & Minor (auto-update)

A package is Tier 2 if:
- The **major** version of the latest release matches the current installed major version
- Only the minor and/or patch version differs (e.g., `11.2.3` → `11.2.5` or `11.3.0`)

These follow the semver contract and should not introduce breaking changes.

### Tier 3 — Major (guided migration)

A package is Tier 3 if:
- The latest version has a **different major version** than the currently installed version (e.g., `11.x` → `12.x`)
- AND it is NOT deprecated (those go to Tier 1)

## Step 5: Display Inventory

Present a summary to the user before making any changes:

> Found **N** packages with available updates:
>
> | Tier | Count | Action |
> |------|-------|--------|
> | Tier 1: EOL/Deprecated | X | Auto-update |
> | Tier 2: Patch/Minor | Y | Auto-update |
> | Tier 3: Major | Z | Guided migration (requires confirmation) |
>
> **Tier 1 packages:**
> - `deprecated-pkg` 2.0.0 → 3.1.0 (deprecated: "use `@new/pkg` instead")
>
> **Tier 2 packages:**
> - `some-lib` 4.2.1 → 4.2.8 (patch)
> - `another-lib` 3.1.0 → 3.4.0 (minor)
>
> **Tier 3 packages:**
> - `big-framework` 11.0.0 → 12.2.0 (major)
>
> Proceeding with Tier 1 and Tier 2 auto-updates first.

If Tier 3 has more than 5 packages, note:
> Tier 3 has **Z** major updates. This run will process up to **5** — run `/package-version-update` again for the rest.

If zero packages are outdated, tell the user and stop — there is nothing to update.

## Step 6: Tier 1 — Auto-update EOL/Deprecated Packages

For each Tier 1 package:

1. **Check for a replacement**: If the deprecation message names a replacement package (e.g., "use `@new/pkg` instead"):
   a. Install the replacement: e.g., `npm install @new/pkg`
   b. Search the codebase for all import/require statements referencing the old package
   c. Update all imports to use the replacement package name
   d. Remove the deprecated package: e.g., `npm uninstall deprecated-pkg`
2. **If no replacement** (just deprecated, newer version available):
   a. Update to the latest version using the package manager update command
3. Verify the lock file was regenerated correctly after each update

**For Node.js EOL**: Do NOT auto-update the Node.js version — instead, warn the user:
> **Node.js version alert**: Your project targets Node.js **X.x** which reached End of Life on **YYYY-MM-DD**. Consider upgrading to Node.js **Y.x** (current LTS). This requires updating `.nvmrc` / `.node-version` / `engines.node` and verifying compatibility.

## Step 7: Tier 2 — Auto-update Patch & Minor Versions

Update all Tier 2 packages. Batch them for efficiency:

```bash
# npm example — batch multiple packages in one command
npm install some-lib@4.2.8 another-lib@3.4.0 yet-another@2.1.9
```

Use the equivalent batch command for the detected package manager:

| npm | yarn v1 | yarn v4 | pnpm | bun |
|-----|---------|---------|------|-----|
| `npm install pkg1@ver1 pkg2@ver2` | `yarn upgrade pkg1@ver1 pkg2@ver2` | `yarn up pkg1@ver1 pkg2@ver2` | `pnpm update pkg1@ver1 pkg2@ver2` | `bun add pkg1@ver1 pkg2@ver2` |

After the batch update, verify the lock file is consistent by running the install command (e.g., `npm ci`). If it fails, run a non-frozen install to regenerate the lock file.

## Step 8: Build & Test after Tier 1 + Tier 2

After all Tier 1 and Tier 2 updates:

1. **Build** the project using the detected package manager's build command
   - If the build fails: compare the error to the baseline from Step 2
   - If the build was already broken before this run → note it in the PR, do not attempt to fix it
   - If the build failure is new (introduced by this run) → identify the cause, fix it, and rebuild (max 3 attempts)
   - If a specific Tier 2 package update caused the failure: **revert** that package to its previous version (`npm install <pkg>@<old-version>`) and add it to the "deferred updates" list with the reason

2. **Test** the project and diff results against the baseline:
   - **New failures** (were passing before, fail now) → caused by this run → investigate which update caused it
     - If identifiable, revert that specific package and note as "deferred — caused test failure"
     - If not identifiable, attempt to fix the source code (max 3 attempts)
   - **Pre-existing failures** (already in baseline) → do NOT touch; list them in the PR under "Pre-existing failures"
   - **Never modify tests** to make them pass — only fix the source code being tested or revert the problematic update

3. If you cannot resolve a new failure after 3 attempts, stop and ask the user for help

## Step 9: Tier 3 — Guided Major Version Updates

Process Tier 3 packages **one at a time**, in this order:
1. `dependencies` before `devDependencies` (production deps are higher priority)
2. Within each group, packages with more imports/usage in the codebase first

**Cap: Process a maximum of 5 major updates per run.** If more than 5 exist, process the first 5 and tell the user to re-run for the rest.

For each Tier 3 package:

### 9a. Fetch Changelog

1. Run `npm view <pkg> --json` to get the `repository.url` and `homepage` fields
2. Derive the GitHub repository URL from the `repository` field. Handle common formats:
   - `"repository": { "url": "git+https://github.com/org/repo.git" }`
   - `"repository": "github:org/repo"`
   - `"repository": "https://github.com/org/repo"`
3. Fetch the **relevant section only** of the changelog — do NOT fetch the entire file:
   - Try fetching GitHub releases for the target major version (e.g., `v12.0.0` release notes)
   - If releases are not available, fetch the raw `CHANGELOG.md` from the repository's default branch and extract only the section between the current version and the target version
4. **If GitHub fetch fails** (rate-limited, private repo, no changelog), fall back to:
   - `npm view <pkg> versions --json` to see the version timeline
   - The package's homepage for migration documentation
   - Inform the user: "Could not fetch changelog for `<pkg>`. Proceeding with version metadata only — review the migration guide manually: `<homepage-url>`"

### 9b. Analyze Breaking Changes

1. Parse the changelog/release notes for breaking changes. Look for:
   - Sections titled "BREAKING CHANGES", "Breaking", "Migration", "Upgrade Guide"
   - Entries marked with `!` in conventional commits (e.g., `feat!:`, `refactor!:`)
   - Removed or renamed APIs, changed defaults, dropped Node.js version support
2. Search the codebase for usage of affected APIs:
   - Find all files that import from the package: `import ... from '<pkg>'` or `require('<pkg>')`
   - Check which specific exports/APIs are used
   - Cross-reference with the breaking changes list
3. Classify each breaking change:
   - **Affects this project**: The removed/changed API is used in the codebase (list the files)
   - **Does not affect this project**: The API is not used anywhere

### 9c. Present Migration Plan

Display a migration plan to the user for confirmation:

> ## Major Update: `<package>` `<current>` → `<latest>`
>
> ### Breaking Changes That Affect This Project:
> - **Removed `legacyMethod()`**: Used in `src/components/Slider.tsx:42`, `src/utils/helpers.ts:18`
>   - **Migration**: Replace with `newMethod()` — same signature, renamed
> - **Changed default for `autoplay` option**: Used in `src/pages/Home.tsx:95`
>   - **Migration**: Explicitly set `autoplay: true` to preserve current behavior
>
> ### Breaking Changes That Do NOT Affect This Project:
> - Dropped IE11 support (not relevant — project targets modern browsers)
> - Removed `ServerRenderer` class (not imported anywhere)
>
> ### Migration Plan:
> 1. Update `<package>` to `<latest>`
> 2. Replace `legacyMethod()` → `newMethod()` in 2 files
> 3. Add explicit `autoplay: true` in 1 file
>
> **Proceed with this update? (yes / no / skip)**

Wait for the user to confirm before applying. If the user says "skip", move to the next Tier 3 package.

### 9d. Apply Migration (after user confirms)

1. Update the package using the package manager update command
2. Apply the code migrations described in the plan:
   - Update import statements if package was renamed or exports changed
   - Replace removed/renamed API calls with their replacements
   - Update configuration options that changed
   - Adjust types/interfaces if TypeScript definitions changed
3. **Build and test**:
   - Build the project — if it fails due to this update, attempt to fix (max 3 attempts)
   - Run tests — if new failures appear, attempt to fix (max 3 attempts)
4. If the update cannot be stabilized after 3 attempts:
   - Offer the user the choice: revert this update or continue debugging
   - If reverting: `npm install <pkg>@<old-version>`, undo code changes, add to "deferred" list
   - Move to the next Tier 3 package

**After processing 5 Tier 3 packages** (or all of them if fewer than 5), if more remain:
> **N remaining** major updates were not processed in this run. Run `/package-version-update` again to continue with the next batch.

## Step 10: Final Build & Test

After all tiers have been processed:

1. Run a full build
2. Run the full test suite
3. Compare results against the baseline from Step 2
4. Report final status to the user:
   > **Final status:**
   > - Build: PASSING / FAILING (pre-existing)
   > - Tests: **X** passing, **Y** failing (**B** pre-existing, **0** new)
   > - Packages updated: **A** (Tier 1) + **B** (Tier 2) + **C** (Tier 3)
   > - Deferred: **D** packages (reverted due to failures)

## Step 11: Create Pull Request

1. **Create a branch**: `chore/dependency-updates-YYYY-MM-DD` (use today's date)
2. **Stage all changes**: `git add` the modified files — be specific:
   - `package.json`
   - Lock file (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, or `bun.lock`)
   - Any source files modified during Tier 1 import replacements or Tier 3 migrations
   - Do NOT add unrelated files
3. **Commit** with a descriptive message:
   ```
   chore(deps): update project dependencies

   - Updated X deprecated/EOL packages (Tier 1)
   - Updated Y packages with patch/minor versions (Tier 2)
   - Migrated Z packages to new major versions (Tier 3)
   ```
4. **Push** the branch to the remote
5. **Create a PR** with this body:

   ```markdown
   ## Dependency Updates

   ### Summary
   | Tier | Description | Packages Updated | Breaking Changes |
   |------|-------------|-----------------|-----------------|
   | Tier 1 | EOL/Deprecated | X | N/A — auto-updated |
   | Tier 2 | Patch/Minor | Y | None (semver-safe) |
   | Tier 3 | Major | Z | W breaking changes addressed |

   ### Package Updates
   | Package | Old Version | New Version | Tier | Notes |
   |---------|-------------|-------------|------|-------|
   | deprecated-pkg | 2.0.0 | @new/pkg 3.1.0 | Tier 1 | Replaced — was deprecated |
   | some-lib | 4.2.1 | 4.2.8 | Tier 2 | Patch update |
   | another-lib | 3.1.0 | 3.4.0 | Tier 2 | Minor update |
   | big-framework | 11.0.0 | 12.2.0 | Tier 3 | See migration changes below |

   ### Migration Changes (Tier 3)
   - `src/components/Slider.tsx`: Replaced `legacyMethod()` with `newMethod()` (big-framework v12 migration)
   - `src/pages/Home.tsx`: Added explicit `autoplay: true` to preserve behavior after default change

   ### Deferred Updates
   | Package | Attempted | Reason |
   |---------|-----------|--------|
   | problem-pkg | 3.0.0 → 4.0.0 | Reverted — caused test failure in `test/integration/foo.test.ts` |

   ### Remaining Updates
   **N** major version updates were not processed in this run. Run `/package-version-update` again to continue.

   ### Manual Action Items
   - [ ] Review Tier 3 migration changes for correctness
   - [ ] Consider upgrading Node.js runtime from 18.x to 20.x (18.x reaches EOL April 2025)
   - [ ] Investigate deferred packages listed above

   ### Build & Test Status
   - Build: PASSING
   - Tests: PASSING (X new failures fixed; B pre-existing failures unchanged — not caused by this run)
   - Pre-existing failures (do not review): `test/legacy/foo.test.ts`, `test/integration/bar.test.ts`
   ```

6. Share the PR URL with the user
7. If Tier 3 packages remain, remind the user to run `/package-version-update` again
