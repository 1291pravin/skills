---
name: factory-spec
description: >-
  Factory pipeline phase 2. Reads `.factory/brief.md`, researches relevant libraries/APIs
  via the `find-docs` skill (Context7), and produces a structured `.factory/spec.md` with
  user stories, API contracts, data model, edge cases, and testable acceptance criteria.
  Only invoked inside the autonomous `factory` pipeline. Never writes code.
---

# factory-spec

Phase 2 of the autonomous factory. Turn the brief into a spec that `factory-planner` can decompose and `factory-coder` can implement without re-deriving design choices.

## Inputs

- `.factory/brief.md`
- `.factory/state.json` (read `request`, `config.stack`)
- Repo state: existing pages, API routes, DB schema (read but don't modify)

## Output

- `.factory/spec.md` (template below)
- update `state.json`: `phase = "plan"`, append log entry

## Steps

1. **Refuse if wrong phase.** Read `state.json`. If `phase != "spec"`, error and exit.
2. **Read brief.** Pull actor, outcome, surface, constraints, done criteria.
3. **Survey existing code.** Use `Grep`/`Glob` to find:
   - existing models / tables / endpoints touching same domain
   - existing UI components reusable for this feature
   - existing tests showing project's test style
4. **Library research (mandatory).** Identify every external lib/API this feature touches (Nuxt features, ORM, validation lib, auth provider, etc.). For each:
   - Invoke `find-docs` skill via Skill tool with a specific query.
   - Capture the relevant API signatures and gotchas in the spec.
   - Do NOT skip this even if you "know" the API — stack may have shifted.
5. **Design contract.** Specify:
   - **Data model** changes (new tables, columns, indexes; migration sketch)
   - **API contract** (route, method, request schema, response schema, error codes)
   - **UI contract** (component tree, props, events, states: loading/empty/error/success)
   - **State management** (where data lives, who fetches, who mutates)
6. **Enumerate edge cases.** Empty data, concurrent writes, auth failure, network failure, validation errors, large inputs, slow responses. Each gets a defined behavior.
7. **Convert done criteria → acceptance tests.** Each "Done criteria" bullet in brief becomes 1-N explicit acceptance test scenarios with Given/When/Then.
8. **Write `spec.md`.**
9. **Advance state.** `phase = "plan"`, append log:
   ```json
   {"ts":"...","phase":"spec","event":"spec_written","docs_consulted":["/nuxt/nuxt","/prisma/prisma",...]}
   ```
10. **Return.** One-line summary to user: `Spec written → .factory/spec.md. <N> acceptance scenarios, <M> libraries researched. Next phase: plan.`

## Calling find-docs

For each library, invoke the Skill tool:

```
Skill(skill: "find-docs", args: "<library> <specific question grounded in this feature>")
```

Examples:
- `Skill(skill: "find-docs", args: "Nuxt 3 server route validation with Zod")`
- `Skill(skill: "find-docs", args: "Prisma migration adding nullable column with default")`
- `Skill(skill: "find-docs", args: "Playwright fixture for authenticated routes")`

Cap at 5 doc queries per spec phase. Record each consulted lib id in `state.config.docs_consulted`.

## spec.md template

```markdown
# Spec: <title from brief>

**Brief:** [.factory/brief.md](./brief.md)
**Stack:** <e.g. Nuxt 3 + Cloudflare D1 + Pinia>
**Docs consulted:** <library ids from find-docs>

## User stories
- As a <actor>, I want <action>, so that <outcome>. (links to AC1, AC2)

## Data model
### New / changed tables
```sql
-- migration sketch (NOT final SQL)
```
### Invariants
- <constraint that must always hold>

## API contract
### `POST /api/orders`
- **Auth:** required (role: customer)
- **Request:** `{ ... }` (Zod schema)
- **Response 200:** `{ ... }`
- **Errors:** 400 (validation), 401 (auth), 409 (conflict), 500
- **Rate limit:** 10/min/user

## UI contract
- **Page:** `app/pages/orders/new.vue`
- **Components:** `OrderForm`, `OrderConfirmation`
- **Props/events:** ...
- **States:** loading, empty, error, success — each described

## State management
- Store: `useOrdersStore` (Pinia)
- Actions: `createOrder()`, `loadOrders()`
- Reactivity boundaries: ...

## Edge cases
| Case | Behavior |
|---|---|
| Empty cart submitted | UI disables submit; API returns 400 |
| Network timeout | Retry once, then show toast |
| ... | ... |

## Acceptance criteria (testable)
### AC1 — Happy path
- **Given** authenticated customer on `/orders/new` with valid cart
- **When** they submit the form
- **Then** order appears in `/orders` list within 2s
- **Test type:** e2e (playwright) + api integration

### AC2 — Validation
- **Given** ...
- **When** ...
- **Then** ...
- **Test type:** unit + api

## Out of scope (from brief)
- <copied forward>

## Open risks
- <known unknowns that may force a re-plan mid-build>
```

## Anti-patterns

- Do NOT skip `find-docs` because you think you know the API.
- Do NOT prescribe filenames for code (planner does that).
- Do NOT write code, even pseudocode beyond Given/When/Then.
- Do NOT add features beyond what the brief implies.
- Do NOT generate >10 acceptance criteria. Cap at brief's "Done criteria" count + edge cases. Bloat = wasted code/test cycles.

## Blocking

If brief lacks info needed to write a meaningful contract (e.g., no clear actor, no observable outcome): set `phase = "blocked"`, add blocker pointing back to brief, exit. Don't fabricate.
