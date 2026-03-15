# Phase 2 Environment Config — Tasks

## Task 1: Verify DEEPRACER_MAX_STEP_SECS is loaded correctly
- [ ] `agent.py`: `MAX_STEP_SECONDS = float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))`
- [ ] Default is 5.0 (not 10.0 from Phase 1)
- [ ] Used in `validate_plan()` for rejection
- [ ] Used in `execute_step()` for clamping

## Task 2: Verify all 9 variables are present in .env
- [ ] MODEL
- [ ] DEEPRACER_IP
- [ ] DEEPRACER_PASSWORD
- [ ] AWS_REGION
- [ ] DEEPRACER_MAX_STEP_SECS
- [ ] DEEPRACER_FWD_THROTTLE
- [ ] DEEPRACER_TURN_THROTTLE
- [ ] DEEPRACER_MAX_SPEED
- [ ] DEEPRACER_STEER_ANGLE

## Task 3: Verify calibration warning comment in .env
- [ ] Warning mentions DEEPRACER_STEER_ANGLE
- [ ] Warning mentions DEEPRACER_TURN_THROTTLE
- [ ] Warning mentions "1.5 s ≈ 90°" calibration
- [ ] Warning says to re-measure on physical car

## Task 4: Verify .env is gitignored
- [ ] `.gitignore` in phase-2-strands-robots-deepracer/ contains `.env`
- [ ] No `.env` file with real credentials in git history

## Task 5: Verify load_dotenv path resolution
- [ ] `deepracer_tools.py`: `load_dotenv(Path(__file__).resolve().parent / ".env")`
- [ ] `agent.py`: same pattern
- [ ] `deepracer_agent_tool.py`: same pattern
- [ ] `app_ui.py`: same pattern
- [ ] `main.py`: same pattern

## Task 6: Verify float parsing for all numeric vars
- [ ] `FWD_THROTTLE = float(os.getenv("DEEPRACER_FWD_THROTTLE", "0.30"))`
- [ ] `TURN_THROTTLE = float(os.getenv("DEEPRACER_TURN_THROTTLE", "0.20"))`
- [ ] `MAX_SPEED = float(os.getenv("DEEPRACER_MAX_SPEED", "1.0"))`
- [ ] `STEER_ANGLE = float(os.getenv("DEEPRACER_STEER_ANGLE", "0.50"))`
- [ ] `MAX_STEP_SECONDS = float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))`

## Task 7: Test with missing DEEPRACER_PASSWORD
- [ ] Start app without PASSWORD set
- [ ] Confirm no error at import time
- [ ] Confirm RuntimeError raised only when connection is attempted
- [ ] Confirm error message does NOT include the password value
