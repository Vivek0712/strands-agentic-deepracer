#!/usr/bin/env python3
"""
roomba.py — iRobot Roomba / Create3 floor cleaning robot tool layer.

USE_CASE=roomba

Hardware: iRobot Create3 (ROS2 native) or Roomba with iRobot Home API
API:      iRobot Create3 ROS2 topics via rosbridge WebSocket
Camera:   External USB camera clipped to robot (Create3 has no camera —
          attach a small USB cam and mount it on top)
Use case: Room-cleaning patterns (boustrophedon/stripes, spiral, perimeter),
          stop on liquid spill detected, avoid cords and socks,
          return to dock when battery low or task complete.

Note: Create3 uses a different coordinate system — forward is +X,
      left is +Y in ROS convention. We follow the standard interface.

Rotation calibration: At ANGULAR_VEL=1.0 rad/s: 1.5 s ≈ 86° (fast spinner).
Roomba spins fast — set lower ANGULAR_VEL if gentler turns needed.

Environment variables:
    ROOMBA_IP           Create3 ROS2 rosbridge host (default 192.168.1.2)
    ROOMBA_PORT         rosbridge port (default 9090)
    ROOMBA_LINEAR_VEL   forward speed m/s (default 0.2 — floor cleaning speed)
    ROOMBA_ANGULAR_VEL  turn rate rad/s (default 1.0)
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
PLATFORM_NAME = "Roomba / Floor Cleaner"
PLATFORM_DESC = "iRobot Create3 · room patterns · liquid spill / cord detection"

# ── Hardware config ───────────────────────────────────────────────────────────
ROOMBA_IP    = os.getenv("ROOMBA_IP",          "192.168.1.2")
ROOMBA_PORT  = int(os.getenv("ROOMBA_PORT",    "9090"))
LINEAR_VEL   = float(os.getenv("ROOMBA_LINEAR_VEL",  "0.2"))  # slow — cleaning speed
ANGULAR_VEL  = float(os.getenv("ROOMBA_ANGULAR_VEL", "1.0"))  # rad/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.5
PHYSICS_FWD_SPEED_MS      = LINEAR_VEL
PHYSICS_TURN_SPEED_MS     = 0.0

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{ROOMBA_IP}:{ROOMBA_PORT}")
    return _WS

def _cmd_vel(linear_x, angular_z, duration):
    ws = _get_ws()
    go = json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear":  {"x": linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0,      "y": 0.0, "z": angular_z},
    }})
    ws.send(go)
    time.sleep(duration)
    ws.send(json.dumps({"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
    }}))

def _dock():
    """Send Roomba to charging dock."""
    try:
        _get_ws().send(json.dumps({"op": "publish", "topic": "/dock", "msg": {}}))
    except Exception:
        pass

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
    return True  # USB camera clipped on top streams via ROS2

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        _get_ws()
        # Subscribe to battery level
        _get_ws().send(json.dumps({
            "op": "subscribe",
            "topic": "/battery_state",
            "type": "sensor_msgs/BatteryState"
        }))
        return (
            f"Roomba connected at {ROOMBA_IP}:{ROOMBA_PORT}. "
            f"Cleaning speed: {LINEAR_VEL}m/s."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(LINEAR_VEL, 0.0, seconds)
        return f"Roomba moved forward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(-LINEAR_VEL, 0.0, seconds)
        return f"Roomba moved backward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Roomba turned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, -ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Roomba turned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _cmd_vel(0.0, 0.0, 0.1)
        _dock()
        return "Roomba stopped. Returning to dock."
    except Exception as exc:
        return f"Error in stop: {exc}"
