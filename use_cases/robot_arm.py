#!/usr/bin/env python3
"""
robot_arm.py — 6-DOF robot arm tool layer via ROS2 MoveIt2.

USE_CASE=robot_arm

Hardware: Any MoveIt2-compatible 6-DOF arm (UR5, Franka, custom)
API:      MoveIt2 via rosbridge WebSocket → /move_group action
Camera:   Wrist-mounted or overhead RGB/depth camera
Use case: Pick-and-place sequences, stop when hand enters workspace,
          replan if object has moved (vision detects wrong position).

"forward/backward/left/right" maps to Cartesian end-effector movements:
    forward  → +X (towards target)
    backward → -X (retract)
    left     → +Y
    right    → -Y
    stop     → hold current position

Rotation calibration:
    "turn" maps to end-effector Z-axis rotation (wrist yaw).
    At ROTATION_SPEED=30 deg/s: 1.5 s ≈ 45° wrist rotation.

Environment variables:
    ROBOT_IP            rosbridge host IP
    ROBOT_PORT          rosbridge port (default 9090)
    ARM_STEP_M          Cartesian step size in metres per second of movement
    ARM_ROTATION_SPEED  wrist rotation speed deg/s (default 30)
"""

import json
import logging
import math
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Robot Arm"
PLATFORM_DESC = "6-DOF arm · MoveIt2 · Cartesian end-effector control"

# ── Hardware config ───────────────────────────────────────────────────────────
ROBOT_IP         = os.getenv("ROBOT_IP",            "192.168.1.100")
ROBOT_PORT       = int(os.getenv("ROBOT_PORT",      "9090"))
ARM_STEP_M       = float(os.getenv("ARM_STEP_M",    "0.05"))   # m/s of command time
ROTATION_SPEED   = float(os.getenv("ARM_ROTATION_SPEED", "30.0"))  # deg/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0
PHYSICS_MAX_CORNER_SPEED  = 0.1    # m/s — arms move slowly for safety
PHYSICS_FWD_SPEED_MS      = ARM_STEP_M
PHYSICS_TURN_SPEED_MS     = 0.0

# ── WebSocket client ──────────────────────────────────────────────────────────
_WS = None


def _get_ws():
    global _WS
    if _WS is None:
        import websocket
        _WS = websocket.WebSocket()
        _WS.connect(f"ws://{ROBOT_IP}:{ROBOT_PORT}")
    return _WS


def _publish(topic: str, msg_type: str, data: dict) -> None:
    _get_ws().send(json.dumps({
        "op": "publish",
        "topic": topic,
        "type": msg_type,
        "msg": data,
    }))


def _call_service(service: str, req: dict) -> dict:
    ws = _get_ws()
    ws.send(json.dumps({
        "op": "call_service",
        "service": service,
        "args": req,
    }))
    return json.loads(ws.recv())


def reset_client() -> None:
    global _WS
    if _WS:
        try: _WS.close()
        except Exception: pass
    _WS = None


def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "cannot connect" in m


def activate_camera() -> bool:
    """Wrist camera streams continuously via ROS2 — no activation needed."""
    return True


# ── Required tool functions ───────────────────────────────────────────────────

def connect() -> str:
    try:
        _get_ws()
        return (
            f"Connected to robot arm at {ROBOT_IP}:{ROBOT_PORT} via rosbridge. "
            f"MoveIt2 ready. End-effector step: {ARM_STEP_M}m/s"
        )
    except Exception as exc:
        return f"Error: {exc}"


def move_forward(seconds: float = 2.0) -> str:
    """Move end-effector in +X direction (towards target)."""
    try:
        dist = ARM_STEP_M * seconds
        _publish("/arm_cmd/cartesian", "geometry_msgs/Vector3",
                 {"x": dist, "y": 0.0, "z": 0.0})
        time.sleep(seconds)
        return f"Arm moved forward (X+): {dist:.3f}m in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"


def move_backward(seconds: float = 2.0) -> str:
    """Retract end-effector in -X direction."""
    try:
        dist = ARM_STEP_M * seconds
        _publish("/arm_cmd/cartesian", "geometry_msgs/Vector3",
                 {"x": -dist, "y": 0.0, "z": 0.0})
        time.sleep(seconds)
        return f"Arm retracted (X-): {dist:.3f}m in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"


def turn_left(seconds: float = 1.5) -> str:
    """Rotate wrist counter-clockwise (Z-axis yaw)."""
    try:
        deg = ROTATION_SPEED * seconds
        _publish("/arm_cmd/wrist_yaw", "std_msgs/Float32", {"data": deg})
        time.sleep(seconds)
        return f"Wrist rotated left: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"


def turn_right(seconds: float = 1.5) -> str:
    """Rotate wrist clockwise (Z-axis yaw)."""
    try:
        deg = ROTATION_SPEED * seconds
        _publish("/arm_cmd/wrist_yaw", "std_msgs/Float32", {"data": -deg})
        time.sleep(seconds)
        return f"Wrist rotated right: {deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"


def stop() -> str:
    """Hold current position — send zero velocity."""
    try:
        _publish("/arm_cmd/cartesian", "geometry_msgs/Vector3",
                 {"x": 0.0, "y": 0.0, "z": 0.0})
        return "Arm holding position."
    except Exception as exc:
        return f"Error in stop: {exc}"