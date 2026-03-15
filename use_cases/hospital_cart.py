#!/usr/bin/env python3
"""
hospital_cart.py — Hospital delivery / medication cart robot tool layer.

USE_CASE=hospital_cart

Hardware: Autonomous indoor delivery robot (e.g. Aethon TUG, Savioke Relay,
          or custom ROS2 Navigation Stack robot)
API:      ROS2 /cmd_vel + /floor_map via rosbridge WebSocket
Camera:   Front-facing RGB camera for corridor/door/person detection
Use case: Navigate hospital corridors, deliver medication between wards,
          stop when corridor is occupied by staff or patient,
          wait at closed fire doors, announce arrival at destination.

Safety is paramount: PHYSICS_MAX_CORNER_SPEED is deliberately low (0.6 m/s).
The vision system should be aggressive — prefer abort over continue near people.

Environment variables:
    CART_IP             rosbridge host (default 192.168.1.60)
    CART_PORT           rosbridge port (default 9090)
    CART_LINEAR_VEL     forward speed m/s (default 0.5, max 0.8 recommended)
    CART_ANGULAR_VEL    turn rate rad/s (default 0.5)
    CART_ANNOUNCE       play arrival chime on connect (default true)
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
PLATFORM_NAME = "Hospital Cart Robot"
PLATFORM_DESC = "Indoor delivery robot · corridor navigation · staff/patient detection"

# ── Hardware config ───────────────────────────────────────────────────────────
CART_IP      = os.getenv("CART_IP",           "192.168.1.60")
CART_PORT    = int(os.getenv("CART_PORT",     "9090"))
LINEAR_VEL   = float(os.getenv("CART_LINEAR_VEL",  "0.5"))   # m/s — keep ≤ 0.8
ANGULAR_VEL  = float(os.getenv("CART_ANGULAR_VEL", "0.5"))   # rad/s
ANNOUNCE     = os.getenv("CART_ANNOUNCE", "true").lower() == "true"

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.6   # slow and safe in hospital corridors
PHYSICS_FWD_SPEED_MS      = LINEAR_VEL
PHYSICS_TURN_SPEED_MS     = 0.0

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{CART_IP}:{CART_PORT}")
    return _WS

def _cmd_vel(linear_x, angular_z, duration):
    ws = _get_ws()
    msg = {"op": "publish", "topic": "/cmd_vel", "msg": {
        "linear":  {"x": linear_x, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": angular_z},
    }}
    ws.send(json.dumps(msg))
    time.sleep(duration)
    msg["msg"]["linear"]["x"] = 0.0
    msg["msg"]["angular"]["z"] = 0.0
    ws.send(json.dumps(msg))

def _announce(text: str):
    try:
        _get_ws().send(json.dumps({
            "op": "publish", "topic": "/cart/announce",
            "msg": {"data": text}
        }))
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
    return True

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        _get_ws()
        if ANNOUNCE:
            _announce("Hospital cart online. Please clear the corridor.")
        return (
            f"Hospital cart connected at {CART_IP}:{CART_PORT}. "
            f"Speed: {LINEAR_VEL}m/s (max safe: {PHYSICS_MAX_CORNER_SPEED}m/s)."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(LINEAR_VEL, 0.0, seconds)
        return f"Cart moved forward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _cmd_vel(-LINEAR_VEL, 0.0, seconds)
        return f"Cart moved backward: {LINEAR_VEL}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Cart turned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, -ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Cart turned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _cmd_vel(0.0, 0.0, 0.1)
        if ANNOUNCE:
            _announce("Delivery complete. Thank you.")
        return "Cart stopped."
    except Exception as exc:
        return f"Error in stop: {exc}"
