---
name: factory-orchestrator
description: >-
  Factory pipeline state-machine driver. Reads `.factory/state.json`, picks the next
  action based on `phase` and task DAG, invokes the matching sub-skill, persists state,
  and repeats until terminal state (`done`, `blocked`, or `aborted`). Self-driving — no
  external `/loop` needed. Only invoked inside the autonomous `factory` pipeline.
---

# factory-orchestrator

State-machine driver. Self-loops: pick next action → invoke sub-skill → persist state → repeat until terminal.

## Why self-loop

- Persistent state in `.factory/state.json` = crash-safe resume on next `/factory` invocation.
- Coder + tester run in subagents — main context stays small even across many ticks.
- Human can `Ctrl-C`; restart with `/factory` picks up from last persisted state.
- Terminal states (`done`, `blocked`, `aborted`) cleanly exit the loop.

## Inputs

- `.factory/state.json`

## Output

- One or more sub-skill invocations (looped until terminal)
- Mutated `state.json` (every tick)
- Log lines in `.factory/log.jsonl` (one per tick)
- Final summary string returned to caller when loop exits

## Decision table

| state.phase | state.human_gate_pending | Action |
|---|---|---|
| (no state.json) | — | error: run `/factory <request>` first |
| `intake` | false | invoke `factory-intake` via Skill |
| `spec` | false | invoke `factory-spec` via Skill |
| `plan` | false | invoke `factory-planner` via Skill |
| `code` | false | invoke `factory-coder` **via Agent subagent** |
| `test` | false | invoke `factory-tester` **via Agent subagent**, then route per flags (see below) |
| `review` | false | if `config.run_review` invoke `factory-reviewer`; else skip → security or done |
| `security` | false | if `config.run_security` invoke `factory-security`; else skip → mark task done |
| `blocked` | any | invoke `factory-human-gate` |
| any | `true` | invoke `factory-human-gate` |
| `done` | false | print summary, exit |

### Default post-test routing (review + security disabled)

After `factory-tester` returns with task `status = "tested"` and `config.run_review == false`:
1. Mark task `status = "done"`.
2. Pick next ready task. If none and all `done` → `phase = "done"`. Else set `current_task_id`, `phase = "code"`.

If `config.run_review == true` but `config.run_security == false`: tester sets `phase = "review"`. After reviewer success, mark task `status = "done"` and pick next.

If both flags true: original cycle code → test → review → security → done.

## Steps

Top-level: **loop until terminal state**.

```
loop:
  read .factory/state.json
  if phase == "done": print summary, exit loop
  if phase == "blocked" or human_gate_pending or aborted: invoke factory-human-gate, exit loop
  one_tick()
```

Inside one tick:

1. **Read state.** If `.factory/state.json` missing → error: tell user `Run /factory <request> first`. Exit.
2. **Idempotency check.** If `phase == "done"`:
   ```
   Factory complete. <N> tasks done. See .factory/artifacts/ and .factory/log.jsonl.
   ```
   Exit.
3. **Decide.** Apply decision table. Determine `next_skill`.
4. **Sanity gate before invoking.**
   - `code/test/review/security` require `current_task_id`. If null, pick next ready task (status `pending` with all `deps` done). If none ready and not all done → cycle in DAG, escalate via human-gate. If all done → set `phase = "done"`, log, exit.
   - Task status transitions depend on enabled phases:
     - default (review off, security off): `pending → in_progress (code) → coded → tested → done`
     - review on, security off: `... → tested → reviewed → done`
     - review on, security on: `... → tested → reviewed → secured → done`
     - review off, security on: `... → tested → secured → done`
5. **Invoke sub-skill.**
   - For `intake`, `spec`, `plan`, `review`, `security`: use the **Skill** tool. Pass no args — sub-skills read state themselves.
   - For `code` and `test`: use the **Agent** tool with `subagent_type: "general-purpose"`. Subagent prompt:
     ```
     Run the `factory-<coder|tester>` skill in this repo. State lives in .factory/state.json — read it yourself, do the work per the skill's SKILL.md, write artifacts to .factory/artifacts/task-<id>/, mutate state.json, append to .factory/log.jsonl. Return ONLY a one-line summary like "Task <id> coded (3 files). Next phase: test." Do NOT include diffs, test output, or doc excerpts in the response.
     ```
     This keeps coder/tester context (diff text, test logs, doc fetches) out of the orchestrator's window.
   - After tester returns, apply the post-test routing rules (see Decision table) before the next tick — that routing is a state mutation, not a sub-skill invocation.
6. **Sub-skill returns.** It will have mutated state. Reload it.
7. **Validate transition.** If sub-skill didn't update `updated_at` or advance `phase`/`task.status`, that's a bug — log a `stalled` event and DO NOT loop. Surface to user.
8. **Append log entry:**
   ```json
   {"ts":"...","event":"tick","phase_before":"...","phase_after":"...","skill":"...","task_id":"..."}
   ```
9. **Continue loop.** Go back to top of loop block. Do NOT return to caller until terminal state reached.

## Loop exit conditions

The internal loop exits only on:
- `state.phase == "done"` → print summary, return.
- `state.phase == "blocked"` or `state.human_gate_pending == true` → invoke `factory-human-gate` once, then return. (User must re-run `/factory` after resolving.)
- `state.aborted == true` → return immediately.
- **Safety cap:** if loop completes 200 ticks without reaching terminal state, force `phase = "blocked"` with blocker `"orchestrator tick cap hit — possible infinite loop"` and exit. Prevents runaway.

## Final return

On exit, return a single summary:
```
Factory <done|blocked|aborted>. Tasks: <N done> / <M total>. Phases run: <count>. Artifacts: .factory/artifacts/. Log: .factory/log.jsonl.
```

## What this skill does NOT do

- Does NOT modify the repo directly. Only `state.json` + `log.jsonl`.
- Does NOT decide to abort on its own. Aborts go through `factory-human-gate`.
- Does NOT run review or security phases unless `config.run_review` / `config.run_security` are true. Default skips both — task moves test → done.
- Does NOT depend on `/loop` or `/schedule`. Self-driving.

## Anti-patterns

- Don't pick a task that has unmet deps. The DAG is the law.
- Don't increment retries here. Only the failing sub-skill increments its own retries.
- Don't write code, tests, or artifacts. Sub-skills own those.
- Don't bypass the 200-tick safety cap.
- Don't keep looping after `human_gate_pending` flips true — invoke human-gate once, return.

## Failure modes the orchestrator detects

| Symptom | Action |
|---|---|
| Sub-skill returned but no state mutation | Log `stalled`, set `phase = "blocked"`, surface to user |
| `current_task_id` points to non-existent task | Log error, set `phase = "blocked"` |
| DAG cycle (no ready task and not all done) | Set `phase = "blocked"`, surface to user |
| `state.json` malformed | Refuse, ask user to inspect / rerun `/factory` to reinitialize (with backup of old state) |

## State snapshot the orchestrator maintains

Every tick must `updated_at` and add a log entry. The orchestrator is the only place that bumps `updated_at` at the tick level — sub-skills also bump it on their own writes, but the orchestrator does a final bump after sub-skill return so `state.updated_at` reflects last tick time even if sub-skill failed silently.
