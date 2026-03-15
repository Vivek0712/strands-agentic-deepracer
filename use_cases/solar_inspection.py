#!/usr/bin/env python3
"""
solar_inspection.py — Solar farm panel inspection robot tool layer.

USE_CASE=solar_inspection

Hardware: Ground robot traversing rows of solar panels
          (wheeled or tracked, GPS or encoder navigation)
API:      ROS2 /cmd_vel via rosbridge WebSocket
Camera:   Downward-facing or forward-facing thermal + RGB camera
Use case: Traverse panel rows, detect cracked/dirty/shaded panels,
          stop at anomaly for detailed inspection, log panel GPS position,
          replan to skip inaccessible rows.

Vision prompt should watch for:
  - Hot spots (thermal anomaly) → stop for inspection
  - Cracked glass → stop and log
  - Bird droppings / severe soiling → stop and flag
  - Normal panel surface → continue

Rotation calibration: At ANGULAR_VEL=0.5 rad/s: 1.5 s ≈ 43°.
Row-end turns are typically 180° (U-turns between rows).

Environment variables:
    SOLAR_IP            rosbridge host IP (default 192.168.1.80)
    SOLAR_PORT          rosbridge port (default 9090)
    SOLAR_LINEAR_VEL    inspection speed m/s (default 0.3 — slow for imaging)
    SOLAR_ANGULAR_VEL   turn rate rad/s (default 0.5)
    SOLAR_ROW_WIDTH_M   distance between panel rows in metres (default 3.0)
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
PLATFORM_NAME = "Solar Panel Inspector"
PLATFORM_DESC = "Solar farm inspection robot · thermal + RGB · anomaly detection"

# ── Hardware config ───────────────────────────────────────────────────────────
SOLAR_IP     = os.getenv("SOLAR_IP",           "192.168.1.80")
SOLAR_PORT   = int(os.getenv("SOLAR_PORT",     "9090"))
LINEAR_VEL   = float(os.getenv("SOLAR_LINEAR_VEL",  "0.3"))  # slow for imaging
ANGULAR_VEL  = float(os.getenv("SOLAR_ANGULAR_VEL", "0.5"))
ROW_WIDTH    = float(os.getenv("SOLAR_ROW_WIDTH_M",  "3.0"))

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.8
PHYSICS_FWD_SPEED_MS      = LINEAR_VEL
PHYSICS_TURN_SPEED_MS     = 0.0

# ── Inspection log (in-memory; persist to file in production) ─────────────────
_inspection_log = []
_position_m     = 0.0  # estimated distance along current row

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None

def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{SOLAR_IP}:{SOLAR_PORT}")
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

def _log_anomaly(description: str):
    entry = {"position_m": round(_position_m, 2), "time": time.strftime("%H:%M:%S"), "note": description}
    _inspection_log.append(entry)
    logger.info(f"[Solar] Anomaly logged: {entry}")

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
    return True  # camera streams continuously on ROS2

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    global _position_m
    _position_m = 0.0
    try:
        _get_ws()
        return (
            f"Solar inspector connected at {SOLAR_IP}:{SOLAR_PORT}. "
            f"Inspection speed: {LINEAR_VEL}m/s. "
            f"Row width: {ROW_WIDTH}m. "
            f"Inspection log: 0 entries."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    global _position_m
    try:
        _cmd_vel(LINEAR_VEL, 0.0, seconds)
        dist = LINEAR_VEL * seconds
        _position_m += dist
        return (
            f"Inspector moved forward: {LINEAR_VEL}m/s for {seconds:.2f}s. "
            f"Row position: {_position_m:.1f}m"
        )
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    global _position_m
    try:
        _cmd_vel(-LINEAR_VEL, 0.0, seconds)
        dist = LINEAR_VEL * seconds
        _position_m -= dist
        return f"Inspector moved backward: {LINEAR_VEL}m/s for {seconds:.2f}s."
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Inspector turned left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _cmd_vel(0.0, -ANGULAR_VEL, seconds)
        deg = math.degrees(ANGULAR_VEL * seconds)
        return f"Inspector turned right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _cmd_vel(0.0, 0.0, 0.1)
        _log_anomaly("Inspection stopped — anomaly at this position.")
        summary = f"Stop at row position {_position_m:.1f}m. Total anomalies: {len(_inspection_log)}."
        return f"Inspector stopped. {summary}"
    except Exception as exc:
        return f"Error in stop: {exc}"
