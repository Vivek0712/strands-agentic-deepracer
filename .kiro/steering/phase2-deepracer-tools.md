---
inclusion: fileMatch
fileMatchPattern: "phase-2-strands-robots-deepracer/deepracer_tools.py"
---

# Phase 2: deepracer_tools.py — Coding Standards & Patterns

## Key Differences from Phase 1
- `is_error(message)` is a module-level helper — the single source of truth for error detection
- `reset_client()` is a public function — call it after network drops or HTTP 401/403
- `_move_for_duration()` fixes the Phase 1 finally-block bug: never `return` inside `finally`
- `stop_warning` local variable captures any stop_car failure; returned AFTER the success path
- Default turn duration is `1.5` s (not `2.0` s) — matches the 90° calibration constant
- Physics constants are module-level (`PHYSICS_*`) — informational, enforced upstream in agent.py

## is_error() — Single Source of Truth
```python
def is_error(message: str) -> bool:
    low = message.lower()
    return low.startswith("error") or "stop_car failed" in low
```
- All callers (agent.py, deepracer_agent_tool.py, app_ui.py) MUST import and use this
- Never duplicate the logic inline

## _move_for_duration() — Fixed finally Pattern
```python
stop_warning: Optional[str] = None
try:
    client.move(steering, throttle, _max_speed)
    time.sleep(float(seconds))
except Exception as exc:
    return f"Error during move (...): {exc}"
finally:
    try:
        client.stop_car()
    except Exception as exc:
        stop_warning = f"Warning: stop_car() failed after move: {exc}"

if stop_warning:
    return stop_warning
return f"Moved: steering=... throttle=... duration=...s max_speed=..."
```
- The `finally` block MUST NOT contain a `return` statement
- `stop_warning` is checked AFTER the try/finally, not inside it

## reset_client()
- Sets `_CLIENT = None` — forces fresh TCP connection on next `_get_client()` call
- Called by `DeepRacerTool.cleanup()` after executor shutdown
- Also useful after HTTP 401/403 or network drop

## Physics Constants
- `PHYSICS_MIN_TURN_RADIUS_M = 0.28` — informational only, enforced by throttle settings
- `PHYSICS_MAX_CORNER_SPEED = 1.5` — enforced by keeping TURN_THROTTLE low
- `PHYSICS_FWD_SPEED_MS = 0.40` — approximate at FWD_THROTTLE=0.30
- `PHYSICS_TURN_SPEED_MS = 0.25` — approximate at TURN_THROTTLE=0.20
- These are exported and used by `app_ui.py` for the dashboard display

## Tool Default Durations
- `deepracer_turn_left(seconds: float = 1.5)` — 1.5 s default (= 90°)
- `deepracer_turn_right(seconds: float = 1.5)` — 1.5 s default (= 90°)
- `deepracer_move_forward(seconds: float = 2.0)` — 2.0 s default
- `deepracer_move_backward(seconds: float = 2.0)` — 2.0 s default

## Throttle Sign Convention (unchanged from Phase 1)
| Direction | steering | throttle |
|---|---|---|
| forward | 0.0 | -FWD_THROTTLE |
| backward | 0.0 | +FWD_THROTTLE |
| left | -STEER_ANGLE | -TURN_THROTTLE |
| right | +STEER_ANGLE | -TURN_THROTTLE |
