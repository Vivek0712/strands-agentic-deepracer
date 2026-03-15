# Phase 2 SSE Streaming — Tasks

## Task 1: Verify _sse() and _push() helpers
- [ ] `_sse(event, data)` returns `f"event: {event}\ndata: {json.dumps(data)}\n\n"`
- [ ] `_push(event, data)` calls `_sse_queue.put(_sse(event, data))`
- [ ] Both are module-level functions in app_ui.py

## Task 2: Verify queue drain in /execute
- [ ] `while not _sse_queue.empty():` loop present
- [ ] `_sse_queue.get_nowait()` used inside loop
- [ ] `queue.Empty` exception caught
- [ ] Drain happens BEFORE `_stop_flag.clear()` and thread start

## Task 3: Verify all 4 event types are pushed
- [ ] `start` pushed before first step with `total` and `pattern`
- [ ] `step` pushed for each result with all 6 fields
- [ ] `done` pushed after all steps with `ok_count` and `fail_count`
- [ ] `stopped` pushed on user abort and on step failure abort

## Task 4: Verify /stream generator
- [ ] `mimetype="text/event-stream"` set
- [ ] `Cache-Control: no-cache` header set
- [ ] `X-Accel-Buffering: no` header set
- [ ] `_sse_queue.get(timeout=15)` used
- [ ] `queue.Empty` → yield `: heartbeat\n\n`
- [ ] Break condition: `"event: done" in msg or "event: stopped" in msg`

## Task 5: Verify heartbeat keeps connection alive
- [ ] 15 second timeout is appropriate for typical execution durations
- [ ] Heartbeat is an SSE comment (`: heartbeat`) not a named event
- [ ] Browser EventSource does not fire an event for comments

## Task 6: Test SSE stream with a mock plan
- [ ] Start server with `python app_ui.py`
- [ ] POST /plan with a simple instruction
- [ ] Open /stream in browser or curl
- [ ] POST /execute
- [ ] Verify start → step × N → done events arrive in order

## Task 7: Test emergency stop via SSE
- [ ] POST /execute to start execution
- [ ] POST /stop during execution
- [ ] Verify `stopped` event arrives in stream
- [ ] Verify stream generator breaks after stopped event
