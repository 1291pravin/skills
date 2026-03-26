---
name: aqa-usablenet
description: >
  Run a UsableNet AQA accessibility scan for a given site or suite, fetch
  violations from the completed run, fix them in severity order (critical →
  serious → moderate → minor) up to 20 per run, and create a focused PR per
  chunk. Handles color contrast, missing alt text, ARIA labels, form labels,
  keyboard navigation, link/button names, document title, heading order,
  landmarks, and focus visibility. Skips third-party and auto-generated files.
  Use this skill whenever the user mentions UsableNet, AQA, accessibility
  violations, WCAG issues, a11y scan, or wants to fix accessibility findings,
  even if they don't explicitly say "aqa-usablenet". Accepts an optional site
  name (e.g. fr.filorga.com) to identify the target suite automatically.
---

# UsableNet AQA Accessibility Remediation

Automate the full AQA remediation workflow: connect to UsableNet AQA, create and run an accessibility test for the target suite, fetch all violations, fix them in severity order (20 per run), and create a focused PR per chunk. Follow each step in order.

## Step 1: Validate Environment Variables

Check that the required environment variables are set:

```bash
[ -z "$AQA_API_KEY" ]    && echo "MISSING: AQA_API_KEY"    || echo "OK: AQA_API_KEY"
[ -z "$AQA_TEAM_SLUG" ]  && echo "MISSING: AQA_TEAM_SLUG"  || echo "OK: AQA_TEAM_SLUG"
```

`AQA_SUITE_ID` is optional — the skill can resolve the suite automatically (see Step 3).

**If any required variable is missing**, stop and tell the user:

> The following environment variable is not set: `AQA_API_KEY` / `AQA_TEAM_SLUG`.
> Please set it in your shell before running this skill:
> ```
> export AQA_API_KEY=<your-api-key>
> export AQA_TEAM_SLUG=<your-team-slug>
> ```
> You can find these values in your UsableNet AQA dashboard.

**Security note**: Never print the key value. Never commit it to any project file. Always set via `export` in the terminal.

## Step 2: Verify API Connectivity

Run a lightweight connectivity check before doing any real work:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/suites"
```

Interpret the HTTP status:

| Status | Meaning | Action |
|--------|---------|--------|
| `200` | Connected | Proceed |
| `401` | Invalid API key | Ask user to check `AQA_API_KEY` |
| `403` | Insufficient permissions | Ask user to verify API key has access to this team |
| `404` | Team slug not found | Ask user to check `AQA_TEAM_SLUG` |
| `5xx` | AQA API is down | Ask user to retry later |

Do not proceed past this step until the API returns `200`.

## Step 3: List Suites and Resolve Target Suite

Fetch all suites for the team:

```bash
curl -s \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/suites"
```

The response contains: `{ suites: [ { id, name, numFlows, numCrawlers }, ... ] }`

**If zero suites are returned**, stop and tell the user:

> No suites found for team `$AQA_TEAM_SLUG`. Please create a suite in the UsableNet AQA dashboard first, then re-run this skill.

**Resolve the target suite using this priority order:**

1. **`AQA_SUITE_ID` is set** → use that suite ID directly, skip name matching, proceed to Step 4
2. **User provided a site name** (e.g. `fr.filorga.com`) → search suite names for a case-insensitive match:
   - If exactly one match found → use it, report to user: `Using suite: "{name}" (id: {id})`
   - If multiple matches found → list them and ask user to set `AQA_SUITE_ID=<id>`
   - If no match found → display all suites and ask user to set `AQA_SUITE_ID=<id>`
3. **Exactly one suite exists** → use it automatically, report to user: `Using suite: "{name}" (id: {id})`
4. **Multiple suites, no site name given** → display the suite list and stop:

> Multiple suites found. Please re-run with a site name or set the suite ID:
>
> | Suite ID | Name | Flows | Crawlers |
> |----------|------|-------|----------|
> | `abc123` | fr.filorga.com | 5 | 2 |
> | `def456` | en.filorga.com | 3 | 1 |
>
> Set the suite: `export AQA_SUITE_ID=<id>`

Store the resolved suite ID as `SUITE_ID` for use in subsequent steps.

## Step 4: Get Suite Details and Collect Flow IDs

Fetch the suite to retrieve its flows. Poll every 5 seconds until `numFlows >= 1`:

```bash
curl -s \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/suites/$SUITE_ID"
```

If `numFlows` is still 0 after polling, wait 5 seconds and retry. After 60 seconds with no flows, stop and tell the user the suite has no flows configured.

Collect all flow IDs as a JSON array: `FLOW_IDS = suite.flows.map(f => f.id)`

Report to the user:
> Suite **{suiteName}** has **{numFlows}** flow(s). Creating accessibility test...

## Step 5: Create Accessibility Test

Generate a timestamp-based test name: `aqa-scan-YYYY-MM-DD-HH-MM` (use the current date/time).

Create the test using all flows from the suite:

```bash
curl -s -X POST \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "suiteId": "'"$SUITE_ID"'",
    "name": "'"$TEST_NAME"'",
    "description": "Automated AQA accessibility scan",
    "flowIds": '"$FLOW_IDS_JSON"',
    "rulesetPackId": "v2",
    "rulesetId": "wcag22"
  }' \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/create"
```

Capture `test.id` from the response as `TEST_ID`. If the request fails, report the error response body to the user and stop.

## Step 6: Run the Test

Trigger the test run:

```bash
curl -s -X POST \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/$TEST_ID/run"
```

Capture `run.id` from the response as `RUN_ID`.

Report to user:
> Test **{testName}** is running. Run ID: `{runId}`. Waiting for scan to complete...

## Step 7: Poll Until Run Completes

Poll the run status every 10 seconds until `run.status === 'ready'`:

```bash
curl -s \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID"
```

On each poll, report progress:
> Run `{runId}` status: **{status}** — polling again in 10s...

When status is `ready`:
> Scan complete.

**Timeout**: If the run has not reached `ready` status after 30 minutes, stop and tell the user:
> The scan is taking longer than expected. Check the AQA dashboard for run `{runId}` status and re-run this skill with `AQA_SUITE_ID={suiteId}` once it completes.

## Step 8: Fetch All Issues

First, get the list of flows with their result summary:

```bash
curl -s \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID/flows"
```

Then, for each flow in the response, fetch its issues:

```bash
curl -s \
  -H "Accept: application/json" \
  -H "X-Team: $AQA_API_KEY" \
  "https://api-aqa.usablenet.com/v3.1/$AQA_TEAM_SLUG/a11y/tests/runs/$RUN_ID/flows/$FLOW_ID/issues?changeIndex=-1&manual=false&stepIndex=0"
```

For each issue in `issuesData.issues`, collect:

```
{
  flowId, flowName,
  selector:      issue.selectors?.[0],
  tagName:       issue.tagName,
  needFixTitle:  issue.needFixTitle,
  ruleId:        issue.ruleId,
  solutionId:    issue.solutionId,
  impact:        issue.impact,           // 'critical' | 'serious' | 'moderate' | 'minor'
  description:   issue.description,
  solutions:     issue.solutions ?? [],
  wcagCriteria:  issue.wcagCriteria,
  html:          issue.html
}
```

Aggregate all issues across all flows into a single list `ALL_ISSUES`.

**If zero issues are found**, report a clean scan and stop:
> No accessibility issues found in this scan. The site passes WCAG 2.2 checks for the configured flows.

## Step 9: Group, Prioritize, and Display Issues

Sort `ALL_ISSUES` by `impact` in this order: `critical` → `serious` → `moderate` → `minor`.

Group by `ruleId` within each severity level. Display a full inventory before fixing:

> Found **{N}** total accessibility issues across **{numFlows}** flow(s):
>
> | Severity | Rule | Count |
> |----------|------|-------|
> | critical | color-contrast | 4 |
> | serious  | image-alt | 7 |
> | serious  | aria-required-attr | 3 |
> | moderate | label | 5 |
> | minor    | heading-order | 2 |
>
> This run will fix issues **1–20** (highest severity first). Re-run this skill to fix the next chunk.

Take the first 20 issues from the sorted list as the **current chunk**.

## Step 10: Detect Package Manager

Determine which package manager the project uses. Check in this order (first match wins):

1. `package.json` → `packageManager` field (e.g. `"packageManager": "pnpm@9.0.0"`)
2. `bun.lockb` or `bun.lock` exists → **bun**
3. `pnpm-lock.yaml` exists → **pnpm**
4. `yarn.lock` exists → **yarn**
   - If `.yarnrc.yml` exists or `packageManager` field contains `yarn@4` or higher → **Yarn 4 (Berry)**
   - Otherwise → **Yarn Classic (v1)**
5. `package-lock.json` exists → **npm**

If no lock file is found, ask the user which package manager to use.

Use the detected package manager for ALL build and test commands throughout:

| Action | npm | yarn v1 | yarn v4 | pnpm | bun |
|--------|-----|---------|---------|------|-----|
| Install | `npm ci` | `yarn install --frozen-lockfile` | `yarn install --immutable` | `pnpm install --frozen-lockfile` | `bun install --frozen-lockfile` |
| Build | `npm run build` | `yarn build` | `yarn build` | `pnpm run build` | `bun run build` |
| Test | `npm test` | `yarn test` | `yarn test` | `pnpm test` | `bun test` |

## Step 11: Baseline Test Snapshot

Before making any changes, run the full test suite and record the current state:

1. Run the test command for the detected package manager
2. Capture the full output
3. Record the names/paths of any currently failing tests
4. Store this as the **baseline failure list**

Use the baseline throughout this workflow: only treat a test failure as a regression if it does NOT appear in the baseline. Never modify tests to make them pass — only fix source code.

## Step 12: Map Issues to Source Files

For each issue in the current chunk (up to 20):

1. Use the `flowName` or flow URL to identify the page (e.g. `/about`, `/checkout`)
2. Map the page path to a source file by looking for file-based routing in:
   - `src/pages/`, `app/`, `pages/`, `src/views/`, `src/components/`
   - Next.js: `/about` → `app/about/page.tsx` or `src/pages/about.tsx`
   - Nuxt: `/about` → `pages/about.vue`
   - Plain HTML: `/about` → `public/about.html` or `about.html`
3. Use the `selector` and `html` fields to pinpoint the exact element. If the selector contains a class name, search for it: `grep -r "class-name" src/`

**Skip an issue and add it to the manual review list** if any of the following apply:
- The file path is inside `node_modules/`
- The URL contains a CDN domain (e.g. `cdn.`, `unpkg.com`, `jsdelivr.net`, `cdnjs`)
- The file is inside `dist/`, `build/`, `.next/`, `.nuxt/`, or has an auto-generated file comment
- No matching source file can be found after a thorough search

## Step 13: Remediate Issues (current chunk of up to 20)

For each mapped issue, read the source file and apply the fix based on `ruleId`. Always consult the `solutions[]` array and `needFixTitle` for guidance on the specific fix. Process in the priority order from Step 9.

If an issue cannot be auto-fixed (third-party component, architectural dependency, or insufficient context), add it to the **manual review list** and move on.

---

### Color Contrast (WCAG 1.4.3 / 1.4.11) — `color-contrast`

- Read the CSS or inline style for the flagged element's text color and background color
- Calculate the contrast ratio. Required: 4.5:1 for normal text, 3:1 for large text (18pt or 14pt bold) and UI components
- Adjust by darkening text color or lightening background (or vice versa), preserving the existing hue
- Update CSS custom properties (`--color-*`) at the `:root` level when the color is defined there
- Example: `color: #777777` on white background → `color: #595959` (achieves 7.0:1)
- Do not replace colors with arbitrary values — match the design's color palette

### Missing Alt Text (WCAG 1.1.1) — `image-alt`

- Find the `<img>` element using the `selector`
- **Decorative image** (background pattern, spacer, icon with adjacent visible label): add `alt=""` and optionally `role="presentation"`
- **Informative image**: add descriptive alt text using surrounding context (heading, caption, filename). Keep under 125 characters. Do not prefix with "image of" or "photo of"
- **Linked image** (`<a><img></a>`): alt text should describe the link destination, not the image appearance

### ARIA Labels (WCAG 4.1.2) — `aria-required-attr`, `aria-label`, `aria-labelledby`

- Find the interactive element (button, input, select, div with `role`) that has no accessible name
- **Prefer** adding a visible `<label>` or visible text content inside the element
- **Icon-only element** (no visible text): add `aria-label="descriptive text"` to the element
- **Visible label exists elsewhere on page**: add `aria-labelledby="id-of-label-element"` and ensure the label element has a matching `id`
- Do not add `aria-label` when the element already has a visible text label — that creates redundancy

### Form Labels (WCAG 1.3.1, 3.3.2) — `label`

- Find the `<input>`, `<select>`, or `<textarea>` without an associated `<label>`
- Add `<label for="input-id">Label text</label>` near the input, connecting via matching `for`/`id` attributes
- If the label must be visually hidden: use a `.sr-only` / `.visually-hidden` CSS class (not `display: none` or `visibility: hidden`, which hides from screen readers too)
- If no such class exists in the project, add it to the global stylesheet:

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

### Keyboard Navigation (WCAG 2.1.1, 2.4.3) — `keyboard`, `tabindex`

- `tabindex="-1"` on an interactive element that should be reachable → remove it or change to `tabindex="0"`
- Positive `tabindex` values (`tabindex="2"`, etc.) create unnatural focus order → remove all positive values and rely on DOM order
- `<div>` or `<span>` with a click handler but no keyboard handler → replace with a semantic `<button>` element, or add `onKeyDown`/`onKeyPress` handlers for `Enter` and `Space`
- Semantic replacement is preferred: `<div onClick>` → `<button>`, navigational elements → `<a href>`

### Link Name / Button Name (WCAG 4.1.2) — `link-name`, `button-name`

- Find the `<a>` or `<button>` with no accessible text (empty, or icon-only)
- **Icon-only with SVG**: add `aria-label="descriptive text"` to the element, or add a `<title>` inside the SVG plus `aria-labelledby="svg-title-id"` on the element
- **Generic link text** ("click here", "read more", "learn more"): replace with descriptive text, e.g. "Read more about {topic}" — infer the topic from the surrounding heading or section context
- **Linked image with no alt text**: ensure the `<img>` inside has descriptive alt text (see alt text rule)

### Document Title (WCAG 2.4.2) — `document-title`

- Find the `<title>` tag in the HTML `<head>`
- If missing: add `<title>{Page Name} | {Site Name}</title>` — infer page name from the `<h1>`, site name from other pages or `package.json#name`
- If present but generic ("Untitled", empty string, or duplicate across pages): write a unique, descriptive title for each page

### Heading Order (WCAG 1.3.1) — `heading-order`

- Identify skipped heading levels, e.g. `<h1>` directly followed by `<h3>` with no `<h2>` in between
- Correct the heading tag to the next sequential level
- If the visual styling must be preserved, restyle with CSS (`font-size`, `font-weight`) rather than altering the tag
- If the heading hierarchy is deeply structurally wrong (not a simple skip), add to the manual review list with an explanation

### Landmark Regions (WCAG 1.3.1) — `landmark-*`, `region`

- If the page has no `<main>` element: wrap the primary content in `<main>`
- If multiple `<nav>` elements exist without `aria-label`: add distinct labels, e.g. `aria-label="Primary navigation"` and `aria-label="Footer navigation"`
- If significant content exists outside any landmark region: wrap it in the appropriate element (`<main>`, `<aside>`, `<footer>`, `<header>`, `<section aria-label="...">`)

### Focus Visible (WCAG 2.4.7) — `focus-visible`

- Find CSS rules with `outline: none` or `outline: 0` on interactive elements (`:focus`, `:focus-visible`)
- Remove the suppression rule, or replace it with a visible custom focus style:

```css
:focus-visible {
  outline: 2px solid #005fcc;
  outline-offset: 2px;
}
```

Ensure the custom focus indicator has at least 3:1 contrast ratio against the adjacent background.

---

## Step 14: Build and Test

After applying fixes for the current chunk:

1. Run the build command for the detected package manager
2. If build fails:
   - Compare errors to known issues from the changes just made
   - Attempt to fix — up to 3 retries
   - If still failing after 3 attempts, stop and ask the user for help
3. Run the test suite
4. Compare failures to the baseline from Step 11
   - **New failure** (not in baseline): attempt to fix — up to 3 retries
   - **Pre-existing failure** (in baseline): note it in the PR, do not fix
5. Never modify test files — only fix source code

If build and tests pass (accounting for pre-existing failures), proceed to PR creation.

## Step 15: Create Pull Request

**Branch name**: `fix/aqa-accessibility-chunk-N-YYYY-MM-DD`
(where N is the chunk number, e.g. `fix/aqa-accessibility-chunk-1-2025-03-26`)

**Commit message** (conventional commits format):

```
fix(a11y): remediate UsableNet AQA violations — chunk N

- Fixed X color contrast issues (WCAG 1.4.3)
- Fixed Y missing alt text violations (WCAG 1.1.1)
- Fixed Z ARIA label issues (WCAG 4.1.2)
- Fixed W form label issues (WCAG 3.3.2)
- Fixed V keyboard navigation issues (WCAG 2.1.1)
Severity range: critical / serious
Suite: {suiteName} | Run: {runId}
```

**PR body**:

```markdown
## UsableNet AQA Accessibility Remediation — Chunk N of ~M

**Severity range fixed in this chunk:** critical → serious (issues 1–20 of {total} total)
**Suite:** {suiteName} (`{suiteId}`)
**Run ID:** `{runId}` | Completed: {timestamp}

### Summary

| Violation Type | Found in chunk | Fixed | Manual Action Needed |
|----------------|---------------|-------|---------------------|
| Color Contrast | X | X | 0 |
| Missing Alt Text | Y | Y | 0 |
| ARIA Labels | Z | Z | 0 |
| Form Labels | W | W | 0 |
| Keyboard Navigation | V | V | 0 |
| Other | U | U | U |

### Files Changed

- `src/components/Header.tsx` — Fixed color contrast on nav links: `#777777` → `#595959`
- `src/pages/about.html` — Added alt text to hero image
- `src/components/SearchBar.tsx` — Added `aria-label` to icon-only search button

### Manual Actions Required

- [ ] `{flowName}` / `{selector}` — {reason why auto-fix was skipped}
- [ ] `{flowName}` / `{selector}` — Third-party widget, vendor fix required

### Remaining Violations

**{total - 20}** violations remain after this chunk. Re-run `/aqa-usablenet` to fix the next chunk.

### Build & Test

- Build: ✅ PASSING
- Tests: ✅ PASSING
- Pre-existing failures (not caused by this run, do not review): `{list}`
```
