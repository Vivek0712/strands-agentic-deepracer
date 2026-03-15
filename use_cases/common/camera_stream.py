#!/usr/bin/env python3
"""
camera_stream.py — Non-blocking MJPEG frame buffer for Phase 3.

Consumes the DeepRacer's MJPEG stream in a background daemon thread.
Always holds the latest decoded JPEG frame in memory so the vision
assessor can grab it instantly (< 1 ms) without blocking execution.

Stream format: multipart/x-mixed-replace HTTP, each part is a raw JPEG.
We parse by scanning for JPEG SOI/EOI byte markers rather than parsing
multipart boundaries — robust regardless of boundary string.

JPEG markers:
    SOI (Start of Image) : 0xFF 0xD8
    EOI (End of Image)   : 0xFF 0xD9
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)

# DeepRacer device often uses self-signed HTTPS; suppress warnings when verify=False
try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(category=InsecureRequestWarning)
except Exception:
    pass


class CameraStream:
    """
    Background thread that keeps the latest JPEG frame from the
    DeepRacer MJPEG stream always available via get_latest_frame().

    Usage:
        stream = CameraStream()
        ok = stream.start()         # blocks up to 5 s for first frame
        frame = stream.get_latest_frame()   # bytes | None, non-blocking
        stream.stop()
    """

    # How long to wait for the first frame before start() returns False
    START_TIMEOUT_SECS: float = 15.0
    # Chunk size for reading the HTTP stream (smaller = more frequent SOI/EOI checks)
    CHUNK_BYTES: int = 1024
    # Seconds to pause before reconnecting after a stream error
    RECONNECT_DELAY_SECS: float = 2.0

    def __init__(self) -> None:
        self._latest_frame: Optional[bytes] = None
        self._lock              = threading.Lock()
        self._stop_event        = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame_count: int  = 0
        self._last_frame_time: float = 0.0
        self._error: Optional[str]   = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the background streaming thread.

        Blocks up to START_TIMEOUT_SECS waiting for the first frame so the
        caller knows the camera is actually delivering images before execution
        begins.

        Returns:
            True  — stream is running and at least one frame was received.
            False — stream started but no frame arrived within the timeout
                    (car may be booting or camera not ready; execution can
                    still proceed without vision rather than blocking).
        """
        if self._thread is not None and self._thread.is_alive():
            logger.info("CameraStream already running.")
            return self._latest_frame is not None

        self._stop_event.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._stream_loop,
            daemon=True,
            name="camera_stream",
        )
        self._thread.start()
        logger.info("CameraStream thread started — waiting for first frame…")

        deadline = time.time() + self.START_TIMEOUT_SECS
        while time.time() < deadline:
            if self._latest_frame is not None:
                logger.info(
                    f"CameraStream ready — first frame received "
                    f"({len(self._latest_frame)} bytes)."
                )
                return True
            time.sleep(0.1)

        logger.warning(
            "CameraStream started but no frame received within "
            f"{self.START_TIMEOUT_SECS}s. Continuing without vision."
        )
        return False

    def stop(self) -> None:
        """Signal the streaming thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("CameraStream stopped.")

    def get_latest_frame(self) -> Optional[bytes]:
        """Return the most recently decoded JPEG frame, or None if unavailable.

        Non-blocking — acquires a short lock and returns immediately.
        Returns None if the stream hasn't started or has no frames yet.
        """
        with self._lock:
            return self._latest_frame

    def get_frame_info(self) -> Tuple[int, float]:
        """Return (frame_count, seconds_since_last_frame) for diagnostics."""
        since = (
            time.time() - self._last_frame_time
            if self._last_frame_time > 0.0
            else float("inf")
        )
        return self._frame_count, since

    def is_running(self) -> bool:
        """True if the background thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def get_error(self) -> Optional[str]:
        """Return the last stream error message, or None."""
        return self._error

    # ── Background thread ─────────────────────────────────────────────────────

    def _stream_loop(self) -> None:
        """Outer reconnect loop — wraps _consume_stream with error recovery."""
        while not self._stop_event.is_set():
            try:
                self._consume_stream()
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self._error = str(exc)
                logger.warning(
                    f"[CameraStream] stream error: {exc}. "
                    f"Reconnecting in {self.RECONNECT_DELAY_SECS}s…"
                )
                time.sleep(self.RECONNECT_DELAY_SECS)

    def _get_response(self):
        """Get a streaming response from the DeepRacer camera.

        aws_deepracer_control_v2.Client.get_raw_video_stream() may return either:
        - A requests.Response (with .iter_content): use it directly.
        - A URL string or dict with 'url'/'stream_url'/'video_url': GET it ourselves.
        """
        from deepracer_tools import _get_client

        client = _get_client()
        info = client.get_raw_video_stream()

        # Library returns a Response directly (e.g. newer DeepRacer firmware / SDK)
        if hasattr(info, "iter_content") and callable(getattr(info, "iter_content", None)):
            logger.debug("MJPEG stream: using Response from get_raw_video_stream()")
            return info

        # Library returns a URL (str or dict)
        if isinstance(info, str):
            stream_url = info
        elif isinstance(info, dict):
            stream_url = None
            for key in ("url", "stream_url", "video_url"):
                if key in info:
                    stream_url = info[key]
                    break
            if not stream_url:
                raise RuntimeError("get_raw_video_stream() dict has no url key")
        else:
            raise RuntimeError(f"get_raw_video_stream() returned unexpected type: {type(info).__name__!r}")

        session = requests.Session()
        session.verify = False  # DeepRacer device typically uses self-signed HTTPS
        response = session.get(stream_url, stream=True, timeout=10)
        response.raise_for_status()
        logger.debug("MJPEG HTTP connection established: %s", stream_url[:60] if len(stream_url) > 60 else stream_url)
        return response

    def _consume_stream(self) -> None:
        """Open the MJPEG stream and continuously extract JPEG frames.

        Reads the HTTP response chunk by chunk. Scans the byte buffer for
        JPEG SOI (0xFF 0xD8) and EOI (0xFF 0xD9) markers to extract complete
        frames, regardless of the multipart boundary format.
        """
        response = self._get_response()

        try:
            buf = b""
            first_chunk_logged = False

            for chunk in response.iter_content(chunk_size=self.CHUNK_BYTES, decode_unicode=False):
                if self._stop_event.is_set():
                    return
                if not chunk:
                    continue

                if not first_chunk_logged:
                    logger.info("[CameraStream] first chunk received (%d bytes)", len(chunk))
                    first_chunk_logged = True

                buf += chunk

                # Extract all complete JPEG frames present in the buffer
                while True:
                    soi = buf.find(b"\xff\xd8")
                    if soi == -1:
                        # No JPEG start marker found — discard and wait for more
                        buf = b""
                        break

                    eoi = buf.find(b"\xff\xd9", soi + 2)
                    if eoi == -1:
                        # Have start but not end yet — trim leading garbage and wait
                        buf = buf[soi:]
                        break

                    # Complete JPEG frame: [soi, eoi+2)
                    frame = buf[soi : eoi + 2]

                    with self._lock:
                        self._latest_frame = frame

                    self._frame_count += 1
                    self._last_frame_time = time.time()

                    if self._frame_count == 1:
                        logger.info("[CameraStream] first frame received (%d bytes)", len(frame))

                    # Advance buffer past this frame
                    buf = buf[eoi + 2 :]

                    logger.debug(
                        f"[CameraStream] frame #{self._frame_count} "
                        f"({len(frame)} bytes)"
                    )
        finally:
            response.close()