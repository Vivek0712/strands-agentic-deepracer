# Phase 1: DeepRacer Tools — Requirements

## Overview
The `deepracer_tools.py` module provides all hardware-level control of the AWS DeepRacer car. It wraps `aws-deepracer-control-v2` into Strands `@tool`-decorated functions that the agent executor can call.

## Requirements

### REQ-TOOLS-1: Tool Registration
- All six public functions MUST be decorated with `@tool` from `strands`
- Each tool MUST have a docstring that clearly describes its purpose (used as tool description by the agent)

### REQ-TOOLS-2: Client Singleton
- A single `drctl.Client` instance MUST be created lazily on first use
- The singleton MUST be stored as module-level `_CLIENT`
- `_get_client()` MUST raise `RuntimeError` with a clear message if `DEEPRACER_PASSWORD` is not set

### REQ-TOOLS-3: Motor Readiness
- `_ensure_motors_ready(client)` MUST call `client.set_manual_mode()` then `client.start_car()`
- Both calls MUST be wrapped in try/except — failures print a warning but do NOT abort movement
- This function MUST be called before every `client.move()` invocation

### REQ-TOOLS-4: Movement Safety
- `_move_for_duration()` MUST call `client.stop_car()` in a `finally` block
- `client.stop_car()` failure in `finally` MUST return the warning string (not be silently swallowed)
- All movement functions MUST return a descriptive result string

### REQ-TOOLS-5: Throttle Convention
- Forward motion: `throttle = -FWD_THROTTLE` (negative)
- Backward motion: `throttle = +FWD_THROTTLE` (positive)
- Left turn: `steering = -STEER_ANGLE`, `throttle = -TURN_THROTTLE`
- Right turn: `steering = +STEER_ANGLE`, `throttle = -TURN_THROTTLE`

### REQ-TOOLS-6: Connect Tool
- `deepracer_connect()` MUST call `client.show_vehicle_info()` with stdout captured via `redirect_stdout`
- If output is empty, MUST return a fallback string confirming the IP
- MUST NOT print directly to stdout

### REQ-TOOLS-7: Stop Tool
- `deepracer_stop()` MUST call `client.stop_car()` directly (not via `_move_for_duration`)
- MUST return a confirmation string on success

### REQ-TOOLS-8: Configuration
- All tuning constants (`FWD_THROTTLE`, `TURN_THROTTLE`, `MAX_SPEED`, `STEER_ANGLE`) MUST be read from `.env` at module load time
- All MUST have safe numeric defaults
- `IP` defaults to `"192.168.0.3"` if `DEEPRACER_IP` is not set

### REQ-TOOLS-9: Error Handling
- All tool functions MUST return error strings prefixed with `"Error ..."` on failure
- No tool function MUST raise an exception to its caller
