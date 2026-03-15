# Phase 1: DeepRacer Client (aws-deepracer-control-v2) — Requirements

## Overview
The `aws-deepracer-control-v2` library is the sole interface between Phase 1 code and the physical DeepRacer car. This spec covers correct usage of the library's API.

## Requirements

### REQ-CLIENT-1: Instantiation
- Client MUST be created with `drctl.Client(password=PASSWORD, ip=IP)`
- Client MUST be a module-level singleton — created once, reused across all tool calls
- Client MUST NOT be recreated on every tool call (expensive, causes connection churn)

### REQ-CLIENT-2: Manual Mode
- `client.set_manual_mode()` MUST be called before every movement sequence
- This call MUST be wrapped in try/except — failure prints a warning but does not abort
- Purpose: switches the car out of autonomous/racing mode into manual control

### REQ-CLIENT-3: Motor Start
- `client.start_car()` MUST be called before every movement sequence
- This call MUST be wrapped in try/except — failure prints a warning but does not abort
- Purpose: arms the motors so movement commands are accepted

### REQ-CLIENT-4: Movement
- `client.move(steering, throttle, max_speed)` sends a single movement command
- The car continues moving until `stop_car()` is called or another `move()` is issued
- `time.sleep(seconds)` MUST be called after `move()` to hold the movement for the desired duration
- `client.move()` MUST be wrapped in try/except — failure returns an error string

### REQ-CLIENT-5: Stop
- `client.stop_car()` MUST be called in a `finally` block after every `client.move()` + `time.sleep()`
- `client.stop_car()` MAY also be called directly by `deepracer_stop()`
- A failed `stop_car()` in `finally` MUST return a warning string — never silently pass

### REQ-CLIENT-6: Vehicle Info
- `client.show_vehicle_info()` prints vehicle info (battery, etc.) to stdout
- Output MUST be captured with `io.StringIO` + `contextlib.redirect_stdout`
- If output is empty after capture, return a fallback connection confirmation string

### REQ-CLIENT-7: Connection Errors
- If `drctl.Client(...)` raises, return `f"Error creating DeepRacer client: {exc}"`
- If `client.move(...)` raises, return `f"Error during move: {exc}"`
- If `client.stop_car()` raises in finally, return `f"Warning: stop_car failed after move: {exc}"`
- If `client.stop_car()` raises in `deepracer_stop()`, return `f"Error calling stop_car: {exc}"`
- If `client.show_vehicle_info()` raises, return `f"Error calling show_vehicle_info: {exc}"`
