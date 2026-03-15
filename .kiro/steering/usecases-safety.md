---
inclusion: always
---

# Use Cases — Safety Rules (Non-Negotiable)

All Phase 3 safety rules apply. These are the use-cases additions.

## Required Interface Contract
- Every `{use_case}.py` MUST export all 9 functions and 4 physics constants — `validate_tools()` is the gate
- `stop()` MUST always attempt hardware stop even if the connection is degraded — never raise, always return a string
- `is_error(message)` MUST return True for any string starting with "error" (case-insensitive) — never duplicate this logic inline
- `reset_client()` MUST clear the cached connection object and NOT raise — idempotent

## Emergency Stop
- `stop()` is the emergency stop for every use case — it MUST be callable at any time without prior `connect()`
- MAVLink use cases (drone, boat, underwater_rov): `stop()` MUST send zero-velocity/hold before returning
- ROS2 use cases (roomba, lawnmower, hospital_cart, solar_inspection, rover): `stop()` MUST publish zero `/cmd_vel` before returning
- TCP use cases (pipeline_crawler, camera_dolly): `stop()` MUST send stop command; socket errors MUST be caught and logged, not raised

## Error String Convention
- All tool functions return strings — errors MUST start with `"Error"` (capital E) so `is_error()` catches them
- NEVER raise exceptions from tool functions — catch all exceptions and return `f"Error in {func_name}: {exc}"`
- `connect()` returning an error string is valid — the engine will surface it to the user

## Credentials
- Passwords and API keys MUST never appear in return strings, log messages, or error messages
- Each use case reads its own `.env` — never hardcode credentials
- `_get_client()` / `_get_vehicle()` / `_get_ws()` / `_get_sock()` MUST raise `RuntimeError` (not return error string) when required credentials are missing

## Physics Constants
- `PHYSICS_MIN_TURN_RADIUS_M = 0.0` means in-place rotation (differential drive, yaw)
- `PHYSICS_MIN_TURN_RADIUS_M = float("inf")` means no turning (pipeline_crawler)
- These constants are used by the planner prompt — they MUST reflect actual hardware behaviour
- Do NOT change physics constants without re-measuring on the physical hardware

## activate_camera()
- MUST return `True` if the use case has no camera or camera needs no activation
- MUST catch all exceptions and return `False` on failure — never raise
- Camera failure MUST NOT prevent `connect()` from succeeding
