#!/usr/bin/env python3
"""
boat.py — Autonomous surface vessel (ASV) tool layer.

USE_CASE=boat

Hardware: Small autonomous boat / USV with differential thrust
          (e.g. BlueBoat, custom twin-motor hull)
API:      ArduPilot SITL or real boat via MAVLink TCP/UDP
Camera:   Forward-facing waterproof camera
Use case: Navigate waterways, inspect buoys/structures, stop when swimmer
          or debris is detected in path, survey patterns (lawnmower/parallel
          transects over water), replan around unexpected floating obstacles.

Movement model: differential thrust — left motor + right motor.
"forward" = both motors forward
"turn left" = right motor more than left
ArduPilot GUIDED mode handles the low-level thrust mixing.

Rotation calibration: At YAW_RATE=20 deg/s: 1.5 s ≈ 30° heading change.
Water resistance means turning is slower than land robots.

Environment variables:
    BOAT_CONNECTION     MAVLink connection string (default: udp:127.0.0.1:14550)
    BOAT_SPEED          forward thrust 0.0–1.0 (default 0.4)
    BOAT_YAW_RATE       yaw rate deg/s (default 20)
"""

import logging
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Autonomous Boat"
PLATFORM_DESC = "Surface vessel · MAVLink · waterway navigation · swimmer detection"

# ── Hardware config ───────────────────────────────────────────────────────────
CONNECTION = os.getenv("BOAT_CONNECTION", "udp:127.0.0.1:14550")
SPEED      = float(os.getenv("BOAT_SPEED",     "0.4"))   # 0.0–1.0 throttle
YAW_RATE   = float(os.getenv("BOAT_YAW_RATE",  "20.0"))  # deg/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 1.5    # boats need space to turn
PHYSICS_MAX_CORNER_SPEED  = 2.0    # m/s safe speed on water
PHYSICS_FWD_SPEED_MS      = SPEED * 2.0   # approx m/s at SPEED=0.4
PHYSICS_TURN_SPEED_MS     = SPEED * 1.0

# ── DroneKit vehicle ──────────────────────────────────────────────────────────
_VEHICLE = None

def _get_vehicle():
    global _VEHICLE
    if _VEHICLE is None:
        from dronekit import connect as dk_connect
        _VEHICLE = dk_connect(CONNECTION, wait_ready=True, timeout=30)
    return _VEHICLE

def _set_rc(channel: int, value: int):
    """Override RC channel. value: 1000 (full reverse) to 2000 (full fwd)."""
    from pymavlink import mavutil
    vehicle = _get_vehicle()
    msg = vehicle.message_factory.rc_channels_override_encode(
        0, 0,
        *([65535] * (channel - 1)), value, *([65535] * (8 - channel))
    )
    vehicle.send_mavlink(msg)

def _thrust(left: float, right: float, duration: float):
    """
    Set differential thrust for duration seconds.
    left/right: -1.0 (full reverse) to 1.0 (full forward)
    """
    from dronekit import VehicleMode
    vehicle = _get_vehicle()
    vehicle.mode = VehicleMode("MANUAL")

    # Map -1..1 to RC 1000..2000
    l_rc = int(1500 + left  * 500)
    r_rc = int(1500 + right * 500)

    # Throttle: ch3 = left motor, ch1 = right motor (adjust to your ESC mapping)
    _set_rc(3, l_rc)
    _set_rc(1, r_rc)
    time.sleep(duration)
    # Neutral
    _set_rc(3, 1500)
    _set_rc(1, 1500)

def reset_client():
    global _VEHICLE
    if _VEHICLE:
        try: _VEHICLE.close()
        except Exception: pass
    _VEHICLE = None

def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m

def activate_camera() -> bool:
    return True

# ── Tool functions ────────────────────────────────────────────────────────────

def connect() -> str:
    try:
        vehicle = _get_vehicle()
        return (
            f"Boat connected at {CONNECTION}. "
            f"Mode: {vehicle.mode.name}. "
            f"Battery: {vehicle.battery.level}%. "
            f"GPS: {vehicle.location.global_frame.lat:.6f}, "
            f"{vehicle.location.global_frame.lon:.6f}"
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        _thrust(SPEED, SPEED, seconds)
        return f"Boat moved forward: thrust={SPEED} for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _thrust(-SPEED, -SPEED, seconds)
        return f"Boat moved backward: thrust={SPEED} for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _thrust(SPEED * 0.2, SPEED, seconds)
        deg = YAW_RATE * seconds
        return f"Boat turned left: ~{deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _thrust(SPEED, SPEED * 0.2, seconds)
        deg = YAW_RATE * seconds
        return f"Boat turned right: ~{deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _thrust(0.0, 0.0, 0.1)
        return "Boat stopped. Holding position."
    except Exception as exc:
        return f"Error in stop: {exc}"
