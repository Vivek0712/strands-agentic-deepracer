# Phase 1: DeepRacer Client — Implementation Tasks

## Task 1: Singleton Pattern
- [ ] Confirm `_CLIENT = None` at module level in `deepracer_tools.py`
- [ ] Confirm `_get_client()` checks `if _CLIENT is None` before creating
- [ ] Confirm `global _CLIENT` is declared inside `_get_client()` before assignment
- [ ] Confirm subsequent calls return the cached `_CLIENT` without re-creating

## Task 2: Client Creation Error Handling
- [ ] Confirm `drctl.Client(password=PASSWORD, ip=IP)` is wrapped in try/except in `_get_client()`
- [ ] Confirm failure returns `f"Error creating DeepRacer client: {exc}"` — wait, _get_client raises RuntimeError for missing password but what about connection errors?
- [ ] Clarify: `_get_client()` raises `RuntimeError` for missing password; callers catch `Exception` from `_get_client()` and return error strings

## Task 3: _ensure_motors_ready()
- [ ] Confirm `client.set_manual_mode()` is in try/except with `print(f"Warning: set_manual_mode failed: {exc}. Continuing.")`
- [ ] Confirm `client.start_car()` is in try/except with `print(f"Warning: start_car failed: {exc}. Continuing.")`
- [ ] Confirm neither failure raises or returns — execution continues to `client.move()`

## Task 4: _move_for_duration() Structure
- [ ] Confirm call order: `_get_client()` → `_ensure_motors_ready()` → `client.move()` → `time.sleep()` → `finally: client.stop_car()`
- [ ] Confirm `client.move(steering, throttle, max_speed)` is in try/except
- [ ] Confirm `time.sleep(float(seconds))` is inside the same try block as `client.move()`
- [ ] Confirm `client.stop_car()` is in `finally:` (not in `else:` or after the try/except)
- [ ] Confirm `stop_car()` failure in finally returns warning string

## Task 5: deepracer_connect() stdout Capture
- [ ] Confirm `buf = io.StringIO()` is created fresh each call
- [ ] Confirm `with redirect_stdout(buf): client.show_vehicle_info()` pattern
- [ ] Confirm `out = buf.getvalue().strip()` extracts the captured output
- [ ] Confirm `return out or f"Connected to DeepRacer at {IP}."` fallback

## Task 6: deepracer_stop() Direct Call
- [ ] Confirm `deepracer_stop()` calls `client.stop_car()` directly (not via `_move_for_duration`)
- [ ] Confirm it does NOT call `_ensure_motors_ready()` (stop should work regardless of mode)
- [ ] Confirm it returns `"Sent stop command to DeepRacer."` on success

## Task 7: Integration Smoke Test
- [ ] With car powered on and correct .env: run `python -c "from deepracer_tools import deepracer_connect; print(deepracer_connect())"`
- [ ] Confirm output shows vehicle info or fallback connection string
- [ ] With wrong IP: confirm error string is returned (not an unhandled exception)
- [ ] With missing password: confirm RuntimeError is raised with clear message
