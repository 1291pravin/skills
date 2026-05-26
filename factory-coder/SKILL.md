---
name: factory-coder
description: >-
  Factory pipeline phase 4. Picks the next ready task from `.factory/tasks.json`, fetches
  relevant library docs via `find-docs`, implements one task end-to-end (code + matching
  unit tests), validates locally, and writes a diff artifact. Retries on failure up to
  `state.config.max_retries_per_task`. Only invoked inside the autonomous `factory`
  pipeline. Implements one task per invocation — caller (orchestrator) loops.
---

# factory-coder

Phase 4 (per-task). Implement one task with library docs in hand, like a human would: read the relevant docs, write code, write tests, run them.

## Invocation context

This skill is invoked by `factory-orchestrator` **inside an Agent subagent** (`subagent_type: general-purpose`), not in the main conversation. Implications:
- All artifacts MUST land on disk (`.factory/artifacts/task-<id>/`, `state.json`, `log.jsonl`). The subagent's context is discarded after it returns.
- Final response back to orchestrator MUST be a single line. No diffs, no test output, no doc excerpts in the return message — those go to artifact files.
- Re-read `state.json` and `tasks.json` at start; do not assume parent context.

## Inputs

- `.factory/state.json` — `current_task_id`
- `.factory/tasks.json` — full DAG
- `.factory/spec.md` — design contract
- `.factory/brief.md` — context for ambiguity
- Repo

## Output

- New / modified files in repo per task `files` list
- `.factory/artifacts/task-<id>/code.diff` — `git diff` snapshot
- `.factory/artifacts/task-<id>/notes.md` — what was done, what was deferred
- update `state.json`: task `status = "coded"`, advance `phase = "test"`

## Steps

1. **Refuse if wrong phase.** Read state. If `phase != "code"` or no `current_task_id`, exit.
2. **Load task.** Find task by id in `tasks.json`. Verify all `deps` have status >= `done`. If not, error and surface to orchestrator.
3. **Read spec slice.** Pull only the spec sections referenced by `acceptance_refs` and any data/API/UI contracts the task touches. Don't re-read whole spec.
4. **Doc lookup.** For each lib in `task.lib_docs_needed`, invoke `find-docs`:
   ```
   Skill(skill: "find-docs", args: "<lib> <specific question for THIS task>")
   ```
   Query should be specific to this task's slice, not the whole feature. Cap at 3 per task.
5. **Pick approach.** Decide:
   - **For UI tasks**: if visual design quality matters, invoke `frontend-design` skill alongside `find-docs`. Otherwise straight implementation.
   - **For API tasks**: validate input with Zod (or stack equivalent), return typed responses, handle defined error codes from spec.
   - **For migration tasks**: write up + down; include backfill if column is NOT NULL.
6. **Implement.** Use `Edit` / `Write` per file in `task.files`. Stay strictly within those files unless a dep is missing — in that case, set blocker and exit (don't sprawl).
7. **Write paired unit test if `kind != "test"`.** Even if test task is separate (planner usually has one), a code task should ship with at least one local sanity test.

   **Placement:** Write to `tests/<descriptive-name>.test.ts` — NOT to `.factory/artifacts/` and NOT co-located with source. The `tests/` directory is the only place vitest picks up tests.

   **Naming rule:** Derive the filename from the domain being tested, not the task ID. Examples:
   - task tests password hashing util → `tests/password-hashing.test.ts`
   - task tests session cookie logic → `tests/session-utils.test.ts`
   - task tests auth route handlers → `tests/auth-routes-smoke.test.ts`
   - task tests review/aggregators pages → `tests/reviews-aggregators-pages.test.ts`
   Never name a test file after the task ID (e.g. NOT `t1.test.ts`, NOT `task-t3.test.ts`).

   **Import paths:** From `tests/`, the project root is one level up. Use:
   - `../server/utils/foo` (not `../../../server/utils/foo`)
   - `../app/composables/useBar` (not `../../../app/composables/useBar`)
   - `../server/middleware/00.session` (not `../../../server/middleware/00.session`)

   Skip for `migration` and pure `config` kinds.
8. **Local validation.** Run cheap checks in this order; abort the rest on first failure:
   - typecheck: `pnpm typecheck` or `tsc --noEmit` (whatever repo uses)
   - lint: `pnpm lint` if configured
   - unit tests for this task: `pnpm test` (runs `vitest run tests/`) — or `pnpm test:api` for API contract tests only
   If repo uses different commands, detect from package.json scripts.
9. **On failure:** read error, attempt fix, repeat from step 6. Max attempts = `state.config.max_retries_per_task` (default 3). If still failing:
   - increment `task.retries`
   - set `task.blocker = "<error summary>"`
   - set `state.phase = "blocked"`, `human_gate_pending = true`
   - exit with blocker message
10. **Capture artifact.** Run `git diff` (unstaged + staged), write to `.factory/artifacts/task-<id>/code.diff`. Write `notes.md`:
    ```markdown
    # Task <id>: <title>
    - Files: <list>
    - Docs consulted: <lib ids>
    - Decisions: <2-3 bullets on design choices made>
    - Deferred: <anything pushed to later tasks>
    ```
11. **Advance state.**
    - task `status = "coded"`
    - `state.phase = "test"`
    - keep `current_task_id` (tester needs it)
    - Note: routing past `test` depends on `config.run_review` / `config.run_security`. Orchestrator handles that — coder always sets `phase = "test"` regardless.
    - log:
      ```json
      {"ts":"...","phase":"code","task_id":"<id>","event":"task_coded","files_changed":<N>}
      ```
12. **Return.** One-liner: `Task <id> coded (<N> files). Next phase: test.`

## Code style

- Match existing repo conventions (read 1-2 similar files first).
- No new abstractions unless spec asks for them.
- No comments except for non-obvious WHY (see CLAUDE.md rules).
- No backwards-compat shims, no fallback noise.
- Error handling only at system boundaries.

## When to use other skills

| Situation | Skill |
|---|---|
| UI component / page with visual quality bar | `frontend-design` |
| Figma-driven UI | `figma:figma-implement-design` (if URL in spec) |
| Library API uncertainty | `find-docs` |
| Post-write cleanup pass | `simplify` (only if change > 1 file and time permits) |

## What this skill does NOT do

- Does NOT run e2e or integration tests — that's `factory-tester`.
- Does NOT review the diff — that's `factory-reviewer`.
- Does NOT commit. Diff stays unstaged until human or `factory-orchestrator` ships.
- Does NOT implement more than one task. Even if the next task is trivial. Orchestrator decides.
- Does NOT skip `find-docs` because "the API is obvious". Skipping was the #1 source of bad code.

## Anti-patterns

- Don't expand the task's `files` list. If extra files are needed, add a blocker explaining what's missing — don't silently scope-creep.
- Don't write integration tests here. Those are separate tasks the planner already created.
- Don't loop on the same failing test more than `max_retries_per_task` times — escalate.
- Don't catch and swallow errors to make tests pass.
