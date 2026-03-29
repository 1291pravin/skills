# Skill Anatomy Reference

Complete reference for the SKILL.md format used across this project.

## Table of Contents
1. [Directory Structure](#directory-structure)
2. [Frontmatter Schema](#frontmatter-schema)
3. [Body Conventions](#body-conventions)
4. [Progressive Disclosure](#progressive-disclosure)
5. [Common Patterns](#common-patterns)
6. [Eval Schema](#eval-schema)

---

## Directory Structure

### Minimal (most skills)
```
skill-name/
└── SKILL.md
```

### Extended (complex skills)
```
skill-name/
├── SKILL.md              # Required — main workflow instructions
├── references/           # Optional — detailed docs loaded on demand
│   ├── api-reference.md  # Full API schema
│   └── config-guide.md   # Configuration details
├── scripts/              # Optional — helper scripts for deterministic tasks
│   └── helper.py
├── assets/               # Optional — templates, icons, fonts
│   └── template.html
└── evals/                # Optional — test cases
    └── evals.json
```

### Key rules
- `SKILL.md` is the only required file
- Scripts in `scripts/` can be executed without loading into context
- Reference files should be read only when needed (pointed to from SKILL.md)
- For large reference files (>300 lines), include a table of contents

---

## Frontmatter Schema

```yaml
---
name: skill-name           # Required — matches directory name
description: >             # Required — triggers skill activation
  What the skill does, what it handles, and when to use it.
  Include natural language triggers. End with "even if they
  don't explicitly say 'skill-name'".
---
```

### Name
- Must match the directory name (e.g., `apiiro-fix/` → `name: apiiro-fix`)
- Use kebab-case: `my-skill-name`

### Description
The description serves dual purpose:
1. **Human-readable** — tells developers what the skill does
2. **AI-triggering** — the AI reads this to decide whether to activate the skill

Write it to be slightly "pushy" — AI assistants tend to under-trigger rather than over-trigger. Include:
- What the skill does (1 sentence)
- What it handles (scope/domains)
- Key capabilities (chunking, resumption, etc.)
- Trigger phrases — what user language should activate this

**Example:**
```yaml
description: >
  Fetch and fix Apiiro security findings for the current repository.
  Handles SCA (vulnerable packages), SAST (code vulnerabilities), secrets
  exposure, misconfigurations, PII detection, and supply chain issues.
  Use this skill whenever the user mentions Apiiro, security alerts,
  vulnerability remediation, or dependency updates for security, even if
  they don't explicitly say "apiiro-fix".
```

---

## Body Conventions

### Structure
```markdown
# <Service/Domain> <Workflow Type>

<1-2 sentence intro summarizing the full workflow>

## Step 1: <First Action>
<Instructions>

## Step 2: <Second Action>
<Instructions>

...
```

### Writing style
- **Imperative form**: "Run the scan", "Create a PR" (not "You should run")
- **Explain the why**: Reasoning produces better AI behavior than rigid rules
- **Platform-aware**: Handle macOS/Linux vs Windows differences
- **Security-conscious**: Never print tokens, use env vars, warn about .gitignore

### Condition checks
```markdown
## Step 1: Check & Install CLI

Run `tool --version` to check if installed.

**If not installed:**
1. **macOS / Linux**: Run `brew install tool`
2. **Windows**: Tell the user:
   > Tool is not installed. Download from https://example.com
   > Once installed, let me know and I'll continue.
```

### User-facing instructions
Use blockquotes when the user needs to take action:
```markdown
> Please set your API key: `export API_KEY=your-key-here`
> Once done, let me know and I'll continue.
```

---

## Progressive Disclosure

Three levels of loading:

| Level | What | Size | When loaded |
|-------|------|------|-------------|
| Metadata | name + description | ~100 words | Always in context |
| SKILL.md body | Full instructions | <500 lines | When skill triggers |
| Bundled resources | References, scripts | Unlimited | On demand |

### When to split into references
- SKILL.md approaching 500 lines
- Multiple domains/frameworks (one reference per variant)
- Large API schemas or configuration docs
- Content only needed for specific sub-workflows

### Domain organization
```
cloud-deploy/
├── SKILL.md              # Workflow + selection logic
└── references/
    ├── aws.md            # AWS-specific details
    ├── gcp.md            # GCP-specific details
    └── azure.md          # Azure-specific details
```

The AI reads only the relevant reference file based on context.

---

## Common Patterns

### Environment variable validation
Collect ALL missing variables at once (don't stop at the first one):
```markdown
Check for required environment variables:
- `API_KEY` — your API authentication key
- `TEAM_SLUG` — your team identifier

If any are missing, list all missing variables together with copy-paste export commands.
```

### Package manager detection
```markdown
Detect the package manager:
1. Check `packageManager` field in `package.json`
2. Check for lock files: `package-lock.json` → npm, `yarn.lock` → yarn, `pnpm-lock.yaml` → pnpm
3. If unclear, ask the user
```

### Chunking and resumption
```markdown
Process up to 20 findings per run. Create a focused PR per chunk.
Track progress in `<workspace>/progress.json` so the next run resumes
where the last session left off.
```

### Baseline snapshots
```markdown
Before making changes:
1. Run the test suite and save the snapshot
2. Record current state (findings count, error count, etc.)

After changes:
1. Re-run the same tests
2. Compare against baseline to verify improvements and catch regressions
```

---

## Eval Schema

### evals.json
```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Realistic user prompt with context and detail",
      "expected_output": "Description of what a good result looks like",
      "files": ["optional/input/files.txt"],
      "assertions": [
        {
          "name": "descriptive-assertion-name",
          "type": "file_exists | content_contains | api_called | custom",
          "check": "What to verify",
          "target": "path/or/value"
        }
      ]
    }
  ]
}
```

### Assertion types
- **file_exists** — Check that an output file was created
- **content_contains** — Check that output contains specific content
- **api_called** — Verify an API endpoint was hit
- **custom** — Free-form check described in `check` field

### Results structure
```
skill-name-workspace/
└── iteration-1/
    ├── eval-1-descriptive-name/
    │   ├── with_skill/
    │   │   └── outputs/
    │   ├── without_skill/
    │   │   └── outputs/
    │   └── eval_metadata.json
    ├── eval-2-another-test/
    │   └── ...
    └── benchmark.json
```
