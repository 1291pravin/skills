---
name: figma-prompt
description: "Capture Figma designs as screenshots and structured design info for developers. Use this skill whenever a developer is working with Figma — e.g., they share a Figma URL, ask to see a design, want design specs, need a screenshot of a component, want to understand a Figma layout, or need design context while coding. Also trigger for: 'capture this Figma', 'show me the design', 'grab the Figma', 'what does this component look like', 'get design info', or any mention of Figma URLs during development work."
---

# figma-prompt CLI Skill

Developers often need quick access to Figma design details — screenshots, layout info, typography, colors, spacing — without switching context or needing Figma Dev Mode. This skill runs the `figma-prompt` CLI to fetch that info directly into the project as a structured prompt + screenshot, so the developer (or an AI tool) can reference the design while coding. Only requires a free Figma PAT with `file_content:read` scope.

The CLI lives at `C:\Projects\figma_to_code` and must be invoked from there (or via the built binary).

## PAT Resolution (do this FIRST for any capture command)

Before running any `capture` command, resolve the Figma Personal Access Token in this order:

1. **Check `.env` file** in the project root for `FIGMA_PAT` or `TOKEN`:
   ```bash
   grep -E '^(FIGMA_PAT|TOKEN)=' .env 2>/dev/null
   ```
2. **Check environment variable** `FIGMA_PAT`:
   ```bash
   echo $FIGMA_PAT
   ```
3. **If neither exists**, guide the user through setup:
   - Tell them: "You need a Figma Personal Access Token to capture designs."
   - Steps to get one:
     1. Go to Figma → Settings → Account → Personal Access Tokens
     2. Click "Generate new token"
     3. Give it a name (e.g., "figma-prompt")
     4. Under Scopes, enable **File content → Read-only** (`file_content:read`)
     5. Copy the token (starts with `figd_`)
   - Then save it:
     ```bash
     echo "FIGMA_PAT=<their-token>" >> .env
     ```
   - Also remind them to ensure `.env` is in `.gitignore` to avoid leaking the token.
   - Do NOT proceed with the capture until the PAT is available.

When you have the token value (from `FIGMA_PAT` or `TOKEN` in `.env`), export it before running CLI commands:
```bash
export FIGMA_PAT=<resolved-value>
```

## Available Commands

All commands run from the project root via `npm run cli --` (dev mode) or `npx figma-prompt` (if built).

### Initialize `.design/` directory
```bash
npm run cli -- init
```
Creates the `.design/` folder structure (`screenshots/`, `prompts/`, `manifest.json`). Run this once before the first capture.

### Capture a Figma design
```bash
npm run cli -- capture "<figma-url>" --pat "$FIGMA_PAT"
```

Options:
| Flag | Description | Example |
|------|-------------|---------|
| `--pat <token>` | Figma PAT (auto-resolved from .env if you export it) | `--pat figd_xxx` |
| `--output <dir>` | Output directory (default: `.design` in cwd) | `--output ./designs` |
| `--framework <fw>` | Target framework: `react`, `vue`, `html` | `--framework react` |
| `--styling <s>` | Styling approach: `tailwind`, `css-modules`, `plain-css` | `--styling tailwind` |
| `--language <l>` | Language: `typescript`, `javascript` | `--language typescript` |
| `--name <name>` | Override component name (single URL only) | `--name MyButton` |

Multiple URLs can be captured in one command:
```bash
npm run cli -- capture "<url1>" "<url2>" "<url3>" --pat "$FIGMA_PAT"
```

Framework, styling, and language are auto-detected from the project if not specified.

### List captures
```bash
npm run cli -- list
```
Shows all captured designs with their Figma URLs, dates, and file paths.

### Delete a capture
```bash
npm run cli -- delete <name>
```
Removes a capture by its component name.

### Detect project settings
```bash
npm run cli -- detect
```
Shows auto-detected framework, styling, and language for the current project.

## Workflow

A typical capture workflow:

1. **Init** (first time only): `npm run cli -- init`
2. **Resolve PAT** from `.env` or guide the user to create one
3. **Capture**: Export `FIGMA_PAT` and run `npm run cli -- capture "<url>"`
4. **Review**: Check the generated prompt in `.design/prompts/<name>.md` and screenshot in `.design/screenshots/<name>.png`
5. **Use**: The generated prompt + screenshot can be fed into any AI coding tool

## Troubleshooting

- **"Figma PAT required" error**: The PAT wasn't found. Check `.env` for `FIGMA_PAT` or `TOKEN`, or pass `--pat` directly.
- **Invalid URL**: The Figma URL must point to a specific node. It should contain a `node-id` parameter (e.g., `?node-id=1:234`).
- **403 from Figma API**: The PAT may lack the `file_content:read` scope, or it may have expired. Regenerate it in Figma settings.
