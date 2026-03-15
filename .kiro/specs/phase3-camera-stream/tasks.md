# Phase 3 Camera Stream — Tasks

## Task 1: Verify start() timeout behaviour
- [ ] Returns True when first frame arrives within START_TIMEOUT_SECS
- [ ] Returns False when no frame arrives within timeout (does not raise)
- [ ] Execution continues after False return — camera is advisory

## Task 2: Verify stop() cleans up correctly
- [ ] Sets _stop_event before joining thread
- [ ] Joins with 3.0 s timeout (does not hang)
- [ ] Sets _thread = None after join

## Task 3: Verify get_latest_frame() is non-blocking
- [ ] Returns None when no frame available (not blocking wait)
- [ ] Returns bytes when frame available
- [ ] Acquires _lock briefly — does not hold it during HTTP I/O

## Task 4: Verify JPEG SOI/EOI extraction
- [ ] Finds SOI at b"\xff\xd8" and EOI at b"\xff\xd9"
- [ ] Extracts buf[soi : eoi + 2] as complete frame
- [ ] Advances buffer to buf[eoi + 2:] after extraction
- [ ] Discards leading garbage before SOI
- [ ] Extracts multiple frames per chunk when buffer contains more than one

## Task 5: Verify _get_response() handles all return types
- [ ] requests.Response with iter_content → used directly
- [ ] str URL → fetched with requests.Session(verify=False)
- [ ] dict with "url" key → URL extracted and fetched
- [ ] dict with "stream_url" key → URL extracted and fetched
- [ ] Unexpected type → raises RuntimeError

## Task 6: Verify reconnect loop
- [ ] _stream_loop catches ALL exceptions from _consume_stream
- [ ] Logs warning with exception message
- [ ] Sleeps RECONNECT_DELAY_SECS before retrying
- [ ] Stops when _stop_event is set

## Task 7: Verify thread safety
- [ ] _latest_frame only written inside _lock
- [ ] _latest_frame only read inside _lock in get_latest_frame()
- [ ] _stop_event checked at top of each chunk iteration

## Task 8: Verify no side effects at import
- [ ] import camera_stream opens no connections
- [ ] CameraStream() constructor opens no connections
- [ ] start() is the only method that opens a connection
