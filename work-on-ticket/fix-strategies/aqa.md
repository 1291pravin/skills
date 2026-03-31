# Fix Strategy: AQA Accessibility Violations

This strategy is loaded by `/work-on-ticket` when the ticket has the `aqa` label. It contains the remediation logic for UsableNet AQA accessibility violations.

## Parse Ticket Description

Extract the issue list from the ticket description. Look for the `{code:json}` block containing an array of issues. Each issue has:

- `ruleId` — e.g., `color-contrast`, `image-alt`, `label`
- `impact` — critical, serious, moderate, minor
- `wcagCriteria` — e.g., `["1.4.3"]`
- `needFixTitle` — human-readable description of what needs fixing
- `selectors` — CSS selectors identifying the element
- `tagName` — HTML tag name
- `html` — the offending HTML snippet
- `flowId` — AQA flow ID
- `flowUrl` — URL of the page where the issue was found
- `solutions` — array of suggested fixes

If the structured data cannot be parsed, tell the user:
> The ticket description doesn't contain parseable issue data. Please re-run `/triage-aqa` to create a fresh ticket.

## Map Issues to Source Files

For each issue, map it to a source file in the repository:

1. Use the `flowUrl` to determine which template/page the issue is on
2. Match URL patterns to source files:
   - `/products/*` → `templates/product.liquid` or `sections/product-*.liquid`
   - `/collections/*` → `templates/collection.liquid` or `sections/collection-*.liquid`
   - `/cart` → `templates/cart.liquid` or `sections/cart-*.liquid`
   - `/pages/*` → `templates/page.liquid`
   - `/` → `templates/index.liquid` or `sections/hero-*.liquid`
3. Use the CSS `selectors` and `html` snippet to find the exact element in the source file
4. If the element is in a shared component (header, footer, snippets), check `sections/header.liquid`, `sections/footer.liquid`, `snippets/*.liquid`

Skip files in `node_modules/`, `dist/`, `build/`, `.next/`, `.nuxt/`, CDN resources, or auto-generated files. Add these to a manual review list.

## Detect Package Manager

Refer to `../../references/package-manager-detection.md` for detection logic.

## Remediation Guidance

Process issues in severity order (critical → serious → moderate → minor). Always consult the issue's `solutions[]` array and `needFixTitle` for specific guidance.

| Rule ID | WCAG | Fix Approach |
|---------|------|-------------|
| `color-contrast` | 1.4.3/1.4.11 | Adjust text/background colors to meet 4.5:1 (normal) or 3:1 (large text). Preserve hue, update CSS custom properties at `:root` when applicable. |
| `image-alt` | 1.1.1 | Decorative: `alt=""` + `role="presentation"`. Informative: descriptive alt under 125 chars. Linked: describe destination. |
| `aria-required-attr`, `aria-label` | 4.1.2 | Prefer visible `<label>` or text content. Icon-only: add `aria-label`. Label elsewhere: use `aria-labelledby`. |
| `label` | 1.3.1/3.3.2 | Add `<label for="id">`. Visually hidden: use `.sr-only` class (not `display:none`). |
| `keyboard`, `tabindex` | 2.1.1/2.4.3 | Replace `<div onClick>` with `<button>`. Remove positive `tabindex`. Remove `tabindex="-1"` on interactive elements. |
| `link-name`, `button-name` | 4.1.2 | Icon-only SVG: add `aria-label` or `<title>`. Generic text: make descriptive. |
| `document-title` | 2.4.2 | Add/fix `<title>{Page} \| {Site}</title>` in `<head>`. |
| `heading-order` | 1.3.1 | Fix skipped levels. Restyle with CSS if visual change isn't desired. |
| `landmark-*`, `region` | 1.3.1 | Wrap content in `<main>`, label multiple `<nav>` elements. |
| `focus-visible` | 2.4.7 | Remove `outline:none` on `:focus`. Add visible `:focus-visible` style with 3:1 contrast. |

## Build & Test Verification

After all remediations:

1. **Build** the project using the detected package manager
2. Run `shopify theme check` if Shopify CLI is available — fix any errors
3. **Test** if a test script exists
4. Compare results against baseline:
   - **New failures** → fix and retry (max 3 attempts)
   - **Pre-existing failures** → do NOT touch
   - **Never modify tests** to make them pass
5. If a new failure cannot be resolved after 3 attempts, stop and ask the user for help
