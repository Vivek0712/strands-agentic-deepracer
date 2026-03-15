# Phase 2 DeepRacer Tools — Requirements

## Overview
Hardware interface module for the AWS DeepRacer. Provides @tool-decorated functions,
physics constants, the fixed `_move_for_duration()` finally pattern, `is_error()` as
single source of truth for error detection, and `reset_client()` for network recovery.

## Functional Requirements

### FR-1: is_error() — Single Source of Truth
- `is_error(message: str) -> bool` MUST be a module-level function
- Returns True when `message.lower().startswith("error")` OR `"stop_car failed" in message.lower()`
- All callers (agent.py, deepracer_agent_tool.py, app_ui.py) MUST import and use this function
- No caller may duplicate this logic inline

### FR-2: Fixed finally Pattern in _move_for_duration()
- `client.stop_car()` MUST be called in the `finally` block
- The `finally` block MUST NOT contain a `return` statement (this was the Phase 1 bug)
- A `stop_warning: Optional[str]` local variable captures any stop_car failure
- `stop_warning` is checked AFTER the try/finally block, not inside it
- On success: returns a formatted string with steering, throttle, duration, max_speed
- On stop_car failure: returns the warning string

### FR-3: reset_client()
- `reset_client()` sets `_CLIENT = None`, forcing a fresh TCP connection on next call
- Called by `DeepRacerTool.cleanup()` after executor shutdown
- Also useful after HTTP 401/403 or network drop

### FR-4: Physics Constants
- `PHYSICS_MIN_TURN_RADIUS_M = 0.28` — minimum turning radius in metres
- `PHYSICS_MAX_CORNER_SPEED = 1.5` — max safe corner speed in m/s
- `PHYSICS_FWD_SPEED_MS = 0.40` — approximate forward speed at FWD_THROTTLE=0.30
- `PHYSICS_TURN_SPEED_MS = 0.25` — approximate turn speed at TURN_THROTTLE=0.20
- All four constants are exported and imported by `app_ui.py` for the dashboard

### FR-5: @tool Functions
- `deepracer_connect()` — health-check, returns vehicle info or error string
- `deepracer_move_forward(seconds: float = 2.0)` — straight forward
- `deepracer_move_backward(seconds: float = 2.0)` — straight reverse
- `deepracer_turn_left(seconds: float = 1.5)` — arc left (1.5 s default = 90°)
- `deepracer_turn_right(seconds: float = 1.5)` — arc right (1.5 s default = 90°)
- `deepracer_stop()` — immediate halt, used as final step and emergency abort

### FR-6: Throttle Sign Convention
| Direction | steering | throttle |
|---|---|---|
| forward | 0.0 | -FWD_THROTTLE |
| backward | 0.0 | +FWD_THROTTLE |
| left | -STEER_ANGLE | -TURN_THROTTLE |
| right | +STEER_ANGLE | -TURN_THROTTLE |

### FR-7: _get_client()
- Returns cached `_CLIENT`, creating one if needed
- MUST raise `RuntimeError` (not return error string) when `PASSWORD` is empty
- Never logs or prints the password value

### FR-8: _ensure_motors_ready()
- Calls `set_manual_mode()` and `start_car()` on the client
- Failures are printed as warnings; execution continues (best-effort)

## Non-Functional Requirements
- NFR-1: `DEEPRACER_PASSWORD` must never appear in logs, error messages, or return values
- NFR-2: `.env` is gitignored — never commit real credentials
- NFR-3: All tool functions return strings — never raise to callers
- NFR-4: Physics constants are informational — enforcement happens upstream in agent.py
