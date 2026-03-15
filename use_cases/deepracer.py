#!/usr/bin/env python3
"""
deepracer.py — AWS DeepRacer tool layer.

USE_CASE=deepracer  (or leave unset — this is the default)

Hardware: AWS DeepRacer 1/18-scale RC car
API:      aws-deepracer-control-v2 (HTTP web console)
Camera:   USB front-facing camera, MJPEG via /display_mjpeg ROS topic

Rotation calibration (empirically measured):
    1.5 s at STEER_ANGLE=0.50, TURN_THROTTLE=0.20 ≈ 90° heading change
    DEGREES_PER_SECOND = 60 °/s
"""

import io
import os
import logging
from contextlib import redirect_stdout
from pathlib import Path

import aws_deepracer_control_v2 as drctl
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "common" / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "AWS DeepRacer"
PLATFORM_DESC = "1/18-scale RC autonomous car · USB camera · ROS2"

# ── Hardware config ───────────────────────────────────────────────────────────
IP       = os.getenv("DEEPRACER_IP",       "192.168.0.3")
PASSWORD = os.getenv("DEEPRACER_PASSWORD", "")

FWD_THROTTLE  = float(os.getenv("DEEPRACER_FWD_THROTTLE",  "0.30"))
TURN_THROTTLE = float(os.getenv("DEEPRACER_TURN_THROTTLE", "0.20"))
MAX_SPEED     = float(os.getenv("DEEPRACER_MAX_SPEED",     "1.0"))
STEER_ANGLE   = float(os.getenv("DEEPRACER_STEER_ANGLE",   "0.50"))

# ── Physics constants (required by base interface) ────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.28
PHYSICS_MAX_CORNER_SPEED  = 1.5
PHYSICS_FWD_SPEED_MS      = 0.40
PHYSICS_TURN_SPEED_MS     = 0.25

# ── HTTP client ───────────────────────────────────────────────────────────────
_CLIENT = None

def _get_client() -> drctl.Client:
    global _CLIENT
    if _CLIENT is None:
        if not PASSWORD:
            raise RuntimeError("DEEPRACER_PASSWORD is not set in .env")
        _CLIENT = drctl.Client(password=PASSWORD, ip=IP)
    return _CLIENT

def reset_client() -> None:
    global _CLIENT
    _CLIENT = None

def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "[error" in m or "exception" in m

# ── Camera activation ─────────────────────────────────────────────────────────

def activate_camera() -> bool:
    """Wake the DeepRacer camera_node via PUT /api/vehicle/media_state."""
    try:
        client = _get_client()
        client._get_csrf_token()
        resp = client.session.put(
            client.URL + "/api/vehicle/media_state",
            headers=client.headers,
            json={"activateVideo": 1},
            verify=False,
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.warning(f"[DeepRacer] camera activation failed: {exc}")
        return False

# ── Required tool functions ───────────────────────────────────────────────────

def connect() -> str:
    """Connect and activate camera."""
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error connecting: {exc}"
    cam = "Camera activated." if activate_camera() else "Camera activation failed."
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            client.show_vehicle_info()
    except Exception as exc:
        return f"Error: {exc}. {cam}"
    return (buf.getvalue().strip() or f"Connected to DeepRacer at {IP}.") + f" | {cam}"


def move_forward(seconds: float = 2.0) -> str:
    try:
        _get_client().move(
            steering=0.0,
            throttle=-FWD_THROTTLE,
            duration=min(seconds, float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))),
            max_speed=MAX_SPEED,
        )
        return f"Moved: steering=+0.00 throttle=-{FWD_THROTTLE:.2f} duration={seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"


def move_backward(seconds: float = 2.0) -> str:
    try:
        _get_client().move(
            steering=0.0,
            throttle=FWD_THROTTLE,
            duration=min(seconds, float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))),
            max_speed=MAX_SPEED,
        )
        return f"Moved: steering=+0.00 throttle=+{FWD_THROTTLE:.2f} duration={seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"


def turn_left(seconds: float = 1.5) -> str:
    try:
        _get_client().move(
            steering=-STEER_ANGLE,
            throttle=-TURN_THROTTLE,
            duration=min(seconds, float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))),
            max_speed=MAX_SPEED,
        )
        return f"Moved: steering=-{STEER_ANGLE:.2f} throttle=-{TURN_THROTTLE:.2f} duration={seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"


def turn_right(seconds: float = 1.5) -> str:
    try:
        _get_client().move(
            steering=STEER_ANGLE,
            throttle=-TURN_THROTTLE,
            duration=min(seconds, float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))),
            max_speed=MAX_SPEED,
        )
        return f"Moved: steering=+{STEER_ANGLE:.2f} throttle=-{TURN_THROTTLE:.2f} duration={seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"


def stop() -> str:
    try:
        _get_client().move(steering=0.0, throttle=0.0, duration=0.1, max_speed=MAX_SPEED)
        return "Stop command sent to DeepRacer."
    except Exception as exc:
        return f"Error in stop: {exc}"