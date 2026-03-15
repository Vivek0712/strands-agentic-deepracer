# Phase 2 DeepRacer Tools — Tasks

## Task 1: Verify is_error() is the single source of truth
- [ ] Confirm `is_error()` checks both `startswith("error")` and `"stop_car failed"`
- [ ] Search all callers — none may duplicate the logic inline
- [ ] Confirm `agent.py` imports `is_error` from `deepracer_tools`
- [ ] Confirm `deepracer_agent_tool.py` imports `is_error` from `deepracer_tools`

## Task 2: Audit _move_for_duration() finally pattern
- [ ] Confirm `finally` block contains only `client.stop_car()` — no `return`
- [ ] Confirm `stop_warning` is declared before the try block as `Optional[str] = None`
- [ ] Confirm `stop_warning` is checked after the try/finally, not inside it
- [ ] Confirm success return string includes steering, throttle, duration, max_speed

## Task 3: Verify reset_client()
- [ ] Confirm `reset_client()` sets `_CLIENT = None`
- [ ] Confirm it is called in `DeepRacerTool.cleanup()` after `executor.shutdown()`
- [ ] Document when to call it: after network drop, HTTP 401/403

## Task 4: Verify physics constants are exported
- [ ] Confirm all four `PHYSICS_*` constants are module-level
- [ ] Confirm `app_ui.py` imports them: `PHYSICS_FWD_SPEED_MS`, `PHYSICS_MAX_CORNER_SPEED`, `PHYSICS_MIN_TURN_RADIUS_M`, `PHYSICS_TURN_SPEED_MS`
- [ ] Confirm values match empirical measurements in docstring

## Task 5: Verify @tool default durations
- [ ] `deepracer_turn_left(seconds: float = 1.5)` — 1.5 s = 90°
- [ ] `deepracer_turn_right(seconds: float = 1.5)` — 1.5 s = 90°
- [ ] `deepracer_move_forward(seconds: float = 2.0)`
- [ ] `deepracer_move_backward(seconds: float = 2.0)`

## Task 6: Verify _get_client() safety
- [ ] Raises `RuntimeError` when `PASSWORD` is empty — not a silent failure
- [ ] Password value never appears in any error message or log line
- [ ] `_CLIENT` is module-level global, cached across calls

## Task 7: Add/extend reset_client() usage documentation
- [ ] Add inline comment explaining when to call `reset_client()`
- [ ] Ensure `.env.example` (if present) warns about calibration sensitivity
