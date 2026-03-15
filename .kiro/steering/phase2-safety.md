---
inclusion: always
---

# Phase 2 — Safety Rules (Non-Negotiable)

These rules apply to ALL code in phase-2-strands-robots-deepracer. Never weaken them.

## Physical Safety
- `client.stop_car()` MUST be called in a `finally` block inside `_move_for_duration()` — do NOT return inside finally (that was the Phase 1 bug)
- `MAX_STEP_SECONDS` (default 5.0) is a hard cap — `execute_step()` MUST clamp seconds to it; `validate_plan()` MUST reject steps exceeding it
- `stop_on_failure=True` is the default for both `execute_plan()` and `execute_plan_full()` — a failed step MUST trigger an emergency `deepracer_stop()` before aborting
- Every valid plan MUST end with `{"action": "stop"}` — `validate_plan()` MUST reject plans where the last step is not `"stop"`
- Steps with `seconds > MAX_STEP_SECONDS` MUST be rejected by `validate_plan()` with a clear message to split them

## Rotation Safety
- The rotation calibration (1.5 s ≈ 90°) MUST NOT be changed without re-measuring on the physical car
- Changing `DEEPRACER_STEER_ANGLE` or `DEEPRACER_TURN_THROTTLE` invalidates the calibration — the `.env` file MUST warn about this
- `_check_rotation()` emits a warning (not error) when total turn time deviates from expected by > 5° — never suppress this warning

## Confirmation Gate
- CLI: user MUST type `y` or `yes` — any other input cancels
- Web UI: plan MUST be displayed before Execute is clickable
- `DeepRacerTool` `action=execute` is blocking and user-initiated — never auto-trigger it

## Emergency Stop
- `_action_stop()` MUST call `deepracer_stop()` on the hardware regardless of task state
- `_execute_task_async` MUST check `self._shutdown_event.is_set()` at the start of every step loop iteration
- `cleanup()` MUST call `_action_stop()` if status is RUNNING/PLANNING/CONNECTING, then `executor.shutdown()`, then `reset_client()`

## Credentials
- `DEEPRACER_PASSWORD` MUST never be logged, printed, or included in error messages
- `_get_client()` MUST raise `RuntimeError` (not return error string) when password is empty
- `.env` is gitignored — never commit real credentials

## is_error() Convention
- `is_error(message)` in `deepracer_tools.py` is the SINGLE source of truth for error detection
- It checks: `message.lower().startswith("error")` OR `"stop_car failed" in message.lower()`
- All callers MUST use `is_error()` — never duplicate this logic inline
