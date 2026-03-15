# Tasks: Use Cases Tool Interface Contract

## Task 1: Audit All Existing Use Cases
- [ ] For each file in `use_cases/*.py` (excluding `common/`), run `validate_tools(load_tools(name))`
- [ ] Confirm all 9 functions present
- [ ] Confirm all 4 physics constants present
- [ ] Confirm `PLATFORM_NAME` and `PLATFORM_DESC` present (optional but recommended)

## Task 2: Verify Error String Convention
- [ ] For each use case, confirm every tool function wraps its body in `try/except`
- [ ] Confirm error returns start with `"Error in {func_name}: "`
- [ ] Confirm `is_error()` returns True for those strings
- [ ] Confirm no tool function raises to the caller

## Task 3: Verify stop() Safety
- [ ] Call `stop()` on each use case before `connect()` — must not raise
- [ ] Confirm `stop()` sends hardware stop command (or zero-velocity for ROS2/MAVLink)
- [ ] Confirm `stop()` catches socket/connection errors and returns error string

## Task 4: Verify reset_client() Idempotency
- [ ] Call `reset_client()` twice in a row — must not raise
- [ ] Call `reset_client()` before `connect()` — must not raise
- [ ] Confirm cached connection object is cleared after call

## Task 5: Verify activate_camera()
- [ ] Confirm use cases with no camera return `True` immediately
- [ ] Confirm use cases with camera activation catch exceptions and return `False`
- [ ] Confirm `connect()` succeeds even when `activate_camera()` returns `False`

## Task 6: Physics Constants Accuracy
- [ ] Review each use case's physics constants against documented hardware specs
- [ ] Flag any constants that appear to be placeholder values (e.g. all 1.0)
- [ ] Confirm `PHYSICS_MIN_TURN_RADIUS_M = float("inf")` for pipeline_crawler and camera_dolly
- [ ] Confirm `PHYSICS_MIN_TURN_RADIUS_M = 0.0` for all ROS2 differential-drive use cases
