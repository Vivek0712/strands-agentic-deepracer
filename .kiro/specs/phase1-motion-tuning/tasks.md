# Phase 1: Motion Tuning — Implementation Tasks

## Task 1: Verify Parameter Application in `deepracer_tools.py`
- [ ] `deepracer_move_forward`: uses `_move_for_duration(0.0, -FWD_THROTTLE, seconds)`
- [ ] `deepracer_move_backward`: uses `_move_for_duration(0.0, FWD_THROTTLE, seconds)`
- [ ] `deepracer_turn_left`: uses `_move_for_duration(-STEER_ANGLE, -TURN_THROTTLE, seconds)`
- [ ] `deepracer_turn_right`: uses `_move_for_duration(STEER_ANGLE, -TURN_THROTTLE, seconds)`
- [ ] `_move_for_duration` passes `MAX_SPEED` as third arg to `client.move()`

## Task 2: Duration Clamping (Enhancement)
- [ ] In `execute_step()`, after resolving `seconds`, clamp: `seconds = min(float(seconds), 10.0)`
- [ ] Log a warning if clamping occurs: `print(f"Warning: clamped duration from {original} to 10.0s")`

## Task 3: PLANNER_PROMPT Duration Rules
- [ ] Confirm PLANNER_PROMPT instructs model to use 1.0–3.0 second durations
- [ ] Confirm PLANNER_PROMPT instructs model to default to ~2.0s when user doesn't specify
- [ ] Confirm PLANNER_PROMPT handles "full circle" as chained same-direction turn steps

## Task 4: Tuning Guide in `.env.example`
- [ ] Add comments explaining what each motion parameter affects physically
- [ ] Add a note that TURN_THROTTLE should be lower than FWD_THROTTLE for tighter turns
- [ ] Add a note that STEER_ANGLE of 0.5 gives moderate turns; increase for sharper turns

## Task 5: Manual Tuning Test
- [ ] Test forward movement at default throttle (0.3) — car should move at moderate speed
- [ ] Test turn at default values — car should arc, not spin in place
- [ ] Increase STEER_ANGLE to 0.8 and test — turn should be sharper
- [ ] Test "do a full circle" prompt — should produce 4–6 chained left or right turn steps
