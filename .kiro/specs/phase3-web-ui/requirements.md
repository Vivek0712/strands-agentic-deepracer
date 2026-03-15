# Phase 3 Web UI — Requirements

## Overview
`app_ui.py` extends the Phase 2 Flask web UI with camera feed, vision status,
and recovery routes. The UI polls `/frame` at 2 Hz for the live camera image
and receives vision events via the existing SSE `/stream` endpoint.

## Functional Requirements

### FR-1: /frame route
- GET — returns latest JPEG from `_camera_policy.camera_stream.get_latest_frame()`
- Always returns HTTP 200 — never 204 or 404
- Falls back to `_PLACEHOLDER_JPEG` (1×1 gray JPEG, base64-decoded at startup) when:
  - `_camera_policy` is None
  - `get_latest_frame()` returns None
  - Frame bytes are empty
- Real frame headers: `Cache-Control: no-store`, `Content-Length: {len(jpeg)}`
- Placeholder header: `X-Frame-Placeholder: true`

### FR-2: /vision_status route
- GET — returns JSON health check
```json
{
  "enabled": true,
  "running": true,
  "frames": 142,
  "staleness": 0.3,
  "error": null
}
```
- `enabled`: False when `_camera_policy` is None
- `running`: `camera_stream.is_running()`
- `frames`: `camera_stream.get_frame_info()[0]`
- `staleness`: `round(camera_stream.get_frame_info()[1], 1)`
- `error`: `get_error()` when not running, else null

### FR-3: /reinit route
- POST — retries `_init()` without server restart
- Returns `{"ok": true, "message": "Phase 3 initialised."}` on success
- Returns `{"ok": false, "error": str(exc)}` with HTTP 500 on failure
- Updates `_init_error` global

### FR-4: /camera/reconnect route
- POST — restarts camera stream if stopped
- Returns `{"ok": true, "message": "Camera stream already running."}` if already running
- Calls `stream.start()` and returns ok/message based on result
- Returns HTTP 500 if `_camera_policy` is None

### FR-5: _init() function
- Creates `CameraPolicy` via `create_camera_policy()`
- Creates `DeepRacerTool` with `event_callback=_event_cb`
- Sets `_init_error = None` on success
- Called at module load — sets `_init_error` on failure (does not crash Flask)

### FR-6: _PLACEHOLDER_JPEG
- Minimal 1×1 gray JPEG, base64-decoded at module load
- Used as fallback in /frame when camera unavailable
- Ensures browser `<img>` tag always has valid content

### FR-7: Startup / cleanup
- `_init()` called at module load in try/except
- `atexit.register(_cleanup)` — calls `_camera_policy.cleanup()` on exit
- `/reinit` POST allows recovery without restart

## Non-Functional Requirements
- NFR-1: All Phase 2 routes (/plan, /execute, /stop, /stream) unchanged in behaviour
- NFR-2: SSE queue drained before each new /execute call
- NFR-3: `threaded=True` required for SSE — unchanged from Phase 2
- NFR-4: `_event_cb` named function (not lambda) passed to DeepRacerTool
