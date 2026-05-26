---
name: factory-human-gate
description: >-
  Factory pipeline pause point. Invoked when the factory hits a blocker (over retry
  budget, HIGH security finding, ambiguous spec, destructive op needed). Surfaces the
  blocker to the human with context and choices, then resumes or aborts based on the
  answer. Only used inside the autonomous `factory` pipeline.
---

# factory-human-gate

The factory's "ask a human" skill. Activated when `state.human_gate_pending == true` or `state.phase == "blocked"`.

## Inputs

- `.factory/state.json`
- `.factory/log.jsonl` (last ~20 entries for context)
- The relevant artifact (review.md, security.md, test-report.md, etc.) for the current blocker

## Output

- A resolved blocker: state mutated to either `phase` resumes or pipeline aborts
- log entry recording the human decision

## Steps

1. **Read state.** If `human_gate_pending == false` AND `phase != "blocked"`, exit immediately — nothing to ask.
2. **Read blockers.** Each blocker in `state.blockers`:
   ```json
   {"phase": "...", "task_id": "...", "reason": "...", "needs_human": true}
   ```
3. **Read context.** Pull the artifact tied to the blocker:
   - `phase: "intake"` → brief.md, original request
   - `phase: "spec"` → brief.md + unresolved questions
   - `phase: "code"` → coder's notes.md + last test/review report
   - `phase: "test"` → test-report.md
   - `phase: "review"` → review.md
   - `phase: "security"` → security.md
4. **Compose the ask.** Use `AskUserQuestion` with 1-4 questions, each 2-4 options:
   - Always include `Abort factory run` as one option for terminal blockers.
   - Always include `Resume — I fixed it manually` for human-fixable blockers.
   - For ambiguous spec: offer concrete interpretations as options.
   - For HIGH security: offer `Fix and retry` / `Override (NOT recommended)` / `Abort`.
5. **Show the artifact.** Before the question, print a tight summary (≤15 lines) of the blocker. Quote the actual error/finding verbatim — do not paraphrase.
6. **Wait for answer.** Apply:
   - **Resume:** remove blocker, set `human_gate_pending = false`, set `phase` to whatever phase was active before block. Decrement task retries if user confirms it's fixed.
   - **Fix and retry:** keep blocker but mark `awaiting_user_fix`. Loop should idle on this until next factory invocation, where it re-checks.
   - **Override:** annotate state with `overrides: [...]` and advance. Log loudly.
   - **Abort:** set `phase = "done"`, mark `aborted = true`, exit.
   - **Other (free text):** record the note, treat as Abort if no clear intent.
7. **Log decision.**
   ```json
   {"ts":"...","event":"human_gate","blocker":"...","decision":"resume|override|abort|fix"}
   ```
8. **Return.**

## What to surface — examples

### Spec-too-vague blocker
```
Factory paused at intake.

Original request: "make orders faster"

Cannot proceed because:
- No actor specified (who experiences "faster"?)
- No measurable target (faster than what?)
- No surface (order list page? order creation API?)

Pick a direction or abort.
```

### Coder over-retry blocker
```
Factory paused at code phase, task t3 (POST /api/orders implementation).

After 3 attempts, this test still fails:
  expected status 200, got 500
  TypeError: Cannot read property 'userId' of undefined
    at server/api/orders.post.ts:24

Last attempt's notes.md says: "auth context shape changed in Nuxt 4 — need to check docs again".

Should I (a) re-run with fresh find-docs lookup, (b) skip this task, (c) abort?
```

### HIGH security blocker
```
Factory paused at security phase, task t3.

security-review found:
  HIGH | server/api/orders.post.ts:34 | CWE-89 | string-interpolated SQL

Quote:
  db.prepare(`SELECT * FROM orders WHERE user_id = ${userId}`)

Recommendation: fix and retry. Override is allowed but logged.
```

## When NOT to invoke this skill

- When the pipeline is healthy. Don't ask "should I continue?" — orchestrator just runs the next phase.
- For LOW review findings. Just log them and advance.
- For routine retries within budget. The retry mechanism handles them; human only sees blockers after retries are exhausted.

## Anti-patterns

- Don't summarize errors — quote them verbatim so the human can grep.
- Don't ask >4 questions at once.
- Don't proceed on ambiguous "Other" answers — treat as Abort.
- Don't silently override HIGH security findings, ever. The user must explicitly choose Override.
