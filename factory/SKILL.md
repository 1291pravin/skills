---
name: factory
description: >-
  Autonomous software factory entry point. Converts vague requirements into production-grade
  software by chaining intake → spec → plan → code → test → review → security skills via a
  shared state.json. Use when the user says "build a factory", "/factory <request>",
  "autonomous build", "run the factory", "build me X end-to-end", or wants Claude to drive a
  full requirement-to-shipped feature loop. The skill itself initializes workspace and
  delegates each phase to a `factory-*` sub-skill. Self-driving via `factory-orchestrator`
  internal loop — no `/loop` or `/schedule` needed.
---

# Factory

Autonomous pipeline: requirement → production code. Each phase is a separate skill that reads/writes a shared workspace.

## Trigger

```
/factory <one-line request>
/factory                       # resume existing state.json
```

## Workspace

All factory artifacts live in `.factory/` at project root (gitignored by default):

```
.factory/
  state.json          # pipeline state machine
  brief.md            # parsed requirement (factory-intake)
  spec.md             # PRD + acceptance criteria (factory-spec)
  tasks.json          # task DAG (factory-planner)
  artifacts/
    task-<id>/
      code.diff       # changes made
      tests/          # test files written
      test-report.md  # tester output
      review.md       # reviewer findings
      security.md     # security audit
  log.jsonl           # append-only event log
```

## state.json schema

```json
{
  "version": 1,
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "request": "original user request",
  "phase": "intake|spec|plan|code|test|review|security|done|blocked",
  "current_task_id": null,
  "tasks": [
    {
      "id": "t1",
      "title": "string",
      "deps": ["t0"],
      "status": "pending|in_progress|coded|tested|reviewed|secured|done|failed",
      "retries": 0,
      "blocker": null,
      "artifact_dir": ".factory/artifacts/task-t1"
    }
  ],
  "blockers": [
    {"phase": "code", "task_id": "t1", "reason": "...", "needs_human": true}
  ],
  "human_gate_pending": false,
  "config": {
    "max_retries_per_task": 3,
    "stack": "nuxt|node|python|...",
    "test_runner": "vitest|jest|pytest",
    "e2e_via_playwright": true,
    "run_review": false,
    "run_security": false,
    "code_test_via_subagent": true
  }
}
```

## What you do when invoked

### Case A: `.factory/state.json` does NOT exist (fresh start)

1. Create `.factory/` and `.factory/artifacts/`.
2. Append `.factory/` to `.gitignore` if not present.
3. Write initial `state.json`:
   - `phase: "intake"`
   - `request: <user's one-line request>`
   - empty `tasks`, `blockers`
4. Invoke `factory-intake` via the Skill tool. It will produce `.factory/brief.md` and update state to `phase: "spec"`.
5. Invoke `factory-orchestrator`. It self-loops until `done` / `blocked` / `aborted`.
6. After orchestrator returns, print final summary (task counts, blockers, artifact paths).

### Case B: `state.json` exists (resume)

1. Read `state.json`.
2. If `phase == "done"`: print summary, exit.
3. If `phase == "blocked"` or `human_gate_pending == true`: invoke `factory-human-gate`. After human resolves, clear `human_gate_pending`, then invoke `factory-orchestrator` to continue.
4. Else: invoke `factory-orchestrator`. It self-loops until terminal state.

## Phase → skill mapping

| phase | skill invoked | how invoked | enabled by default | reads | writes |
|---|---|---|---|---|---|
| intake | `factory-intake` | Skill (main ctx) | yes | request | `brief.md` |
| spec | `factory-spec` | Skill (main ctx) | yes | `brief.md` | `spec.md` |
| plan | `factory-planner` | Skill (main ctx) | yes | `spec.md` | `tasks.json` |
| code | `factory-coder` | **Agent subagent** | yes | one task, spec | code + tests in repo, `code.diff` |
| test | `factory-tester` | **Agent subagent** | yes | task artifact | `test-report.md` |
| review | `factory-reviewer` | Skill (main ctx) | **no — opt-in via `config.run_review`** | task artifact | `review.md` |
| security | `factory-security` | Skill (main ctx) | **no — opt-in via `config.run_security`** | task artifact | `security.md` |

Default per-task cycle: code → test → done. If `run_review` set, insert review phase. If `run_security` set, insert security phase after review (or after test if review off). When all tasks `done`, set `phase: "done"`.

### Subagent invocation (code + test)

`factory-coder` and `factory-tester` are invoked through the `Agent` tool (`subagent_type: general-purpose`), not direct `Skill`. Reason: their work fills lots of context (diffs, test output, doc lookups) that the orchestrator does not need to retain. The subagent runs the skill, writes artifacts to `.factory/artifacts/task-<id>/`, mutates `state.json`, and returns a one-line summary to the main context.

### Enabling optional phases

User can flip the flags at any time:
```
/factory enable review
/factory enable security
/factory disable review
```
Or edit `.factory/state.json` `config.run_review` / `config.run_security` directly. Orchestrator reads the flag at each task transition.

## Autonomous loop

Self-driving. `factory-orchestrator` loops internally — picks next ready action, executes one phase, persists state, repeats. Continues until terminal state:
- `phase == "done"` → all tasks done, exit.
- `phase == "blocked"` or `human_gate_pending == true` → invoke `factory-human-gate`, then exit (human must resume via `/factory`).
- `aborted == true` → exit.

No external `/loop` or `/schedule` driver needed. To resume after a block, user runs `/factory` again; orchestrator picks up from current state.

## Logging

Every state mutation appends to `.factory/log.jsonl`:
```json
{"ts":"...","phase":"code","task_id":"t1","event":"task_started","skill":"factory-coder"}
```

## Stopping conditions

The factory pauses (sets `human_gate_pending: true`) when:
- spec has ambiguity that intake's clarifying Qs did not resolve
- a task exceeds `max_retries_per_task`
- security audit returns HIGH severity (only if `run_security` enabled)
- review marks an issue as `blocking` (only if `run_review` enabled)
- destructive op needed (drop table, force-push, prod deploy)

## State invariants

- Never overwrite `request` after creation.
- Never delete tasks; mark `status: "failed"` and add a blocker.
- Always `updated_at` on every mutation.
- A task moves through statuses linearly: pending → in_progress → coded → tested → reviewed → secured → done. Failed at any step: revert to `in_progress` with incremented `retries`, or `failed` if over budget.

## What this skill does NOT do

- Does not run tests itself (that's `factory-tester`).
- Does not write code itself (that's `factory-coder`).
- Does not deploy. Out of MVP scope. Add `factory-deployer` later.
