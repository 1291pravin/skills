---
name: factory-security
description: >-
  Factory pipeline phase 7. Runs a security audit on the current task's diff by invoking
  the built-in `security-review` skill, then adds factory-specific gates (secrets check,
  authz check against spec, input validation). Writes `security.md`. HIGH severity
  blocks the pipeline; MED is noted; LOW is logged. Only invoked inside the autonomous
  `factory` pipeline.
---

# factory-security

Phase 7 (per-task). Security audit before the task is marked done.

## Inputs

- `.factory/state.json` — `current_task_id`
- `.factory/artifacts/task-<id>/code.diff`
- `.factory/spec.md` (for declared auth/data-classification requirements)
- Repo

## Output

- `.factory/artifacts/task-<id>/security.md`
- update state: task `status = "done"` (if clean or low only), advance pipeline to next task. On MED → note + advance. On HIGH → `phase = "blocked"`, `human_gate_pending = true`.

## Steps

1. **Refuse if wrong phase.** If `phase != "security"`, exit.
2. **Invoke `security-review`** (built-in slash command):
   ```
   Skill(skill: "security-review", args: "scan diff for task <id>")
   ```
3. **Factory-specific checks:**
   - **Secrets:** scan diff for keys matching `(api_key|secret|token|password|bearer|AKIA[0-9A-Z]{16})` — anything outside `.env.example`. HIGH.
   - **Authz:** if spec declared `auth: required (role: X)`, the route must enforce it. Read the diff for an auth check. Missing = HIGH.
   - **Input validation:** server routes must validate inputs (Zod or stack equivalent). Unvalidated `req.body` reads = MED.
   - **SQL injection:** string-interpolated SQL queries → HIGH. Parameterized only.
   - **XSS:** `v-html`, `dangerouslySetInnerHTML` with user content → HIGH.
   - **Open redirect:** redirects using unvalidated input → MED.
   - **CSRF:** state-changing API routes without CSRF token (when cookies-based auth) → MED.
   - **Logging:** PII / secrets being logged → HIGH.
   - **Dep additions:** new packages added to package.json — flag for human review of trust (MED unless from a known-trusted org).
4. **Aggregate.** Merge subskill output + factory checks. Dedupe.
5. **Decision:**
   - Any HIGH → `phase = "blocked"`, `human_gate_pending = true`, surface to user. Task stays `reviewed`, do NOT mark `done`.
   - Only MED/LOW → task `status = "done"`. Advance: next ready task in DAG becomes `current_task_id`, `phase = "code"`. If no more tasks, `phase = "done"`.
6. **Write report.**
7. **Log + return.**

## security.md template

```markdown
# Security audit — task <id>: <title>

**Diff:** [.factory/artifacts/task-<id>/code.diff](./code.diff)
**Findings:** <H HIGH> · <M MED> · <L LOW>

## Findings
| Severity | File:Line | CWE | Issue | Fix |
|---|---|---|---|---|
| HIGH | server/api/orders.post.ts:34 | CWE-89 | String-interpolated SQL: `db.prepare(`...${userId}...`)` | Use parameterized: `db.prepare('... ?').bind(userId)` |
| MED | server/api/orders.post.ts:18 | CWE-20 | `body.amount` not validated | Add Zod schema, reject if missing |

## Subskill report
- `security-review`: <summary>

## Decision
<advance | block (HIGH found)>
```

## Anti-patterns

- Don't dismiss HIGH because "it's just dev code". Production faithfulness from day 1.
- Don't aggregate two HIGHs into a "general issue" finding. One row per issue.
- Don't pass a task with new deps from unknown authors silently.
- Don't accept "I'll add validation later" — block now.

## What this skill does NOT do

- Does NOT run SAST tools (CodeQL/Semgrep). MVP relies on built-in `security-review` + heuristics. Add a `factory-sast` skill later.
- Does NOT scan deps for CVEs (use `npm audit` / `pnpm audit` in a separate pass).
- Does NOT do threat modeling — that belongs in spec phase.
