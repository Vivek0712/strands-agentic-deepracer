---
inclusion: fileMatch
fileMatchPattern: "phase-2-strands-robots-deepracer/app_ui.py"
---

# Phase 2: app_ui.py — Coding Standards & Patterns

## Key Differences from Phase 1
- SSE (Server-Sent Events) streaming via `/stream` route — not a simple JSON response
- `/execute` spawns a background thread and returns immediately; progress arrives via SSE
- `/stop` route for emergency hardware stop — sets `_stop_flag` and calls `deepracer_stop()`
- Physics constants imported from `deepracer_tools` and passed to `index.html` template
- `warnings.catch_warnings(record=True)` captures rotation warnings from `validate_plan()`
- `debug=True, threaded=True` — threaded mode required for SSE to work correctly

## Routes
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Render dashboard with physics, patterns, quick prompts |
| `/plan` | POST | Call planner, return `{"ok": bool, "plan": {...}, "warnings": [...]}` |
| `/execute` | POST | Start background execution thread, return `{"ok": true}` immediately |
| `/stop` | POST | Set stop flag + hardware stop, push SSE stopped event |
| `/stream` | GET | SSE generator — yields step events until done/stopped |

## SSE Event Types
| Event | Payload | Meaning |
|---|---|---|
| `start` | `{total, pattern}` | Execution beginning |
| `step` | `{index, action, seconds, ok, message, emergency}` | One step completed |
| `done` | `{ok_count, fail_count}` | All steps finished |
| `stopped` | `{message}` | Aborted by user or error |

## Global State
- `_planner` — singleton, created lazily on first `/plan` request
- `_current_plan` — set by `/plan`, consumed by `/execute`
- `_stop_flag` — `threading.Event`, set by `/stop`, checked in execution thread
- `_sse_queue` — `queue.Queue[str]`, written by execution thread, read by `/stream`

## SSE Queue Management
- `/execute` MUST drain `_sse_queue` before starting a new execution
- `/stream` yields `: heartbeat\n\n` on 15 s timeout to keep connection alive
- `/stream` breaks after yielding a `done` or `stopped` event

## Error Detection in execute thread
- `is_error()` MUST NOT be used directly in `app_ui.py` — use the `ok` field from `execute_plan()` results
- Emergency steps are detected by `message.startswith("[emergency]")`
- `ok = not (message.lower().startswith("error") or is_emergency)` — consistent with agent.py

## Template Context
`index.html` receives: `model`, `min_turn_radius`, `max_corner_speed`, `fwd_speed`, `turn_speed`, `max_step_secs`, `max_plan_steps`, `quick_prompts` (list), `patterns` (list of tuples)
