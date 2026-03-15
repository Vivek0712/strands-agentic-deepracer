#!/usr/bin/env python3
"""
POC: Display DeepRacer camera feed in an OpenCV window.

Uses the same connection as Phase 3 (.env: DEEPRACER_IP, DEEPRACER_PASSWORD).
Pattern: DeepracerCam thread reads get_raw_video_stream() and stores latest JPEG;
main loop calls get_image(timeout) and displays. Reconnects inside thread when
stream ends so the feed stays whole.

Run from this directory:
    python cam_feed_poc.py

Requirements:
    pip install aws-deepracer-control-v2 opencv-python numpy python-dotenv requests

Quit: press ESC in the window.
"""

import os
import sys
import time
from pathlib import Path
from threading import Lock, Thread

import cv2
import numpy as np
import requests

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

# Optional override: set DEEPRACER_VIDEO_TOPIC to use a specific topic (e.g. /camera_pkg/display_mjpeg).
# Empty = use library default (deepracer_tools patches the library to use /camera_pkg/display_mjpeg).
VIDEO_TOPIC = (os.getenv("DEEPRACER_VIDEO_TOPIC", "") or "").strip()

try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(category=InsecureRequestWarning)
except Exception:
    pass


def wait_until(closure, timeout=30, static_sleep=0, check_interval=0.1, **kwargs):
    """Wait until closure returns a truthy value or timeout."""
    deadline = time.time() + timeout
    if static_sleep > 0:
        time.sleep(static_sleep)
    while time.time() < deadline:
        r = closure(**kwargs)
        if r is not None and r is not False:
            return r
        time.sleep(check_interval)
    return r


def _open_stream_with_topic(ip: str, password: str, topic: str):
    """Open stream by logging in and GET /route?topic=... (no library stream call)."""
    base = f"https://{ip}:443"
    session = requests.Session()
    session.verify = False
    # Login (common patterns: JSON or form)
    login = session.post(
        f"{base}/login",
        json={"password": password},
        timeout=10,
    )
    if login.status_code != 200:
        login = session.post(
            f"{base}/login",
            data={"password": password},
            timeout=10,
        )
    if login.status_code != 200:
        raise RuntimeError(f"Login failed: {login.status_code} {login.text[:200]}")
    # Stream: /route?topic=/camera_pkg/display_mjpeg&width=480&height=360
    r = session.get(
        f"{base}/route",
        params={"topic": topic, "width": 480, "height": 360},
        stream=True,
        timeout=10,
    )
    r.raise_for_status()
    return r


class DeepracerCam(Thread):
    """Background thread: consume MJPEG stream from client or custom topic URL."""

    def __init__(self, client, ip: str = None, password: str = None, topic_override: str = None):
        super().__init__()
        self.daemon = True
        self.client = client
        self._ip = ip or getattr(client, "ip", None)
        self._password = password or getattr(client, "password", None)
        self.topic_override = topic_override  # e.g. /camera_pkg/display_mjpeg
        self._data = None
        self._data_lock = Lock()

    def _data_set(self, data):
        with self._data_lock:
            self._data = data

    def _get_data(self):
        with self._data_lock:
            return self._data

    def get_image(self, timeout=2):
        """Return latest decoded frame as numpy array (BGR), or None. Blocks up to timeout."""
        return wait_until(self._get_image, timeout=timeout)

    def _get_image(self):
        data = self._get_data()
        if data is None:
            return None
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def run(self):
        reconnect_delay = 2.0
        read_timeout = 10.0
        ip = self._ip or os.getenv("DEEPRACER_IP", "192.168.0.3")
        password = self._password or os.getenv("DEEPRACER_PASSWORD", "")

        while True:
            if self.topic_override and password:
                try:
                    r = _open_stream_with_topic(ip, password, self.topic_override)
                except Exception as e:
                    time.sleep(reconnect_delay)
                    continue
            else:
                r = self.client.get_raw_video_stream()
                if not hasattr(r, "status_code") or r.status_code != 200:
                    time.sleep(reconnect_delay)
                    continue

            buf = b""
            try:
                # Prefer raw stream so we block for data; set read timeout
                raw = getattr(r, "raw", None)
                if raw is not None and hasattr(raw, "read"):
                    fp = getattr(raw, "fp", None)
                    if fp is not None and hasattr(fp, "settimeout"):
                        fp.settimeout(read_timeout)
                    while True:
                        chunk = raw.read(1024)
                        if not chunk:
                            break
                        buf += chunk
                        a = buf.find(b"\xff\xd8")
                        b = buf.find(b"\xff\xd9", a + 2) if a != -1 else -1
                        if a != -1 and b != -1:
                            self._data_set(buf[a : b + 2])
                            buf = buf[b + 2 :]
                else:
                    for chunk in r.iter_content(chunk_size=1024, decode_unicode=False):
                        if not chunk:
                            continue
                        buf += chunk
                        a = buf.find(b"\xff\xd8")
                        b = buf.find(b"\xff\xd9", a + 2) if a != -1 else -1
                        if a != -1 and b != -1:
                            self._data_set(buf[a : b + 2])
                            buf = buf[b + 2 :]
            finally:
                if hasattr(r, "close"):
                    r.close()
            time.sleep(reconnect_delay)


def main():
    ip = os.getenv("DEEPRACER_IP", "192.168.0.3")
    password = os.getenv("DEEPRACER_PASSWORD", "")
    if not password:
        print("Set DEEPRACER_PASSWORD in .env or environment.")
        sys.exit(1)

    import deepracer_tools  # noqa: F401 — applies get_raw_video_stream topic patch
    import aws_deepracer_control_v2 as drctl
    client = drctl.Client(password=password, ip=ip)
    print(f"Create client with ip = {ip}")

    if VIDEO_TOPIC:
        print(f"Using video topic: {VIDEO_TOPIC}")
    else:
        print("Using library default stream.")

    print("Connecting to camera stream…")
    cam = DeepracerCam(client, ip=ip, password=password, topic_override=VIDEO_TOPIC or None)
    cam.start()
    time.sleep(1)

    i = 0
    try:
        while True:
            image = cam.get_image(timeout=1)
            if image is not None:
                cv2.imshow("DeepRacer Camera (ESC to quit)", image)
            else:
                print("waiting", i)
                i += 1
            if cv2.waitKey(1) == 27:
                break
    finally:
        cv2.destroyAllWindows()
        print("Done.")


if __name__ == "__main__":
    main()
