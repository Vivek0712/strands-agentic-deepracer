---
inclusion: fileMatch
fileMatchPattern: "phase-3-adaptive-visual-navigation/app_ui.py"
---

# Phase 3: app_ui.py — Steering

## Phase 3 Routes
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Dashboard (index.html) |
| `/plan` | POST | LLM plan via CameraPolicy → JSON; stores `_instruction_hint` |
| `/execute` | POST | Run approved `_current_plan` via `_execute_approved_plan()` in daemon thread |
| `/stop` | POST | Emergency stop — calls `_action_stop()` + `deepracer_stop()` |
| `/stream` | GET | SSE: start · step · vision · replan · vision_abort · done · stopped |
| `/frame` | GET | Latest JPEG from camera (always 200 — placeholder if unavailable) |
| `/vision_status` | GET | Camera health JSON: enabled, running, frames, staleness, error |
| `/reinit` | POST | Retry Phase 3 init without server restart |
| `/camera/reconnect` | POST | Restart camera stream if stopped |

## Singletons
- `_camera_policy: CameraPolicy` — created by `_init()` at startup
- `_deepracer_tool: DeepRacerTool` — created by `_init()`, receives `_event_cb`
- `_current_plan: dict` — set by `/plan`, consumed by `/execute`
- `_sse_queue: queue.Queue` — written by `_event_cb`, read by `/stream`
- `_init_error: Optional[str]` — set if `_init()` fails; returned in `/plan` and `/execute` errors

## /frame Route
- Returns `_camera_policy.camera_stream.get_latest_frame()` as `image/jpeg`
- Falls back to `_PLACEHOLDER_JPEG` (1×1 gray JPEG) when camera unavailable
- Always returns HTTP 200 — never 204 or 404
- Headers: `Cache-Control: no-store`, `Content-Length` on real frames
- Placeholder header: `X-Frame-Placeholder: true`

## /vision_status Route
```json
{
  "enabled": true,
  "running": true,
  "frames": 142,
  "staleness": 0.3,
  "error": null
}
```
- `staleness` = seconds since last frame (from `get_frame_info()`)
- `error` = `get_error()` when stream not running, else null

## /execute Route
- Drains `_sse_queue` before starting (removes stale events from previous run)
- Runs `asyncio.run(_deepracer_tool._execute_approved_plan(plan))` in daemon thread
- Thread name: `"phase3_exec"`

## SSE /stream Route
- Blocks on `_sse_queue.get(timeout=15)` — yields events instantly
- Sends `: heartbeat\n\n` every 15 s to keep connection alive
- Closes after "done" or "stopped" event

## Startup / Cleanup
- `_init()` called at module load — sets `_init_error` on failure (does not crash)
- `atexit.register(_cleanup)` — calls `_camera_policy.cleanup()` on exit
- `/reinit` POST — retries `_init()` after fixing `.env`

## Inherited Phase 2 Rules (all still apply)
- SSE queue drain before each new execution
- `/stop` pushes "stopped" event to SSE queue
- `threaded=True` required for SSE
- `is_error()` NOT imported in `app_ui.py` — error detection is in `deepracer_tools.py`
