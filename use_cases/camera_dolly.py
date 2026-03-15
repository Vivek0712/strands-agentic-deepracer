#!/usr/bin/env python3
"""
camera_dolly.py — Motorised camera dolly / slider tool layer.

USE_CASE=camera_dolly

Hardware: Motorised camera dolly, slider, or cable cam
          (e.g. Edelkrone SliderPLUS, custom Arduino/stepper rig)
API:      Serial over USB or TCP to Arduino/Raspberry Pi motor controller
Camera:   The dolly IS the camera — the mounted DSLR/mirrorless is
          the "front camera". Vision checks for subject in frame.
Use case: Cinematic movement patterns (dolly in, arc, reveal, orbit),
          stop when subject enters exact frame position,
          replan if subject has moved out of composition.

"turn left/right" maps to pan of the camera head (tilt/pan motor).
"forward/backward" maps to dolly track movement.

Rotation calibration: At PAN_SPEED=15 deg/s: 1.5 s ≈ 22.5° pan.
Adjust for your pan head's motor speed.

Environment variables:
    DOLLY_HOST          TCP host or 'serial' for serial port (default 192.168.1.70)
    DOLLY_PORT          TCP port (default 8000) or serial port (/dev/ttyUSB0)
    DOLLY_TRACK_SPEED   track movement speed 0.0–1.0 (default 0.3 — cinematic slow)
    DOLLY_PAN_SPEED     pan/tilt degrees per second (default 15)
"""

import json
import logging
import os
import socket
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Camera Dolly"
PLATFORM_DESC = "Motorised dolly · cinematic movement patterns · subject tracking"

# ── Hardware config ───────────────────────────────────────────────────────────
DOLLY_HOST   = os.getenv("DOLLY_HOST",        "192.168.1.70")
DOLLY_PORT   = int(os.getenv("DOLLY_PORT",    "8000"))
TRACK_SPEED  = float(os.getenv("DOLLY_TRACK_SPEED", "0.3"))  # 0.0–1.0 relative
PAN_SPEED    = float(os.getenv("DOLLY_PAN_SPEED",   "15.0")) # deg/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.3   # slow cinematic movements
PHYSICS_FWD_SPEED_MS      = TRACK_SPEED * 0.5   # approx m/s at TRACK_SPEED=0.3
PHYSICS_TURN_SPEED_MS     = 0.0   # pan in place

# ── TCP client ────────────────────────────────────────────────────────────────
_SOCK = None

def _get_sock():
    global _SOCK
    if _SOCK is None:
        _SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCK.settimeout(5)
        _SOCK.connect((DOLLY_HOST, DOLLY_PORT))
    return _SOCK

def _send(cmd: dict) -> str:
    _get_sock().sendall((json.dumps(cmd) + "\n").encode())
    try:
        return _get_sock().recv(256).decode().strip()
    except socket.timeout:
        return "ok"

def reset_client():
    global _SOCK
    if _SOCK:
        try: _SOCK.close()
        except Exception: pass
    _SOCK = None

def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m

def activate_camera() -> bool:
    """Trigger camera to start live view / HDMI out for frame capture."""
    try:
        resp = _send({"cmd": "camera_live_view", "on": True})
        return "ok" in resp.lower()
    except Exception:
        return True

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        resp = _send({"cmd": "ping"})
        activate_camera()
        return (
            f"Camera dolly connected at {DOLLY_HOST}:{DOLLY_PORT}. "
            f"Track speed: {TRACK_SPEED}, Pan speed: {PAN_SPEED}°/s. "
            f"Response: {resp}"
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    """Dolly forward along track (towards subject)."""
    try:
        _send({"cmd": "track", "direction": "forward", "speed": TRACK_SPEED, "duration": seconds})
        time.sleep(seconds)
        dist = PHYSICS_FWD_SPEED_MS * seconds
        return f"Dolly moved forward: speed={TRACK_SPEED} for {seconds:.2f}s (~{dist:.2f}m)"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    """Dolly backward along track (away from subject)."""
    try:
        _send({"cmd": "track", "direction": "backward", "speed": TRACK_SPEED, "duration": seconds})
        time.sleep(seconds)
        dist = PHYSICS_FWD_SPEED_MS * seconds
        return f"Dolly moved backward: speed={TRACK_SPEED} for {seconds:.2f}s (~{dist:.2f}m)"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    """Pan camera head left."""
    try:
        _send({"cmd": "pan", "direction": "left", "speed": PAN_SPEED, "duration": seconds})
        time.sleep(seconds)
        deg = PAN_SPEED * seconds
        return f"Camera panned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    """Pan camera head right."""
    try:
        _send({"cmd": "pan", "direction": "right", "speed": PAN_SPEED, "duration": seconds})
        time.sleep(seconds)
        deg = PAN_SPEED * seconds
        return f"Camera panned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _send({"cmd": "stop"})
        return "Dolly stopped. Camera holding position."
    except Exception as exc:
        return f"Error in stop: {exc}"
