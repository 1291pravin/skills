---
name: skill-creator
description: >
  Create, test, and iteratively improve AI skills (SKILL.md files) for any
  AI-assisted IDE — Claude Code, Windsurf, Cursor, or others. Guides you
  through the full lifecycle: interview, draft, test, review, and refine.
  Use this skill whenever the user wants to create a new skill, improve an
  existing skill, write a SKILL.md, build an automation workflow, or turn a
  manual process into a reusable skill — even if they don't explicitly say
  "skill-creator".
---

# Skill Creator

Create, test, and iterate on AI skills that work across any AI-assisted IDE (Claude Code, Windsurf, Cursor, etc.). Skills are reusable instruction sets stored as `SKILL.md` files that teach the AI assistant how to perform specific workflows.

## How Skills Work

A skill is a markdown file (`SKILL.md`) with YAML frontmatter that tells an AI assistant **when** to activate and **what** to do. The format is IDE-agnostic — any AI assistant that reads markdown instructions can use it. See `references/skill-anatomy.md` for the full format reference.

---

## Phase 1: Capture Intent

Start by understanding what the user wants to automate. If the current conversation already contains a workflow (e.g., the user says "turn this into a skill"), extract what you can from conversation history first — tools used, sequence of steps, corrections made, input/output formats. Then confirm and fill gaps.

Ask these questions (skip any already answered by context):

1. **What should this skill do?** — The core workflow in plain language.
2. **When should it trigger?** — What phrases or contexts should activate it?
3. **What's the expected output?** — Files created, APIs called, PRs opened, etc.
4. **What tools/APIs does it need?** — REST APIs, CLIs, file operations, etc.
5. **Should we test it?** — Skills with objectively verifiable outputs (file transforms, API calls, code changes) benefit from test cases. Subjective skills (writing, design) usually don't. Suggest the right default but let the user decide.

### Research Phase

Before drafting, do your homework:

- Check if a similar skill already exists in the project — read existing `SKILL.md` files for patterns and conventions
- If the skill involves an API, look up the API docs (use context7 MCP if available, or web search)
- If the skill involves a CLI tool, verify it exists and check its flags
- Come prepared so the user doesn't have to explain things you could have looked up

---

## Phase 2: Draft the SKILL.md

Based on the interview, write the skill following these conventions:

### Frontmatter

```yaml
---
name: skill-name
description: >
  2-3 sentences covering: what the skill does, what it handles,
  and what phrases/contexts should trigger it. End with trigger
  language like "even if they don't explicitly say 'skill-name'".
---
```

The `description` is the primary triggering mechanism — it determines whether the AI activates the skill. Make it slightly "pushy" to avoid under-triggering. Include both what the skill does AND specific contexts for when to use it.

### Body Structure

Follow the conventions established in this project:

1. **Title** — `# <Service/Domain> <Workflow Type>`
2. **Intro** — 1-2 sentences summarizing the workflow
3. **Numbered steps** — Sequential workflow sections (`## Step 1: ...`, `## Step 2: ...`)

### Writing Principles

- **Explain the why, not just the what.** AI assistants are smart — when they understand *why* a step matters, they handle edge cases better than rigid MUST/NEVER rules. If you catch yourself writing ALL CAPS directives, reframe as reasoning instead.
- **Prefer REST APIs over CLIs** when possible (project convention). CLIs can be fallbacks.
- **Make skills idempotent** — safe to re-run without side effects.
- **Keep it focused** — single responsibility per skill.
- **Use imperative form** — "Run the scan", "Create a PR", not "You should run the scan".
- **Include platform detection** — Handle macOS/Linux vs Windows differences where relevant.
- **Protect secrets** — Never print tokens, always use environment variables, warn about `.gitignore`.

### Progressive Disclosure

Keep the main `SKILL.md` under 500 lines. If the skill is complex:

```
skill-name/
├── SKILL.md              (main workflow, <500 lines)
├── references/           (detailed docs, loaded on demand)
│   ├── api-reference.md  (full API schema)
│   └── config-guide.md   (configuration details)
├── scripts/              (helper scripts for deterministic tasks)
└── assets/               (templates, icons, etc.)
```

Reference files clearly from SKILL.md with guidance on when to read them:
> "For the full API schema, read `references/api-reference.md`."

### Examples in Skills

Include concrete examples to reduce ambiguity:

```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication

**Example 2:**
Input: Fixed crash when uploading empty files
Output: fix(upload): handle empty file edge case
```

---

## Phase 3: Test the Skill

After drafting, create 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user for confirmation before running.

### Writing Test Prompts

Good test prompts are:
- **Realistic** — what a developer would actually type, with context, typos, casual language
- **Varied** — different phrasings, different levels of detail, different sub-workflows
- **Edge-case-aware** — at least one prompt should test a non-obvious scenario

Bad: `"Fix the security issue"`
Good: `"hey there's an apiiro alert on the dashboard for our checkout repo, something about a vulnerable lodash version in package.json, can you take care of it?"`

### Save Test Cases

Save to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "The realistic user prompt",
      "expected_output": "Description of what a good result looks like",
      "files": []
    }
  ]
}
```

### Running Tests

How you run tests depends on your environment:

**Option A: Manual testing (works everywhere)**
1. Open a new AI chat session in your IDE
2. Make sure the skill is accessible (in the skills directory)
3. Paste each test prompt and observe the result
4. Note what worked and what didn't

**Option B: Script-assisted testing (if Python available)**
Run `scripts/eval_runner.py` to automate test execution:
```bash
python skill-creator/scripts/eval_runner.py \
  --skill-path <path-to-skill>/SKILL.md \
  --evals <path-to-skill>/evals/evals.json \
  --output <workspace>/iteration-1/
```

This captures outputs in a structured directory for review.

**Option C: Side-by-side comparison**
For each test prompt, run it twice — once with the skill available, once without. Compare the results to see if the skill actually improves the output. Save results in:
```
<skill-name>-workspace/
└── iteration-1/
    ├── eval-1/
    │   ├── with_skill/
    │   └── without_skill/
    └── eval-2/
        ├── with_skill/
        └── without_skill/
```

---

## Phase 4: Review and Iterate

Present the test results to the user and get feedback. For each test case, show:
- The prompt that was used
- What the skill produced
- What (if anything) went wrong

### Improving the Skill

When incorporating feedback:

1. **Generalize, don't overfit.** The skill will be used across many prompts, not just these test cases. If a fix only helps one specific test, it's probably too narrow. Look for the underlying pattern.

2. **Keep it lean.** Remove instructions that aren't pulling their weight. If the AI is wasting time on unproductive steps, trim those instructions.

3. **Explain the reasoning.** Instead of adding rigid rules (ALWAYS do X, NEVER do Y), explain *why* something matters. This produces better results across diverse inputs.

4. **Bundle repeated work.** If every test run independently creates the same helper script or takes the same multi-step approach, that's a signal to bundle it. Write it once in `scripts/` and reference it from the skill.

### The Iteration Loop

1. Apply improvements to the SKILL.md
2. Re-run all test prompts
3. Show results to the user
4. Read feedback, improve again
5. Repeat until:
   - The user is happy
   - All feedback is positive
   - Improvements are marginal

---

## Phase 5: Optimize Description (Optional)

The `description` field is what determines whether the AI activates the skill. To optimize it:

### Create Trigger Test Queries

Write 16-20 test queries — a mix of should-trigger (8-10) and should-not-trigger (8-10):

**Should-trigger queries** — different phrasings of the same intent:
- Formal and casual versions
- Cases where the user doesn't name the skill explicitly but clearly needs it
- Uncommon use cases and edge cases

**Should-not-trigger queries** — near-misses that share keywords but need something different:
- Adjacent domains with overlapping terminology
- Ambiguous phrasing where naive keyword matching would wrongly trigger
- Queries that touch on the skill's domain but in wrong context

Bad negative: `"Write a fibonacci function"` (too obviously irrelevant)
Good negative: `"I need to update the package.json version field to match our release tag"` (shares keywords with a security/dependency skill but is a different task)

### Test and Refine

For each query, check if the skill triggers as expected. Adjust the description wording until trigger accuracy is high. The key insight: AI assistants only consult skills for tasks they can't easily handle alone — simple one-step queries may not trigger any skill regardless of description quality.

---

## IDE-Specific Notes

### Windsurf (Cascade)
- Skills are loaded from the project's skill directories
- Cascade reads SKILL.md files and uses the description for triggering
- Test by starting a new Cascade chat and trying your test prompts
- No subagent support — test prompts must be run one at a time

### Claude Code
- Skills live in `.claude/plugins/` or project directories
- Supports subagents for parallel test execution
- Can use `claude -p` for automated eval runs if available
- Supports `.skill` packaging for distribution

### Cursor
- Skills can be referenced via `.cursorrules` or project docs
- Test by opening Composer and trying your test prompts
- No native skill format — SKILL.md serves as instruction context

### General
- The SKILL.md format works in any AI IDE that reads markdown context
- The workflow (interview → draft → test → iterate) is universal
- Adjust the testing approach based on what your IDE supports
