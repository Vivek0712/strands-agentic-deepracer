---
inclusion: fileMatch
fileMatchPattern: "phase-3-adaptive-visual-navigation/camera_stream.py"
---

# Phase 3: camera_stream.py — Steering

## Purpose
Background MJPEG consumer. Runs a daemon thread that continuously reads the
DeepRacer camera stream and keeps the latest decoded JPEG frame in memory.
`get_latest_frame()` is non-blocking — callers get the frame instantly.

## Class: CameraStream

### Key Methods
- `start() -> bool` — starts daemon thread, blocks up to `START_TIMEOUT_SECS` (15 s) for first frame; returns True if frame received, False if timeout (execution continues either way)
- `stop()` — sets `_stop_event`, joins thread with 3 s timeout
- `get_latest_frame() -> Optional[bytes]` — returns raw JPEG bytes or None; acquires `_lock` briefly
- `get_frame_info() -> Tuple[int, float]` — returns `(frame_count, seconds_since_last_frame)`
- `is_running() -> bool` — True if daemon thread is alive
- `get_error() -> Optional[str]` — last stream error, or None

### Internal Methods
- `_stream_loop()` — outer reconnect loop; catches exceptions, sleeps `RECONNECT_DELAY_SECS` (2.0 s), retries
- `_get_response()` — calls `_get_client().get_raw_video_stream()`; handles Response object, URL string, or dict with url/stream_url/video_url key
- `_consume_stream()` — reads `iter_content(chunk_size=CHUNK_BYTES)`, scans for JPEG SOI (0xFF 0xD8) and EOI (0xFF 0xD9) markers, stores complete frames via `_lock`

## JPEG Extraction Strategy
- Uses SOI/EOI byte markers — NOT multipart boundary parsing
- Robust across different DeepRacer firmware versions and boundary formats
- `buf.find(b"\xff\xd8")` → SOI; `buf.find(b"\xff\xd9", soi+2)` → EOI
- Complete frame: `buf[soi : eoi + 2]`; advance buffer: `buf = buf[eoi + 2:]`
- Discards leading garbage before SOI on each iteration

## Constants
- `START_TIMEOUT_SECS = 15.0` — wait for first frame on start()
- `CHUNK_BYTES = 1024` — HTTP read chunk size
- `RECONNECT_DELAY_SECS = 2.0` — pause between reconnect attempts

## Thread Safety
- `_latest_frame` protected by `threading.Lock()` (`_lock`)
- `_stop_event` is `threading.Event()` — checked at top of each chunk loop iteration
- Thread is `daemon=True` — dies automatically when main process exits

## Error Handling
- `_stream_loop()` catches ALL exceptions from `_consume_stream()` — logs warning, reconnects
- `_get_response()` raises `RuntimeError` on unexpected return type — caught by `_stream_loop()`
- `urllib3.InsecureRequestWarning` suppressed — DeepRacer uses self-signed HTTPS
- `session.verify = False` when making direct HTTP requests to the stream URL
