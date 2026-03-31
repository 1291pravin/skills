# Fix Strategy: Default (Feature / General Ticket)

This strategy is loaded by `/work-on-ticket` when the ticket has no specialized labels (apiiro, aqa, sonarqube, errors). It implements changes based on the ticket's acceptance criteria using all available context.

## Fetch Design Specs (Optional — MCP)

Check if the **Figma MCP server** is available.

**If available:**

1. Scan the ticket description and attachments for Figma URLs (e.g. `https://www.figma.com/file/...` or `https://www.figma.com/design/...`)
2. Use the Figma MCP to fetch design specs:
   - Component properties and variants
   - Colors (hex values, design tokens)
   - Spacing and padding values
   - Typography (font family, size, weight, line-height)
   - Auto-layout and responsive behavior
3. Store the extracted specs for use during implementation.

**If not available:**

Skip and print:
> Tip: Configure the Figma MCP server for automatic design spec fetching. See `../references/mcp-setup.md`

## Fetch Shopify Documentation (Optional — MCP)

Check if the **shopify-dev-mcp** server is available.

**If available:**

Based on the ticket context, determine relevant Shopify topics and fetch documentation:

- **Liquid templates** — if the ticket involves template changes
- **Section schema** — if building or modifying sections
- **Metafields** — if the ticket references custom data
- **Cart API / AJAX API** — if cart functionality is involved
- **Theme architecture** — for structural changes (layouts, templates, snippets)
- **Shopify Functions / Extensions** — if extending checkout or storefront

**If not available:**

Skip and print:
> Tip: Configure the shopify-dev-mcp server for automatic Shopify documentation fetching. See `../references/mcp-setup.md`

## Implement Changes

Use all gathered context to implement the ticket:

- **Jira details** — summary, description, acceptance criteria
- **Figma specs** (if fetched) — colors, spacing, typography, component structure
- **Shopify docs** (if fetched) — correct Liquid syntax, section schema patterns, API usage

Follow Shopify theme development best practices:

- Use **Liquid** for templates and rendering logic
- Build reusable **sections** and **snippets**
- Define settings via **settings_schema** with proper types and defaults
- For JavaScript: follow existing patterns in the codebase (check `assets/` for conventions)
- Keep CSS scoped to the component or section
- Use semantic HTML and ensure accessibility (ARIA attributes, alt text)

Work through each acceptance criterion. After implementing, review the diff to verify nothing was missed.

## Build & Test Verification

Refer to `../../references/package-manager-detection.md` for detection logic.

1. Install dependencies if needed
2. Run the build command
3. Run `shopify theme check` if the Shopify CLI is available — fix any errors or warnings
4. Run tests if a test script exists
5. Compare results against baseline. If there are regressions:
   - Attempt to fix the issue
   - Re-run build and tests
   - Retry up to **3 attempts**. If regressions persist, stop and report to the developer
