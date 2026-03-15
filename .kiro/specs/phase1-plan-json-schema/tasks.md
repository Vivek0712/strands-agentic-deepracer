# Phase 1: Plan JSON Schema — Tasks

## Task 1: Validation in plan_navigation()
- [ ] Confirm `"steps" not in data` check raises `ValueError`
- [ ] Confirm `not isinstance(data["steps"], list)` check raises `ValueError`
- [ ] Confirm the error message is `"Planner response missing 'steps' list"`
- [ ] Confirm extra top-level keys do not cause errors (just ignored)

## Task 2: execute_step() Robustness
- [ ] Confirm `step.get("action", "")` — missing action defaults to empty string
- [ ] Confirm `str(...).lower()` — action is always stringified and lowercased
- [ ] Confirm `step.get("seconds")` — missing seconds returns None (not KeyError)
- [ ] Confirm seconds coercion: `float(seconds)` with `except (TypeError, ValueError): seconds = 2.0`
- [ ] Confirm unknown action returns `f"Skipped unknown action '{action}'."` string

## Task 3: Schema Edge Cases
- [ ] Test plan with `"steps": []` — confirm execute_plan returns empty list, no crash
- [ ] Test step with `"seconds": "2"` (string) — confirm coerced to float 2.0
- [ ] Test step with `"seconds": null` — confirm defaults to 2.0 for motion actions
- [ ] Test step with `"action": "FORWARD"` (uppercase) — confirm dispatched correctly
- [ ] Test step with `"action": "hover"` (unknown) — confirm skip string returned
- [ ] Test step with extra keys `{"action": "stop", "note": "end"}` — confirm no error

## Task 4: Planner Output Validation
- [ ] Submit "Move forward 2 seconds" — confirm plan has `{"action": "forward", "seconds": 2.0}`
- [ ] Submit "Stop" — confirm plan has `{"action": "stop"}` with no `"seconds"` key
- [ ] Submit "Connect to the car" — confirm plan has `{"action": "connect"}` with no `"seconds"` key
- [ ] Submit "Do a full circle" — confirm plan has multiple same-direction turn steps (not a single step)
- [ ] Submit gibberish — confirm plan is a single `{"action": "stop"}` step (safety fallback)

## Task 5: API Response Schema (Web UI)
- [ ] Confirm `/api/plan` response matches `{"plan": {"steps": [...]}}`
- [ ] Confirm `/api/execute` response matches `{"ok": bool, "results": [{"step": int, "action": str, "seconds": float|null, "ok": bool}]}`
- [ ] Confirm `seconds` is `null` in results for `stop` and `connect` steps
