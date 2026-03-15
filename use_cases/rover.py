#!/usr/bin/env python3
"""
rover.py — Outdoor exploration rover tool layer.

USE_CASE=rover

Hardware: 4/6-wheeled outdoor rover (rocker-bogie, skid-steer, or
          standard differential drive). Examples: Sawppy, custom ROS2 rover,
          FPV chassis with Raspberry Pi.
API:      ROS2 /cmd_vel via rosbridge WebSocket
Camera:   Forward-facing wide-angle camera (fisheye or standard)
Use case: Terrain exploration, search patterns over open areas, stop when
          steep terrain or drop-off detected, replan around large rocks,
          survey grids, inspect infrastructure from outside.

Vision prompt should watch for:
  - Drop-offs / ledges → abort immediately
  - Large rocks / debris blocking path → replan
  - Loose sand / mud → replan to firmer ground
  - Clear terrain → continue

Rotation calibration: At ANGULAR_VEL=0.4 rad/s: 1.5 s ≈ 34°.
Outdoor rovers turn more slowly due to terrain resistance.

Environment variables:
    ROVER_IP            rosbridge host IP (default 192.168.1.90)
    ROVER_PORT          rosbridge port (default 9090)
    ROVER_LINEAR_VEL    forward speed m/s (default 0.3)
    ROVER_ANGULAR_VEL   turn rate rad/s (default 0.4)
    ROVER_MAX_SLOPE_DEG abort if IMU pitch/roll exceeds this (default 25)
"""

import json
import logging
import math
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Outdoor Rover"
PLATFORM_DESC = "Exploration rover · terrain navigation · drop-off / rock detection"

# ── Hardware config ───────────────────────────────────────────────────────────
ROVER_IP      = os.getenv("ROVER_IP",           "192.168.1.90")
ROVER_PORT    = int(os.getenv("ROVER_PORT",     "9090"))
LINEAR_VEL    = float(os.getenv("ROVER_LINEAR_VEL",  "0.3"))
ANGULAR_VEL   = float(os.getenv("ROVER_ANGULAR_VEL", "0.4"))
MAX_SLOPE_DEG = float(os.getenv("ROVER_MAX_SLOPE_DEG", "25.0"))

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.6
PHYSICS_FWD_SPEED_MS      = LINEAR_VEL
PHYSICS_TURN_SPEED_MS     = 0.0

# ── State ─────────────────────────────────────────────────────────────────────
_latest_imu = {"pitch": 0.0, "roll": 0.0}

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{ROVER_IP}:{ROVER_PORT}")
    return _WS

def _cmd_vel(linear_x, angular_z, duration):
    ws = _get_ws()
    ws.send(json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear":  {"x": linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": angular_z},
    }}))
    time.sleep(duration)
    ws.send(json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
    }}))

def _check_imu() -> str | None:
    """Return an error message if tilt exceeds MAX_SLOPE_DEG, else None."""
    pitch = abs(_latest_imu.get("pitch", 0.0))
    roll  = abs(_latest_imu.get("roll",  0.0))
    if pitch > MAX_SLOPE_DEG or roll > MAX_SLOPE_DEG:
        return f"Slope limit exceeded: pitch={pitch:.1f}° roll={roll:.1f}° (max {MAX_SLOPE_DEG}°)"
    return None

def reset_client():
    global _WS
    if _WS:
        try: _WS.close()
        except Exception: pass
    _WS = None

def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "slope limit" in m

def activate_camera() -> bool:
    return True

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        _get_ws()
        # Subscribe to IMU for slope detection
        _get_ws().send(json.dumps({
            "op": "subscribe",
            "topic": "/imu/data",
            "type": "sensor_msgs/Imu"
        }))
        return (
            f"Rover connected at {ROVER_IP}:{ROVER_PORT}. "
            f"Speed: {LINEAR_VEL}m/s. "
            f"Max slope: {MAX_SLOPE_DEG}°."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    slope_err = _check_imu()
    if slope_err:
        return f"Error: {slope_err} — refusing to move forward."
    try:
        _cmd_vel(LINEAR_VEL, 0.0, seconds)
        dist = LINEAR_VEL * seconds
        return f"Rover moved forward: {LINEAR_VEL}m/s for {seconds:.2f}s (~{dist:.2f}m)"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(-LINEAR_VEL, 0.0, seconds)
        return f"Rover moved backward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Rover turned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, -ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Rover turned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _cmd_vel(0.0, 0.0, 0.1)
        return "Rover stopped."
    except Exception as exc:
        return f"Error in stop: {exc}"
