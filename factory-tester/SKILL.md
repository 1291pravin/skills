---
name: factory-tester
description: >-
  Factory pipeline phase 5. Verifies the current task like a human would — drives the
  running app through the browser via the `playwright-cli` skill for UI work, or hits the
  live endpoints with `curl` for API work. Checks each acceptance criterion against real
  behavior, logs any issues, and routes back to the coder on failure. Writes NO test
  files. Only invoked inside the autonomous `factory` pipeline.
---

# factory-tester

## Invocation context

Invoked by `factory-orchestrator` **inside an Agent subagent** (`subagent_type: general-purpose`), not in the main conversation. All output (verification log, snapshots, curl transcripts, AC coverage) MUST land in `.factory/artifacts/task-<id>/test-report.md`. Return one summary line to the orchestrator — no logs in the response.

Phase 5, **per task**. After the coder finishes a task, this skill exercises that task's behavior against its acceptance criteria — manually, like a tester sitting at the app. Two verification modes:

1. **Browser / UI** — drive the running dev server through the `playwright-cli` skill (open, navigate, click, fill, snapshot, read console).
2. **API** — hit the running backend's routes with `curl` and assert status + response body.

## Does NOT write tests

This skill writes **zero** test files. No `*.spec.ts`, no `tests/` additions, no test generation. The coder may have shipped its own unit tests — those are not this skill's concern. This skill *uses the app*, observes what it does, and reports whether each AC holds. Verification is by live interaction, not committed test code.

## Inputs

- `.factory/state.json` — `current_task_id`
- `.factory/tasks.json` — current task + its `acceptance_refs`, `kind`
- `.factory/spec.md` — AC definitions (Given/When/Then), API contract, UI contract, edge-case table
- `.factory/artifacts/task-<id>/code.diff` — what the coder changed (to know what to exercise)
- `package.json` scripts — to find the dev/server start command

## Output

- `.factory/artifacts/task-<id>/test-report.md` — verification log + AC coverage + issues
- update `state.json`: task `status = "tested"` + `phase = "review"` on pass; or revert to `phase = "code"` with blocker on failure (or `phase = "blocked"` over budget)
- **No repo files written.**

## Steps

1. **Refuse if wrong phase.** Read state. If `phase != "test"` or no `current_task_id`, exit.
2. **Load task + ACs.** Find the task in `tasks.json`. Pull the Given/When/Then for each id in `acceptance_refs` from `spec.md`, plus any edge-case rows that apply.
3. **Pick verification mode** from `task.kind` and which spec contract the ACs touch:
   - **Browser** (`playwright-cli`): `kind` in `component` · `page` · `store` · `composable` (when user-facing) — or the AC is described against the UI contract.
   - **API** (`curl`): `kind` in `api-route` · `server-util` — or the AC is described against the API contract only.
   - **Both**: a task whose AC spans a UI action that calls an API end-to-end → exercise the UI with `playwright-cli`, and spot-check the underlying endpoint with `curl` if the UI hides the failure.
   - **Skip** (no observable behavior yet): `migration` · `config` · `fixture` · `docs` with no route/page wired up — record "no live surface to exercise; verified by downstream task" and advance to review. See *When to skip*.
4. **Start the app if not already running.**
   - Detect command from `package.json`: Nuxt `pnpm dev`, wrangler `pnpm wrangler dev`, or a repo `dev`/`start`/`test:setup` script.
   - Launch in background, capture PID, wait for the port to accept connections before proceeding.
   - If a server is already up on the expected port, reuse it.
5. **Verify each AC like a human.** Walk the Given/When/Then. Do NOT write a test file — perform the steps live.

   **Browser (via `playwright-cli` skill):**
   ```
   Skill(skill: "playwright-cli", args: "open http://localhost:3000<path>, then <do the AC's When steps>, then snapshot and report whether <the AC's Then> holds")
   ```
   Drive it: `open` / `goto` the page, `snapshot` to get refs, `click` / `fill` / `select` / `press` per the When, then `snapshot` + `eval` to confirm the Then. Run `playwright-cli console` to catch JS errors. Prefer `data-testid`; fall back to accessible roles/text. Save a snapshot per AC with `--filename` so it lands as an artifact.

   **API (via `curl`):**
   - One invocation per AC × applicable edge-case row.
   - Send the real request to the running route; assert HTTP status, then response body shape/values against the spec's API contract.
   - Cover the defined error codes (e.g. 200 / 400 / 401 / 409) from the spec, not just the happy path.
   - Use a fresh row / unique payload per call so calls don't depend on each other. Clean up created rows where feasible.
   - Capture the full request line + response (status + trimmed body) into the report.
6. **Judge each AC.** Mark `pass` only if the observed behavior matches the Then. Anything off — wrong status, wrong body, console error, missing element, broken redirect — is an issue.
7. **Log issues.** For every failing AC write: AC id, what was expected (from spec), what actually happened, and the exact repro (the `playwright-cli` step sequence or the `curl` command + response). This is the payload the coder needs to fix it.
8. **Decision:**
   - **All AC pass, no issues** → task `status = "tested"`, `phase = "review"` (orchestrator skips review/security per `config.run_review` / `config.run_security` and marks the task `done` if both off).
   - **Any AC fails** → increment `task.retries`.
     - Under `config.max_retries_per_task`: set `status = "in_progress"`, `phase = "code"`, and put a tight failure summary (which AC, expected vs actual, repro) in `task.blocker` so the coder fixes the right thing.
     - Over budget: `phase = "blocked"`, `human_gate_pending = true`.
9. **Write `test-report.md`** (template below).
10. **Cleanup.** Kill any server PID started in step 4. Close any `playwright-cli` browser session (`playwright-cli close`).
11. **Log + return.** Append a `tick` log line; return one summary line.

## test-report.md template

```markdown
# Test report — task <id>: <title>

**Run at:** <ISO>
**Mode:** <browser (playwright-cli) | api (curl) | both | skipped>
**App:** <auto-started `<cmd>` | reused on :<port> | n/a>

## Acceptance coverage
| AC | How verified | Result |
|---|---|---|
| AC1 | playwright-cli: /orders → fill → submit → snapshot order-ac1.yaml | ✅ pass |
| AC2 | curl -X POST /api/orders (bad payload) → expect 400 | ❌ fail — got 500 |

## Issues found
### AC2 — invalid payload should return 400
- **Expected:** `400` + `{ "error": "validation" }` (spec API contract)
- **Actual:** `500`, body `Internal Server Error`
- **Repro:**
  ```
  curl -s -o - -w '%{http_code}' -X POST http://localhost:3000/api/orders \
    -H 'content-type: application/json' -d '{}'
  ```

## Next action
- <`route back to code (retry N/M)`, `proceed to review`, or `escalate (over retry budget)`>
```

## Calling playwright-cli

Always go through the skill — it owns browser launch, server-readiness, snapshots, and cleanup. Do not call the `playwright-cli` binary directly here.

```
Skill(skill: "playwright-cli", args: "open http://localhost:3000/login, fill email + password, click submit, snapshot, and report whether the dashboard heading appears")
```

It returns a snapshot of page state after each action — read that to judge the AC. Use `playwright-cli console` to surface JS errors that a passing visual still hides.

## curl style (API mode)

- Hit the **live** route on the running backend. No mocks.
- One call per AC × edge-case row; show status and body.
- Capture status explicitly: `curl -s -o /dev/null -w '%{http_code}'` (or `-w '\n%{http_code}'` to keep the body).
- On Windows the subagent runs PowerShell — prefer the `Bash` tool for `curl` so POSIX flags and quoting work, or use `curl.exe` from PowerShell.
- Assert the error codes the spec defines, not only 200.
- Keep calls independent: unique payloads / fresh rows; clean up where feasible.

## Anti-patterns

- **Don't write test files.** Not `*.spec.ts`, not a `tests/` entry, not generated specs. Verify live. This is the whole point of this rewrite.
- Don't mark an AC pass without observing the actual behavior (a snapshot, a status code, a body).
- Don't advance the pipeline past a real failure. Loop back to coder or escalate.
- Don't exercise an endpoint/page that this task didn't touch — scope to the current task's `acceptance_refs` and `code.diff`.
- Don't leave the dev server or browser session running. Kill what you started.
- Don't retry a flaky-looking pass — if behavior is non-deterministic, that's an issue to log.

## When to skip

If `task.kind` is `migration` / `config` / `fixture` / `docs` and there is no route or page wired up yet to observe, there is nothing to drive — record "no live surface; verified by downstream task" and advance to review. The downstream task that consumes the migration/config is where it gets exercised.

## Blocking

If the dev server / backend fails to boot, set `state.phase = "blocked"`, blocker = `"dev server boot failed: <reason>"`. Don't loop on it — it's a config problem the human must resolve.
