# Phase 1: Environment Configuration — Implementation Tasks

## Task 1: `.env.example` Maintenance
- [ ] Ensure all 8 variables are documented with comments
- [ ] Ensure `DEEPRACER_PASSWORD` uses `your_password_here` placeholder
- [ ] Ensure all optional variables show their default values in comments
- [ ] Ensure `MODEL` shows the full model ID `us.amazon.nova-lite-v1:0`

## Task 2: `.gitignore` Verification
- [ ] Confirm `.env` is listed in `phase-1-agentic-navigation-planner/.gitignore`
- [ ] Confirm `.env` is NOT listed in `.env.example` (example file is safe to commit)

## Task 3: `deepracer_tools.py` — Env Loading
- [ ] `load_dotenv(Path(__file__).resolve().parent / ".env")` at module level
- [ ] `IP = os.getenv("DEEPRACER_IP", "192.168.0.3")`
- [ ] `PASSWORD = os.getenv("DEEPRACER_PASSWORD")` — no default (None if unset)
- [ ] `FWD_THROTTLE = float(os.getenv("DEEPRACER_FWD_THROTTLE", "0.3"))`
- [ ] `TURN_THROTTLE = float(os.getenv("DEEPRACER_TURN_THROTTLE", "0.2"))`
- [ ] `MAX_SPEED = float(os.getenv("DEEPRACER_MAX_SPEED", "1.0"))`
- [ ] `STEER_ANGLE = float(os.getenv("DEEPRACER_STEER_ANGLE", "0.5"))`

## Task 4: `agent.py` — Env Loading
- [ ] `load_dotenv(Path(__file__).resolve().parent / ".env")` at module level
- [ ] `DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"` as module constant
- [ ] Model resolved in `create_planner()`: arg → `os.getenv("MODEL", DEFAULT_MODEL)`

## Task 5: `main.py` — Env Loading
- [ ] `load_dotenv(Path(__file__).resolve().parent / ".env")` at module level
- [ ] `MODEL = os.getenv("MODEL", DEFAULT_MODEL)` for display in welcome message

## Task 6: Password Validation
- [ ] In `_get_client()`: check `if PASSWORD is None or PASSWORD == ""`
- [ ] Raise `RuntimeError("DEEPRACER_PASSWORD is not set in environment")`
- [ ] Confirm the password value is never included in any log or error string

## Task 7: Verification Checklist
- [ ] Run with `DEEPRACER_PASSWORD` unset — confirm `RuntimeError` is raised
- [ ] Run with invalid float in `DEEPRACER_FWD_THROTTLE` — confirm `ValueError` at startup
- [ ] Confirm `git status` does not show `.env` as a tracked file
- [ ] Confirm `.env.example` is committed and contains all 8 variables
