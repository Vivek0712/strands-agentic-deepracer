# Phase 1: DeepRacer Tools — Implementation Tasks

## Task 1: Module Setup
- [ ] Import `aws_deepracer_control_v2 as drctl`, `strands.tool`, `dotenv`, `os`, `time`, `io`, `contextlib.redirect_stdout`
- [ ] Load `.env` from `Path(__file__).resolve().parent / ".env"` at module level
- [ ] Define constants: `IP`, `PASSWORD`, `FWD_THROTTLE`, `TURN_THROTTLE`, `MAX_SPEED`, `STEER_ANGLE`
- [ ] Initialise `_CLIENT = None`

## Task 2: `_get_client()`
- [ ] Check `PASSWORD` is set — raise `RuntimeError("DEEPRACER_PASSWORD is not set in environment")` if not
- [ ] Create `drctl.Client(password=PASSWORD, ip=IP)` on first call, cache in `_CLIENT`
- [ ] Return `_CLIENT` on subsequent calls

## Task 3: `_ensure_motors_ready(client)`
- [ ] Call `client.set_manual_mode()` in try/except, print warning on failure
- [ ] Call `client.start_car()` in try/except, print warning on failure

## Task 4: `_move_for_duration(steering, throttle, seconds, max_speed=None)`
- [ ] Call `_get_client()` — return error string on failure
- [ ] Call `_ensure_motors_ready(client)`
- [ ] Call `client.move(steering, throttle, max_speed)` then `time.sleep(seconds)`
- [ ] Wrap move+sleep in try/except — return error string on failure
- [ ] Call `client.stop_car()` in `finally` — return warning string if it fails
- [ ] Return descriptive success string with steering, throttle, seconds, max_speed values

## Task 5: `deepracer_connect()`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_get_client()` — return error string on failure
- [ ] Capture `client.show_vehicle_info()` stdout with `io.StringIO` + `redirect_stdout`
- [ ] Return captured output, or fallback `f"Connected to DeepRacer at {IP}."` if empty

## Task 6: `deepracer_move_forward(seconds: float = 2.0)`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_move_for_duration(0.0, -FWD_THROTTLE, seconds)`

## Task 7: `deepracer_move_backward(seconds: float = 2.0)`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_move_for_duration(0.0, FWD_THROTTLE, seconds)`

## Task 8: `deepracer_turn_left(seconds: float = 2.0)`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_move_for_duration(-STEER_ANGLE, -TURN_THROTTLE, seconds)`

## Task 9: `deepracer_turn_right(seconds: float = 2.0)`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_move_for_duration(STEER_ANGLE, -TURN_THROTTLE, seconds)`

## Task 10: `deepracer_stop()`
- [ ] Add `@tool` decorator and docstring
- [ ] Call `_get_client()` — return error string on failure
- [ ] Call `client.stop_car()` — return error string on failure
- [ ] Return `"Sent stop command to DeepRacer."` on success

## Task 11: Verification
- [ ] Confirm all 6 public functions have `@tool` decorator
- [ ] Confirm `_move_for_duration` has `finally: client.stop_car()`
- [ ] Confirm no function raises an exception to its caller
- [ ] Confirm `PASSWORD` check raises `RuntimeError` (not returns error string)
