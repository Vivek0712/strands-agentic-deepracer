# Phase 2 Web UI — Requirements

## Overview
Flask web UI (`app_ui.py`) providing a dashboard for the navigation planner with
SSE-based real-time step streaming, physics display, pattern reference, quick prompts,
and emergency stop. Runs at http://127.0.0.1:5000.

## Functional Requirements

### FR-1: Routes
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Render dashboard with physics, patterns, quick prompts |
| `/plan` | POST | Call planner, return plan JSON + warnings |
| `/execute` | POST | Start background execution, return immediately |
| `/stop` | POST | Emergency stop — set flag + hardware stop |
| `/stream` | GET | SSE generator — yields events until done/stopped |

### FR-2: GET / — Dashboard
- Renders `templates/index.html` with template context:
  - `model` — active model ID
  - `min_turn_radius`, `max_corner_speed`, `fwd_speed`, `turn_speed` — from `PHYSICS_*` constants
  - `max_step_secs`, `max_plan_steps` — from agent.py constants
  - `quick_prompts` — list of 12 example instructions
  - `patterns` — list of (name, description) tuples for all 14 patterns

### FR-3: POST /plan
- Reads `instruction` from JSON body
- Returns 400 if instruction is empty
- Calls `plan_navigation(_get_planner(), instruction)` with `warnings.catch_warnings(record=True)`
- Returns `{"ok": true, "plan": {...}, "warnings": [...]}` on success
- Returns `{"ok": false, "error": "..."}` with 500 on exception
- Stores plan in `_current_plan` global

### FR-4: POST /execute
- Returns 400 if `_current_plan` is None
- Drains `_sse_queue` before starting
- Clears `_stop_flag`
- Spawns daemon thread running `_run()` closure
- Returns `{"ok": true}` immediately

### FR-5: POST /stop
- Sets `_stop_flag`
- Calls `deepracer_stop()` on hardware
- Pushes `stopped` SSE event with message
- Returns `{"ok": true, "message": "..."}`

### FR-6: GET /stream — SSE
- Returns `text/event-stream` response with `Cache-Control: no-cache` and `X-Accel-Buffering: no`
- Yields events from `_sse_queue` with 15 s timeout
- Yields `: heartbeat\n\n` on timeout to keep connection alive
- Breaks after yielding `done` or `stopped` event

### FR-7: SSE Event Types
| Event | Payload fields | Meaning |
|---|---|---|
| `start` | `total`, `pattern` | Execution beginning |
| `step` | `index`, `action`, `seconds`, `ok`, `message`, `emergency` | One step completed |
| `done` | `ok_count`, `fail_count` | All steps finished |
| `stopped` | `message` | Aborted by user or error |

### FR-8: Global State
- `_planner` — singleton, created lazily on first `/plan` request via `_get_planner()`
- `_current_plan` — set by `/plan`, consumed by `/execute`
- `_stop_flag` — `threading.Event`, set by `/stop`, checked in execution thread
- `_sse_queue: queue.Queue[str]` — written by execution thread, read by `/stream`

### FR-9: Execution Thread (_run closure)
- Iterates `execute_plan(plan, stop_on_failure=True)` results
- Checks `_stop_flag` each iteration — pushes `stopped` event and breaks if set
- Detects emergency steps by `message.startswith("[emergency]")`
- `ok = not (message.lower().startswith("error") or is_emergency)`
- Pushes `done` event when all steps complete without abort

### FR-10: Rotation Warnings
- `warnings.catch_warnings(record=True)` wraps `plan_navigation()` call
- Captured warnings returned in `"warnings"` array of `/plan` response
- Browser can display rotation mismatch warnings to the user

## Non-Functional Requirements
- NFR-1: `debug=True, threaded=True` — threaded mode required for SSE
- NFR-2: `is_error()` MUST NOT be imported or used directly in app_ui.py
- NFR-3: Emergency stop must work even if execution thread is not running
- NFR-4: Queue must be drained before each new execution to prevent stale events
