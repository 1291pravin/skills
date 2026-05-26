---
name: factory-reviewer
description: >-
  Factory pipeline phase 6. Reviews the current task's diff against spec.md + tasks.json
  expectations. Wraps the built-in `review` and `simplify` skills, plus does
  factory-specific checks: scope creep, AC alignment, code-style drift. Writes
  `review.md` with severity-tagged findings. Blocks pipeline on any `blocking` finding.
  Only invoked inside the autonomous `factory` pipeline.
---

# factory-reviewer

Phase 6 (per-task). Review the diff produced by `factory-coder` before security audit.

## Inputs

- `.factory/state.json` — `current_task_id`
- `.factory/artifacts/task-<id>/code.diff`
- `.factory/spec.md`, `.factory/tasks.json` (current task)
- Repo

## Output

- `.factory/artifacts/task-<id>/review.md`
- update state: task `status = "reviewed"`, advance `phase = "security"` if no blockers; else `phase = "code"` (loop back with feedback) or `"blocked"`.

## Steps

1. **Refuse if wrong phase.** If `phase != "review"`, exit.
2. **Read diff.** Load `code.diff`. Also `git diff` to catch anything not staged.
3. **Invoke `review` skill** (built-in PR review):
   ```
   Skill(skill: "review", args: "review uncommitted changes in scope of task <id>")
   ```
4. **Invoke `simplify` skill** for code-quality pass:
   ```
   Skill(skill: "simplify", args: "review changed files for reuse and dead code")
   ```
5. **Factory-specific checks** (do these yourself, not via subskill):
   - **Scope:** all changed files must be in `task.files`. Files outside the list = scope creep finding (severity: `medium`).
   - **AC alignment:** the diff must plausibly satisfy `task.acceptance_refs`. If a referenced AC's behavior isn't implemented, severity `blocking`.
   - **Style drift:** code style differs from neighboring files (imports order, naming, default exports). Severity: `low`.
   - **Comments:** added comments that just describe WHAT the code does → flag for removal (`low`).
   - **Dead code:** unused exports, unreferenced helpers (`low`).
   - **Error handling:** caught errors that swallow info, fallbacks added "just in case" (`medium`).
   - **Doc currency:** if code uses a lib API not in spec's `docs_consulted`, ask coder to call `find-docs` and verify; severity `medium`.
6. **Aggregate.** Merge findings from both skills + factory checks. Dedupe by file:line.
7. **Decision rule:**
   - Any `blocking` → set `task.status = "in_progress"`, `task.blocker = "review: <summary>"`, increment retries, route back to coder (`phase = "code"`). If over retry budget: `phase = "blocked"`.
   - Any `medium` finding > 3 → also route back; quality is sliding.
   - Otherwise → `task.status = "reviewed"`, `phase = "security"`.
8. **Write report.**
9. **Log + return.**

## review.md template

```markdown
# Review — task <id>: <title>

**Diff:** [.factory/artifacts/task-<id>/code.diff](./code.diff)
**Files changed:** <N>
**Findings:** <B blocking> · <M medium> · <L low>

## Findings
| Severity | File:Line | Issue | Fix |
|---|---|---|---|
| blocking | server/api/orders.post.ts:24 | AC2 says 409 on conflict; route returns 500 | Catch unique constraint error, return 409 |
| medium | server/api/orders.post.ts:5 | Imports `lodash` — not in package.json, not in spec | Use native or add to deps via spec amendment |
| low | server/api/orders.post.ts:12 | Comment restates code | Remove |

## Subskill reports
- `review`: <one-line summary>
- `simplify`: <one-line summary>

## Decision
<route back to code | proceed to security | escalate>
```

## Severity definitions

- **blocking** — violates AC, breaks an existing test, security smell, or scope-violates the task contract.
- **medium** — quality/maintainability issue that should be fixed before merge.
- **low** — nit; don't fail the build but record it.

## Anti-patterns

- Don't flag a finding without a concrete fix.
- Don't propose refactors unrelated to this task (logged as future task, not as a finding here).
- Don't loop on the same `blocking` finding more than the retry budget — escalate.
- Don't approve a diff with TODO / FIXME / `as any` introduced — flag every one.

## Calling other skills

Note: `review` is the built-in slash command; it expects a target. `simplify` is the user-installed quality skill. Both run on the working tree, so we pass through what's currently uncommitted. Cap subskill invocations at 2 per task to control cost.
