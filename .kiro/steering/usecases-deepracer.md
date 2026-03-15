---
inclusion: fileMatch
fileMatchPattern: "use_cases/deepracer.py"
---

# Use Cases — deepracer.py Reference

## Platform
AWS DeepRacer 1/18-scale RC car · aws-deepracer-control-v2 HTTP API · USB MJPEG camera

## Key Differences from Phase 2/3 deepracer_tools.py
- Functions are NOT `@tool`-decorated — the common engine wraps them via `load_tools()`
- `activate_camera()` is a separate exported function (PUT `/api/vehicle/media_state`)
- `connect()` calls both `show_vehicle_info()` and `activate_camera()` in one step
- `is_error()` also checks for `"[error"` and `"exception"` (broader than Phase 2)

## Hardware Config (env vars)
```
DEEPRACER_IP            192.168.0.3
DEEPRACER_PASSWORD      (required — raises RuntimeError if empty)
DEEPRACER_FWD_THROTTLE  0.30
DEEPRACER_TURN_THROTTLE 0.20
DEEPRACER_MAX_SPEED     1.0
DEEPRACER_STEER_ANGLE   0.50
DEEPRACER_MAX_STEP_SECS 5.0
```

## Physics Constants
```python
PHYSICS_MIN_TURN_RADIUS_M = 0.28   # Ackermann steering — not in-place
PHYSICS_MAX_CORNER_SPEED  = 1.5    # m/s
PHYSICS_FWD_SPEED_MS      = 0.40
PHYSICS_TURN_SPEED_MS     = 0.25
```

## Rotation Calibration
`1.5 s at STEER_ANGLE=0.50, TURN_THROTTLE=0.20 ≈ 90°` (60 °/s)
Do NOT change `STEER_ANGLE` or `TURN_THROTTLE` without re-measuring.

## .env Loading Order
1. `use_cases/common/.env` (base)
2. `use_cases/.env` (override, `override=False` so common wins on conflict)

## _get_client() Rules
- Raises `RuntimeError` if `DEEPRACER_PASSWORD` is empty — never returns None silently
- Cached in module-level `_CLIENT` — call `reset_client()` to force reconnect

## stop() Behaviour
Sends `throttle=0.0, steering=0.0, duration=0.1` — a brief zero-throttle pulse, not a hard stop command. This is intentional for the DeepRacer HTTP API.
