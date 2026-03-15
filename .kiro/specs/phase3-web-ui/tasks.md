# Phase 3 Web UI — Tasks

## Task 1: Verify /frame always returns 200
- [ ] Returns real JPEG when camera has frames
- [ ] Returns _PLACEHOLDER_JPEG when _camera_policy is None
- [ ] Returns _PLACEHOLDER_JPEG when get_latest_frame() returns None
- [ ] Returns _PLACEHOLDER_JPEG when frame bytes are empty
- [ ] Never returns 204 or 404
- [ ] Real frame has Cache-Control: no-store and Content-Length headers
- [ ] Placeholder has X-Frame-Placeholder: true header

## Task 2: Verify /vision_status JSON structure
- [ ] enabled=False when _camera_policy is None
- [ ] running reflects camera_stream.is_running()
- [ ] frames from get_frame_info()[0]
- [ ] staleness rounded to 1 decimal from get_frame_info()[1]
- [ ] error=null when stream is running
- [ ] error from get_error() when stream not running

## Task 3: Verify /reinit route
- [ ] Calls _init() on POST
- [ ] Returns {"ok": true} on success
- [ ] Returns {"ok": false, "error": ...} with HTTP 500 on failure
- [ ] Updates _init_error global

## Task 4: Verify /camera/reconnect route
- [ ] Returns "already running" message if stream is running
- [ ] Calls stream.start() if not running
- [ ] Returns ok=True with frames message if start() returns True
- [ ] Returns ok=False with "no frames yet" message if start() returns False
- [ ] Returns HTTP 500 if _camera_policy is None

## Task 5: Verify _init() error handling
- [ ] Sets _init_error on failure
- [ ] Does not crash Flask on failure
- [ ] _camera_policy and _deepracer_tool remain None on failure
- [ ] /plan and /execute return _phase3_error_message() when not initialised

## Task 6: Verify _PLACEHOLDER_JPEG
- [ ] Valid JPEG bytes (starts with 0xFF 0xD8, ends with 0xFF 0xD9)
- [ ] Decoded from base64 at module load — not per-request
- [ ] Used in /frame when camera unavailable

## Task 7: Verify atexit cleanup
- [ ] _cleanup() registered with atexit
- [ ] Calls _camera_policy.cleanup() on exit
- [ ] Does not raise if _camera_policy is None

## Task 8: Verify SSE vision events in /stream
- [ ] "vision" event displayed in UI step log
- [ ] "replan" event displayed with count and instruction
- [ ] "vision_abort" event displayed with reasoning
- [ ] "start" event includes vision: bool flag
- [ ] "done" event includes replan_count
