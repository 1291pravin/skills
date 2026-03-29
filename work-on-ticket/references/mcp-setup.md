# MCP Server Configuration for work-on-ticket

This guide explains how to set up MCP (Model Context Protocol) servers used by the work-on-ticket skill to fetch Figma design specs and Shopify developer documentation.

## Figma MCP Server

The Figma MCP server connects to the Figma API and provides design spec data directly to Claude Code — component properties, colors, spacing, typography, and auto-layout details.

### Getting a Figma Access Token

1. Open Figma and go to **Account Settings**.
2. Scroll to **Personal access tokens**.
3. Click **Generate new token**, give it a name, and copy the token.
4. Export it as an environment variable:
   ```bash
   export FIGMA_ACCESS_TOKEN="your-figma-token"
   ```

### What It Provides

- Component properties and variants
- Fill and stroke colors (hex, RGBA)
- Padding, spacing, and gap values
- Typography: font family, size, weight, line-height, letter-spacing
- Auto-layout direction, alignment, and constraints
- Export settings and asset URLs

## Shopify Dev MCP (shopify-dev-mcp)

The shopify-dev-mcp server provides access to Shopify's public developer documentation. No API key is required.

### What It Provides

- Liquid reference (filters, tags, objects)
- Section and block schema documentation
- Theme architecture (layouts, templates, snippets, assets)
- Storefront API and AJAX API references
- Metafield and metaobject documentation
- Shopify Functions and checkout extensibility docs

## Configuration

Add both servers to your Claude Code MCP configuration file (`.claude/mcp.json` in your project root or `~/.claude/mcp.json` globally):

```json
{
  "mcpServers": {
    "figma": {
      "command": "npx",
      "args": ["-y", "figma-developer-mcp"],
      "env": {
        "FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"
      }
    },
    "shopify-dev-mcp": {
      "command": "npx",
      "args": ["-y", "shopify-dev-mcp"]
    }
  }
}
```

### Verifying the Setup

After adding the configuration, restart Claude Code. You can verify MCP servers are connected by checking the tool list — Figma and Shopify documentation tools should appear.

If a server fails to start, check:

1. **Node.js** is installed and `npx` is on your PATH.
2. **FIGMA_ACCESS_TOKEN** is exported in your shell profile (for the Figma server).
3. Network access is available (both servers fetch data over HTTPS).

## Notes

- The Figma server requires a valid access token. Free Figma accounts have API access.
- The Shopify dev MCP server uses public documentation and does not require authentication.
- Both servers run locally as child processes managed by Claude Code. They do not persist after the session ends.
- To disable a server temporarily, remove or comment out its entry in `mcp.json`.
