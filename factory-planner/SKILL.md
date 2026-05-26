---
name: factory-planner
description: >-
  Factory pipeline phase 3. Reads `.factory/spec.md` and decomposes it into a DAG of
  small, independently-shippable tasks in `.factory/tasks.json`. Each task names exactly
  one slice (one file or small file group), declares deps, and links acceptance criteria
  it satisfies. Used only inside the autonomous `factory` pipeline.
---

# factory-planner

Phase 3. Turn the spec into a tasks DAG that the coder can pull from one at a time.

## Inputs

- `.factory/spec.md`
- `.factory/brief.md`
- `.factory/state.json`
- Repo state (to ensure task names match existing structure)

## Output

- `.factory/tasks.json` — list of task objects
- update `state.json`: copy tasks into `state.tasks` (just id/title/deps/status), `phase = "code"`, `current_task_id = <first ready task>`

## Steps

1. **Refuse if wrong phase.** Read `state.json`. If `phase != "plan"`, exit.
2. **Read spec.** Pull data model, API contract, UI contract, ACs.
3. **Slice rules:**
   - One task = one of: a migration, an API route, a component, a store action group, a fixture, an integration test, an e2e test.
   - Max ~150 LOC produced per task (heuristic; bigger = split).
   - Each task lists which ACs it advances (`acceptance_refs`).
   - Order respects deps: schema before route, route before UI fetching it, UI before its e2e test.
4. **Test tasks are first-class.** Every code task has a paired test task (unit/integration) and where relevant an e2e task referencing it. Tests are NOT a final step — they're interleaved with the code they cover.
5. **Write `tasks.json`.** Schema below.
6. **Pick first ready task** (no deps or all deps `done`): set `state.current_task_id`.
7. **Advance state.** `phase = "code"`, log:
   ```json
   {"ts":"...","phase":"plan","event":"plan_written","task_count":<N>,"first_task":"t1"}
   ```
8. **Return.** `Plan written → .factory/tasks.json. <N> tasks (<C> code, <T> test, <M> migration). First task: <t1 title>. Next phase: code.`

## tasks.json schema

```json
{
  "version": 1,
  "tasks": [
    {
      "id": "t1",
      "title": "Add orders table migration",
      "kind": "migration",
      "deps": [],
      "acceptance_refs": ["AC1", "AC2"],
      "files": ["db/migrations/0003_orders.sql"],
      "notes": "FK to users.id, status enum, index on (user_id, created_at)",
      "lib_docs_needed": ["/prisma/prisma"],
      "test_strategy": "verified by t2 (integration test)"
    },
    {
      "id": "t2",
      "title": "POST /api/orders integration tests",
      "kind": "test",
      "deps": ["t1"],
      "acceptance_refs": ["AC1", "AC2"],
      "files": ["tests/api/orders.post.spec.ts"],
      "notes": "covers 200, 400, 401, 409. Use real D1 instance.",
      "test_kind": "api-integration"
    },
    {
      "id": "t3",
      "title": "POST /api/orders implementation",
      "kind": "api-route",
      "deps": ["t1", "t2"],
      "acceptance_refs": ["AC1", "AC2"],
      "files": ["server/api/orders.post.ts"],
      "notes": "Zod validation, transactional insert"
    },
    {
      "id": "t10",
      "title": "Order creation e2e",
      "kind": "test",
      "deps": ["t3", "t9"],
      "acceptance_refs": ["AC1"],
      "files": ["tests/e2e/order-creation.spec.ts"],
      "notes": "Auth fixture; full happy path; assert order in list",
      "test_kind": "e2e-playwright"
    }
  ]
}
```

### Valid `kind` values

`migration` · `api-route` · `server-util` · `component` · `page` · `store` · `composable` · `fixture` · `test` · `config` · `docs`

### Valid `test_kind` values (only when `kind == "test"`)

`unit` · `api-integration` · `e2e-playwright` · `visual` (defer if not in scope)

## DAG hygiene

- No cycles. Validate before writing.
- Every non-test task should have at least one test task downstream that covers it.
- Every AC in spec must have ≥1 test task with that AC in `acceptance_refs`. If an AC has no test, that's a planner bug — fix before writing.
- Keep total tasks ≤ 25 for MVP. If spec implies more, the spec is too big and should be split into multiple factory runs — set `phase = "blocked"` and surface to human.

## Anti-patterns

- Do not write code or scaffold files. Only describe what each task should produce.
- Do not invent files outside what the spec implies (no random `utils/helpers.ts` catch-alls).
- Do not skip test tasks to "move faster" — the coder skill depends on a test target.
- Do not put more than one `kind` per task (one API route per task, not three).
- Do not reference libraries not already validated in spec's `docs_consulted` list.
