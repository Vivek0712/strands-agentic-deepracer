# Phase 2 Web UI — Design

## Architecture

```
Browser
  │
  ├─ GET /          → index.html (physics dashboard, pattern list, quick prompts)
  │
  ├─ POST /plan     → JSON body: {instruction}
  │                   Response: {ok, plan, warnings}
  │                   Side effect: _current_plan = plan
  │
  ├─ POST /execute  → No body
  │                   Response: {ok: true}  (immediate)
  │                   Side effect: spawns _run() daemon thread
  │
  ├─ GET /stream    → SSE stream
  │                   Reads from _sse_queue
  │                   Yields: start → step × N → done|stopped
  │
  └─ POST /stop     → No body
                      Response: {ok, message}
                      Side effect: _stop_flag.set() + deepracer_stop()
```

## Global State Lifecycle

```
Startup:
  _planner = None          (lazy init on first /plan)
  _current_plan = None
  _stop_flag = Event()     (cleared)
  _sse_queue = Queue()     (empty)

/plan request:
  _planner = _get_planner()   (creates if None)
  _current_plan = plan_data

/execute request:
  drain _sse_queue
  _stop_flag.clear()
  thread = Thread(target=_run)
  thread.start()
  return {ok: true}

_run() thread:
  _push("start", ...)
  for step, message in execute_plan(plan):
    if _stop_flag.is_set(): _push("stopped"); break
    _push("step", ...)
    if not ok: break
  _push("done", ...)

/stop request:
  _stop_flag.set()
  deepracer_stop()
  _push("stopped", ...)
```

## SSE Wire Format

Each event is formatted as:
```
event: <type>\ndata: <json>\n\n
```

Example sequence:
```
event: start
data: {"total": 5, "pattern": "square"}

event: step
data: {"index": 1, "action": "forward", "seconds": 2.0, "ok": true, "message": "Moved: ...", "emergency": false}

event: step
data: {"index": 2, "action": "right", "seconds": 1.5, "ok": true, "message": "Moved: ...", "emergency": false}

event: done
data: {"ok_count": 5, "fail_count": 0}
```

## Template Context

`index.html` receives all physics constants and pattern data at render time:
- Physics values displayed in a dashboard panel
- Patterns listed as clickable quick-select buttons
- Quick prompts listed as one-click fill buttons
- SSE events update a live step log in the UI

## Error Handling

| Scenario | Behaviour |
|---|---|
| Empty instruction | 400 + `{"ok": false, "error": "No instruction provided."}` |
| Planning exception | 500 + `{"ok": false, "error": str(exc)}` |
| No current plan | 400 + `{"ok": false, "error": "No plan. Get a plan first."}` |
| Hardware stop fails | Error message included in stop response, not raised |
| SSE timeout (15 s) | Heartbeat comment sent to keep connection alive |
