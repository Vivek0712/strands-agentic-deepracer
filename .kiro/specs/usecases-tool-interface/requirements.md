# Spec: Use Cases Tool Interface Contract

## Overview
Every `{use_case}.py` file must satisfy a strict interface so the common engine can drive any robot without modification.

## Requirements

### REQ-1: Required Functions
Every use case MUST export these 9 callable functions:

| Function | Signature | Return |
|----------|-----------|--------|
| `connect` | `() -> str` | Status string or `"Error: ..."` |
| `move_forward` | `(seconds: float) -> str` | Result string or `"Error in move_forward: ..."` |
| `move_backward` | `(seconds: float) -> str` | Result string or `"Error in move_backward: ..."` |
| `turn_left` | `(seconds: float) -> str` | Result string or `"Error in turn_left: ..."` |
| `turn_right` | `(seconds: float) -> str` | Result string or `"Error in turn_right: ..."` |
| `stop` | `() -> str` | Result string or `"Error in stop: ..."` |
| `is_error` | `(message: str) -> bool` | True if message indicates failure |
| `reset_client` | `() -> None` | None — clears cached connection |
| `activate_camera` | `() -> bool` | True on success or if no camera |

### REQ-2: Required Physics Constants
Every use case MUST export these 4 float constants:

| Name | Meaning |
|------|---------|
| `PHYSICS_MIN_TURN_RADIUS_M` | Min arc radius in metres; `0.0` = in-place; `float("inf")` = no turning |
| `PHYSICS_MAX_CORNER_SPEED` | Max safe speed during turns (m/s) |
| `PHYSICS_FWD_SPEED_MS` | Typical forward speed (m/s) |
| `PHYSICS_TURN_SPEED_MS` | Typical turning speed (m/s); `0.0` for in-place yaw |

### REQ-3: Error String Convention
- All tool functions MUST catch all exceptions and return `f"Error in {func_name}: {exc}"`
- Error strings MUST start with `"Error"` (capital E) — `is_error()` checks `startswith("error")` case-insensitively
- Tool functions MUST NEVER raise to the caller

### REQ-4: stop() Safety
- `stop()` MUST be callable at any time, even before `connect()`
- `stop()` MUST attempt hardware stop even if connection is degraded
- `stop()` MUST catch all exceptions and return an error string — never raise

### REQ-5: reset_client() Contract
- MUST clear the cached connection object
- MUST be idempotent — safe to call multiple times
- MUST NOT raise

### REQ-6: activate_camera() Contract
- MUST return `True` if the use case has no camera
- MUST catch all exceptions and return `False` on failure
- Camera failure MUST NOT prevent `connect()` from succeeding

### REQ-7: Optional Metadata
Use cases MAY export:
- `PLATFORM_NAME: str` — shown in dashboard title
- `PLATFORM_DESC: str` — shown in dashboard subtitle
