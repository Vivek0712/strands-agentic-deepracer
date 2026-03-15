#!/usr/bin/env python3
"""
lawnmower.py — Autonomous lawnmower / outdoor ground robot tool layer.

USE_CASE=lawnmower

Hardware: GPS-guided autonomous lawnmower (e.g. Husqvarna Automower,
          Worx Landroid, or custom build on ROS2 Navigation Stack)
API:      ROS2 /cmd_vel + /boundary topic via rosbridge WebSocket
Camera:   Front-facing RGB camera for obstacle detection
Use case: Execute mowing patterns (stripes, spiral, perimeter-first),
          stop when child/pet detected in frame, replan around garden
          furniture, respect boundary wire or GPS geofence.

Movement model: differential drive — turns in place like a tank.
Rotation calibration: At ANGULAR_VEL=0.6 rad/s: 1.5 s ≈ 52° turn.
Adjust ANGULAR_VEL after physical measurement on your mower.

Environment variables:
    MOWER_IP            rosbridge host IP (default 192.168.1.50)
    MOWER_PORT          rosbridge port (default 9090)
    MOWER_LINEAR_VEL    forward speed m/s (default 0.4)
    MOWER_ANGULAR_VEL   turn rate rad/s (default 0.6)
    MOWER_BLADE_ON      start blade motor on connect (default true)
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
PLATFORM_NAME = "Autonomous Lawnmower"
PLATFORM_DESC = "GPS + camera guided mower · pattern mowing · child/pet detection"

# ── Hardware config ───────────────────────────────────────────────────────────
MOWER_IP     = os.getenv("MOWER_IP",           "192.168.1.50")
MOWER_PORT   = int(os.getenv("MOWER_PORT",     "9090"))
LINEAR_VEL   = float(os.getenv("MOWER_LINEAR_VEL",  "0.4"))   # m/s
ANGULAR_VEL  = float(os.getenv("MOWER_ANGULAR_VEL", "0.6"))   # rad/s
BLADE_ON     = os.getenv("MOWER_BLADE_ON", "true").lower() == "true"

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0           # differential drive — in-place turn
PHYSICS_MAX_CORNER_SPEED  = 0.8           # m/s safe outdoor speed
PHYSICS_FWD_SPEED_MS      = LINEAR_VEL
PHYSICS_TURN_SPEED_MS     = 0.0

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{MOWER_IP}:{MOWER_PORT}")
    return _WS

def _pub(topic, msg_type, msg):
    _get_ws().send(json.dumps({"op": "publish", "topic": topic, "type": msg_type, "msg": msg}))

def _cmd_vel(linear_x, angular_z, duration):
    _pub("/cmd_vel", "geometry_msgs/Twist", {
        "linear":  {"x": linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": angular_z},
    })
    time.sleep(duration)
    _pub("/cmd_vel", "geometry_msgs/Twist", {
        "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
    })

def reset_client():
    global _WS
    if _WS:
        try: _WS.close()
        except Exception: pass
    _WS = None

def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m

def activate_camera() -> bool:
    return True  # outdoor camera streams continuously

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        _get_ws()
        if BLADE_ON:
            _pub("/mower/blade", "std_msgs/Bool", {"data": True})
        return (
            f"Lawnmower connected at {MOWER_IP}:{MOWER_PORT}. "
            f"Blade: {'on' if BLADE_ON else 'off'}. "
            f"Speed: {LINEAR_VEL}m/s."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(LINEAR_VEL, 0.0, seconds)
        return f"Mower moved forward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(-LINEAR_VEL, 0.0, seconds)
        return f"Mower moved backward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Mower turned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, -ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Mower turned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _cmd_vel(0.0, 0.0, 0.1)
        _pub("/mower/blade", "std_msgs/Bool", {"data": False})
        return "Mower stopped. Blade off."
    except Exception as exc:
        return f"Error in stop: {exc}"
