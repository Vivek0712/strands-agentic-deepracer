# Phase 1: Error Handling — Implementation Tasks

## Task 1: Tool Layer Audit
- [ ] Read every function in `deepracer_tools.py` and confirm no `raise` statements outside `_get_client()`
- [ ] Confirm every except block returns a string starting with `"Error "` or `"Warning: "`
- [ ] Confirm `stop_car()` in `finally` returns the warning string on failure (not `pass`)
- [ ] Confirm `_get_client()` raises `RuntimeError` (not returns an error string) for missing password

## Task 2: Agent Layer Audit
- [ ] Confirm `plan_navigation()` raises `ValueError` on JSON parse failure
- [ ] Confirm `plan_navigation()` raises `ValueError` when `"steps"` is missing or not a list
- [ ] Confirm `execute_step()` returns `f"Skipped unknown action '{action}'."` for unknown actions
- [ ] Confirm `execute_plan()` has no try/except that swallows step errors — errors flow as strings

## Task 3: CLI Error Messages
- [ ] Confirm agent creation failure prints `❌ Failed to create planner agent:` and returns (not crashes)
- [ ] Confirm planning failure prints `❌ Failed to plan navigation:` and continues the loop
- [ ] Confirm each step result is printed even when it starts with "Error"
- [ ] Confirm `KeyboardInterrupt` handler prints `"\nInterrupted. Type 'exit' to quit."` and continues

## Task 4: Web API Error Responses
- [ ] Confirm `/api/plan` returns `jsonify({"error": str(e)}), 500` on exception
- [ ] Confirm `/api/execute` returns `jsonify({"ok": False, "error": str(e)}), 500` on exception
- [ ] Confirm both endpoints return `400` (not `500`) for missing/invalid input

## Task 5: Frontend Error Handling
- [ ] Confirm `getPlanBtn` click handler has a `catch(e)` that calls `showResult(e.message, 'error')`
- [ ] Confirm `executeBtn` click handler has a `catch(e)` that calls `showResult(e.message, 'error')`
- [ ] Confirm non-ok HTTP responses show `data.error` in the error result box
- [ ] Confirm result box uses `.error` CSS class (red background) for all failure states

## Task 6: Error Convention Test
- [ ] Simulate a bad DEEPRACER_IP — confirm error string starts with "Error" and is shown to user
- [ ] Simulate missing DEEPRACER_PASSWORD — confirm RuntimeError is raised at client creation
- [ ] Submit empty prompt to `/api/plan` — confirm 400 response with `{"error": "prompt is required"}`
- [ ] Submit plan with no steps to `/api/execute` — confirm 400 response
