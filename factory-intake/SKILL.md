---
name: factory-intake
description: >-
  Factory pipeline phase 1. Parses a vague feature request into a structured brief.md
  with user, problem, goals, constraints, and explicit unknowns. Only used inside the
  autonomous `factory` pipeline — not for general PRD work. Asks the user clarifying
  questions when the request lacks critical information, otherwise records assumptions
  and proceeds.
---

# factory-intake

Phase 1 of the autonomous factory. Turn the original one-line request in `state.json` into a structured brief that downstream skills (`factory-spec`, `factory-planner`) can rely on.

## Inputs

- `.factory/state.json` — read `request` field
- Current repo context (CLAUDE.md, package.json, existing code) to ground assumptions

## Output

- `.factory/brief.md` — structured brief (template below)
- update `state.json`: `phase = "spec"`, append log entry

## Steps

1. **Read state.** Read `.factory/state.json`. Pull `request`. Refuse if `phase != "intake"`.
2. **Survey repo.** Quick read of CLAUDE.md, AGENTS.md, README.md, package.json/pyproject.toml. Detect stack. Populate `state.config.stack` if empty.
3. **Identify gaps.** Compare request to a minimum-viable brief checklist:
   - **Who** is the user / actor?
   - **What** observable outcome do they get?
   - **Where** in the app does this live (page/route/API)?
   - **Constraints**: auth required? data source? perf budget? a11y?
   - **Out of scope**: what should explicitly NOT be done?
   - **Done criteria**: how do we know it works?
4. **Ask only blocking questions.** Use `AskUserQuestion` with 1-4 questions, each with 2-4 options + an implied "Other". Skip Qs you can answer from repo. If nothing blocking, skip the ask.
5. **Record assumptions.** Anything inferred from repo without user confirmation goes in an `## Assumptions` section. Mark each with confidence (high/med/low).
6. **Write `brief.md`** using template.
7. **Advance state.** Set `phase = "spec"`, set `updated_at`, append to `log.jsonl`:
   ```json
   {"ts":"...","phase":"intake","event":"brief_written","artifact":".factory/brief.md"}
   ```
8. **Return.** Tell user one line: `Brief written → .factory/brief.md. Next phase: spec.`

## brief.md template

```markdown
# Brief: <short title>

**Request:** <verbatim original request>
**Created:** <ISO date>

## Actor
- Primary: <who triggers / uses this>
- Secondary: <admins, observers, etc.>

## Outcome
<one paragraph: what the actor sees / can do that they couldn't before>

## Surface
- Route / page / endpoint: <e.g., `/orders/new`, `POST /api/orders`>
- Entry points: <nav link, button, API client>

## Constraints
- Auth: <required role / public>
- Data: <DB tables involved, external APIs>
- Performance: <p95 target, payload size>
- Accessibility: <WCAG level if relevant>
- Browser/device: <if frontend>

## Out of scope
- <explicit non-goals>

## Done criteria
- [ ] <observable, testable statement>
- [ ] <...>

## Assumptions
- [HIGH] <inferred from repo, very likely correct>
- [MED] <reasonable inference, worth confirming>
- [LOW] <guess, flag for human review>

## Open questions (deferred to spec phase)
- <questions that aren't blocking but spec phase should resolve>
```

## When to block instead of ask

If the request is so vague that even with answers the brief would be guesswork (e.g. "make the app better"), do NOT spawn 10 clarifying questions. Set `state.phase = "blocked"`, add a blocker:
```json
{"phase":"intake","reason":"request too vague — need feature, user, and one acceptance criterion","needs_human":true}
```
…and exit. The `factory-human-gate` skill surfaces this to the user.

## Anti-patterns

- Do not write a spec — `factory-spec` does that with library docs.
- Do not enumerate tasks — `factory-planner` does that.
- Do not write code or design — wrong phase.
- Do not ask >4 questions per turn (UI limit).
- Do not invent acceptance criteria the user didn't imply.
