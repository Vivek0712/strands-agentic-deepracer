# Phase 1: Agentic Navigation Planner — Implementation Tasks

## Task 1: Environment & Dependency Setup
- [ ] Copy `.env.example` to `.env` and fill in `DEEPRACER_IP`, `DEEPRACER_PASSWORD`, `AWS_REGION`
- [ ] Optionally set `MODEL`, `DEEPRACER_FWD_THROTTLE`, `DEEPRACER_TURN_THROTTLE`, `DEEPRACER_MAX_SPEED`, `DEEPRACER_STEER_ANGLE`
- [ ] Run `pip install -r requirements.txt` inside `phase-1-agentic-navigation-planner/`
- [ ] Verify AWS credentials are configured for Bedrock access in `AWS_REGION`

## Task 2: DeepRacer Client & Tools (`deepracer_tools.py`)
- [ ] Implement `_get_client()` singleton using `drctl.Client(password=PASSWORD, ip=IP)`
- [ ] Implement `_ensure_motors_ready(client)` calling `set_manual_mode()` and `start_car()` with try/except
- [ ] Implement `_move_for_duration(steering, throttle, seconds, max_speed)` with `finally: stop_car()`
- [ ] Implement `@tool deepracer_connect()` — calls `client.show_vehicle_info()` with stdout capture
- [ ] Implement `@tool deepracer_move_forward(seconds)` — steering=0.0, throttle=-FWD_THROTTLE
- [ ] Implement `@tool deepracer_move_backward(seconds)` — steering=0.0, throttle=+FWD_THROTTLE
- [ ] Implement `@tool deepracer_turn_left(seconds)` — steering=-STEER_ANGLE, throttle=-TURN_THROTTLE
- [ ] Implement `@tool deepracer_turn_right(seconds)` — steering=+STEER_ANGLE, throttle=-TURN_THROTTLE
- [ ] Implement `@tool deepracer_stop()` — calls `client.stop_car()` directly

## Task 3: Planner Agent (`agent.py`)
- [ ] Define `PLANNER_PROMPT` constant with JSON-only output instruction and all action rules
- [ ] Implement `create_planner(model)` returning `strands.Agent(model=m, tools=[], system_prompt=PLANNER_PROMPT)`
- [ ] Implement `plan_navigation(planner, user_request)` with markdown fence stripping and JSON validation
- [ ] Implement `execute_step(step)` dispatching on `action.lower()` with `seconds` defaulting to 2.0
- [ ] Implement `execute_plan(plan)` iterating all steps, returning `List[Tuple[step, result]]`

## Task 4: Terminal REPL (`main.py`)
- [ ] Implement `print_welcome()` showing model name and example prompts
- [ ] Implement `print_help()` with at least 4 example prompts
- [ ] Implement `main()` REPL loop: input → plan → print steps → confirm → execute → print results
- [ ] Handle `exit`, `quit`, `bye`, `help`, `?` commands
- [ ] Handle `KeyboardInterrupt` without crashing
- [ ] Handle planner creation failure with a clear error message

## Task 5: Flask Web UI (`app_ui.py`)
- [ ] Set up Flask app with correct `template_folder` and `static_folder` paths
- [ ] Implement `get_planner()` with `hasattr` singleton caching
- [ ] Implement `GET /` returning `render_template("index.html")`
- [ ] Implement `POST /api/plan` with prompt validation, plan generation, JSON response
- [ ] Implement `POST /api/execute` with plan validation, execution, minimal summary response
- [ ] Ensure `debug=False` on `app.run()`

## Task 6: Web UI Template (`templates/index.html`)
- [ ] Header with Strands × DeepRacer logos and Phase 1 badge
- [ ] Two-column layout: chat panel + plan panel (responsive single-column on mobile)
- [ ] Prompt input + Plan button; disable button during fetch
- [ ] Chat bubbles: user prompt (right-aligned) + agent plan summary (left-aligned)
- [ ] Plan panel: numbered `<ol>` of steps, Execute + Cancel buttons
- [ ] Result box with loading / success / error CSS states
- [ ] Status text element for "Planning…" / "Executing…" feedback
- [ ] Cancel button hides plan panel and clears current plan
- [ ] Execute button POSTs plan to `/api/execute` and shows result

## Task 7: Validation & Safety Checks
- [ ] Verify `stop_car()` is always in a `finally` block in `_move_for_duration`
- [ ] Verify `DEEPRACER_PASSWORD` raises `RuntimeError` when unset
- [ ] Verify plan confirmation cannot be bypassed in both CLI and web UI
- [ ] Verify unknown actions in `execute_step` return a skip message, not an exception
- [ ] Verify `execute_plan` continues after a failed step

## Task 8: Manual Testing
- [ ] Test `python main.py` — "Connect to the car"
- [ ] Test `python main.py` — "Move forward 2 seconds, turn left 1 second, then stop"
- [ ] Test `python main.py` — "Do a full circle"
- [ ] Test `python app_ui.py` — open http://127.0.0.1:5000, submit a prompt, execute plan
- [ ] Test cancellation in both CLI and web UI
- [ ] Test with invalid/empty prompt in web UI
