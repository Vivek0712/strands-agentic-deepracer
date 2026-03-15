#!/usr/bin/env python3
"""
pipeline_crawler.py — Pipeline / duct inspection robot tool layer.

USE_CASE=pipeline_crawler

Hardware: Tracked or wheeled robot that moves inside pipes/ducts
API:      Serial or TCP to onboard microcontroller
Camera:   Forward-facing endoscope camera
Use case: Crawl through pipes, stop on crack/corrosion/blockage detected,
          log position, replan to inspect area more closely.

Movement model: constrained 1D movement — forward/backward only.
"turn left/right" maps to pan of the camera head, not vehicle movement.
The robot moves in a straight line inside the pipe.

Rotation calibration:
    Camera pan at PAN_SPEED=30 deg/s: 1.5 s ≈ 45° pan angle.
    Vehicle has no turning — forward/backward only.

Environment variables:
    CRAWLER_HOST    IP or serial port (default: 192.168.1.200)
    CRAWLER_PORT    TCP port (default: 8888)
    CRAWLER_SPEED   forward speed (0.0–1.0, default 0.3)
    CRAWLER_PAN_SPD camera pan speed deg/s (default 30)
"""

import json
import logging
import os
import socket
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Pipeline Crawler"
PLATFORM_DESC = "Pipe inspection robot · endoscope camera · crack/corrosion detection"

# ── Hardware config ───────────────────────────────────────────────────────────
CRAWLER_HOST = os.getenv("CRAWLER_HOST",    "192.168.1.200")
CRAWLER_PORT = int(os.getenv("CRAWLER_PORT", "8888"))
SPEED        = float(os.getenv("CRAWLER_SPEED",    "0.3"))
PAN_SPEED    = float(os.getenv("CRAWLER_PAN_SPD",  "30.0"))  # deg/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = float("inf")  # cannot turn — pipe constrained
PHYSICS_MAX_CORNER_SPEED  = 0.5           # m/s safe crawl speed
PHYSICS_FWD_SPEED_MS      = SPEED * 0.5  # approximate m/s at SPEED=0.3
PHYSICS_TURN_SPEED_MS     = 0.0          # camera pan, not movement

# ── TCP client ────────────────────────────────────────────────────────────────
_SOCK = None


def _get_sock():
    global _SOCK
    if _SOCK is None:
        _SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCK.settimeout(5)
        _SOCK.connect((CRAWLER_HOST, CRAWLER_PORT))
    return _SOCK


def _send_cmd(cmd: dict) -> str:
    sock = _get_sock()
    sock.sendall((json.dumps(cmd) + "\n").encode())
    try:
        return sock.recv(256).decode().strip()
    except socket.timeout:
        return "ok"


def reset_client() -> None:
    global _SOCK
    if _SOCK:
        try: _SOCK.close()
        except Exception: pass
    _SOCK = None


def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "cannot connect" in m


def activate_camera() -> bool:
    """Endoscope camera streams continuously — no activation needed."""
    try:
        resp = _send_cmd({"cmd": "camera_on"})
        return "ok" in resp.lower()
    except Exception:
        return True  # assume active if no response


# ── Required tool functions ───────────────────────────────────────────────────

def connect() -> str:
    try:
        resp = _send_cmd({"cmd": "ping"})
        return (
            f"Pipeline crawler connected at {CRAWLER_HOST}:{CRAWLER_PORT}. "
            f"Response: {resp}. Speed: {SPEED}, Camera: active."
        )
    except Exception as exc:
        return f"Error: {exc}"


def move_forward(seconds: float = 2.0) -> str:
    try:
        _send_cmd({"cmd": "move", "direction": "forward", "speed": SPEED, "duration": seconds})
        time.sleep(seconds)
        dist = SPEED * 0.5 * seconds  # approximate
        return f"Crawler moved forward: speed={SPEED} duration={seconds:.2f}s (~{dist:.2f}m)"
    except Exception as exc:
        return f"Error in move_forward: {exc}"


def move_backward(seconds: float = 2.0) -> str:
    try:
        _send_cmd({"cmd": "move", "direction": "backward", "speed": SPEED, "duration": seconds})
        time.sleep(seconds)
        dist = SPEED * 0.5 * seconds
        return f"Crawler moved backward: speed={SPEED} duration={seconds:.2f}s (~{dist:.2f}m)"
    except Exception as exc:
        return f"Error in move_backward: {exc}"


def turn_left(seconds: float = 1.5) -> str:
    """Pan camera left — robot cannot turn inside pipe."""
    try:
        _send_cmd({"cmd": "pan", "direction": "left", "speed": PAN_SPEED, "duration": seconds})
        time.sleep(seconds)
        deg = PAN_SPEED * seconds
        return f"Camera panned left: {deg:.1f}° in {seconds:.2f}s (robot stationary)"
    except Exception as exc:
        return f"Error in turn_left: {exc}"


def turn_right(seconds: float = 1.5) -> str:
    """Pan camera right — robot cannot turn inside pipe."""
    try:
        _send_cmd({"cmd": "pan", "direction": "right", "speed": PAN_SPEED, "duration": seconds})
        time.sleep(seconds)
        deg = PAN_SPEED * seconds
        return f"Camera panned right: {deg:.1f}° in {seconds:.2f}s (robot stationary)"
    except Exception as exc:
        return f"Error in turn_right: {exc}"


def stop() -> str:
    try:
        _send_cmd({"cmd": "stop"})
        return "Crawler stopped."
    except Exception as exc:
        return f"Error in stop: {exc}"