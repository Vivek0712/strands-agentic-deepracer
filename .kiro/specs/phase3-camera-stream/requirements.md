# Phase 3 Camera Stream — Requirements

## Overview
`camera_stream.py` provides a background MJPEG frame buffer for Phase 3.
A daemon thread continuously reads the DeepRacer camera stream and keeps
the latest decoded JPEG frame in memory. `get_latest_frame()` is non-blocking.

## Functional Requirements

### FR-1: CameraStream.start()
- Starts a daemon thread named `"camera_stream"`
- Blocks up to `START_TIMEOUT_SECS` (15.0 s) polling for the first frame
- Returns `True` if at least one frame was received within the timeout
- Returns `False` if timeout elapsed with no frame — execution continues either way
- If thread is already running, returns immediately based on whether a frame exists

### FR-2: CameraStream.stop()
- Sets `_stop_event`
- Joins the thread with a 3.0 s timeout
- Sets `_thread = None`

### FR-3: CameraStream.get_latest_frame() -> Optional[bytes]
- Returns raw JPEG bytes of the most recent frame, or None
- Non-blocking — acquires `_lock` briefly and returns
- Returns None if stream has not started or no frames received yet

### FR-4: CameraStream.get_frame_info() -> Tuple[int, float]
- Returns `(frame_count, seconds_since_last_frame)`
- `seconds_since_last_frame` is `float("inf")` if no frame ever received

### FR-5: CameraStream.is_running() -> bool
- Returns True if the daemon thread is alive

### FR-6: CameraStream.get_error() -> Optional[str]
- Returns the last stream error string, or None

### FR-7: JPEG Frame Extraction
- Uses SOI marker `b"\xff\xd8"` and EOI marker `b"\xff\xd9"` — NOT multipart boundary parsing
- Accumulates chunks in a buffer; extracts all complete frames per chunk
- Complete frame: `buf[soi : eoi + 2]`; buffer advanced to `buf[eoi + 2:]`
- Leading garbage before SOI is discarded

### FR-8: _get_response()
- Calls `_get_client().get_raw_video_stream()`
- Handles three return types:
  - `requests.Response` with `iter_content` — used directly
  - `str` URL — fetched with `requests.Session(verify=False)`
  - `dict` with `url`/`stream_url`/`video_url` key — URL extracted then fetched
- Raises `RuntimeError` on unexpected return type (caught by `_stream_loop`)

### FR-9: Reconnect Loop
- `_stream_loop()` wraps `_consume_stream()` in try/except
- On exception: logs warning, sleeps `RECONNECT_DELAY_SECS` (2.0 s), retries
- Stops when `_stop_event.is_set()`

### FR-10: Thread Safety
- `_latest_frame` protected by `threading.Lock()` (`_lock`)
- `_stop_event` checked at top of each chunk iteration in `_consume_stream()`

## Non-Functional Requirements
- NFR-1: `urllib3.InsecureRequestWarning` suppressed at import time
- NFR-2: Thread is `daemon=True` — dies automatically when main process exits
- NFR-3: `CHUNK_BYTES = 1024` — small chunks for frequent SOI/EOI checks
- NFR-4: No side effects at import time — no connections opened
