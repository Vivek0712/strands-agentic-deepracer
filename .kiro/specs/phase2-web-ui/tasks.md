# Phase 2 Web UI — Tasks

## Task 1: Verify all 5 routes exist
- [ ] `GET /` → renders index.html
- [ ] `POST /plan` → returns plan JSON
- [ ] `POST /execute` → starts background thread, returns immediately
- [ ] `POST /stop` → hardware stop + SSE stopped event
- [ ] `GET /stream` → SSE generator

## Task 2: Verify template context in GET /
- [ ] `model` passed
- [ ] `min_turn_radius` = PHYSICS_MIN_TURN_RADIUS_M
- [ ] `max_corner_speed` = PHYSICS_MAX_CORNER_SPEED
- [ ] `fwd_speed` = PHYSICS_FWD_SPEED_MS
- [ ] `turn_speed` = PHYSICS_TURN_SPEED_MS
- [ ] `max_step_secs` = MAX_STEP_SECONDS
- [ ] `max_plan_steps` = MAX_PLAN_STEPS
- [ ] `quick_prompts` list has ≥ 10 entries
- [ ] `patterns` list has ≥ 14 entries as (name, description) tuples

## Task 3: Verify POST /plan
- [ ] Empty instruction → 400
- [ ] `warnings.catch_warnings(record=True)` wraps plan_navigation call
- [ ] Warnings returned in response `"warnings"` array
- [ ] `_current_plan` set on success
- [ ] Exception → 500 with error message

## Task 4: Verify POST /execute
- [ ] Returns 400 if `_current_plan` is None
- [ ] Drains `_sse_queue` before starting
- [ ] `_stop_flag.clear()` called
- [ ] Daemon thread spawned
- [ ] Returns `{"ok": true}` immediately (not after execution)

## Task 5: Verify _run() execution thread
- [ ] Pushes `start` event with total steps and pattern
- [ ] Checks `_stop_flag` each iteration
- [ ] Pushes `step` event for each result
- [ ] Emergency detection: `message.startswith("[emergency]")`
- [ ] `ok` computed without calling `is_error()` directly
- [ ] Pushes `done` event when complete
- [ ] Pushes `stopped` event when flag set

## Task 6: Verify POST /stop
- [ ] `_stop_flag.set()` called
- [ ] `deepracer_stop()` called
- [ ] `stopped` SSE event pushed
- [ ] Returns `{"ok": true, "message": "..."}`

## Task 7: Verify GET /stream SSE
- [ ] Content-Type: text/event-stream
- [ ] Cache-Control: no-cache header
- [ ] X-Accel-Buffering: no header
- [ ] Heartbeat on 15 s timeout: `: heartbeat\n\n`
- [ ] Breaks after `done` or `stopped` event

## Task 8: Verify Flask configuration
- [ ] `app.run(debug=True, threaded=True, port=5000)`
- [ ] `threaded=True` is required for SSE to work
