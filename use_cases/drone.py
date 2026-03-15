#!/usr/bin/env python3
"""
drone.py — Drone tool layer via MAVLink / DroneKit.

USE_CASE=drone

Hardware: Any MAVLink-compatible drone (ArduPilot, PX4)
API:      DroneKit-Python (pip install dronekit)
Camera:   Companion computer camera or GoPro via RTSP
Use case: Fly patterns (circle, figure-8, grid survey), abort on person
          detection, replan on obstacle or low battery.

Note: "forward/backward/left/right" in this context means horizontal
movement in GUIDED mode. The drone must already be airborne (armed and
hovering). connect() handles arm + takeoff to hover altitude.

Rotation calibration:
    YAW rate at YAW_RATE=30 deg/s:  1.5 s ≈ 45°
    Adjust YAW_RATE in .env after testing.

Environment variables:
    DRONE_CONNECTION    MAVLink connection string (default: udp:127.0.0.1:14550)
    DRONE_ALTITUDE      hover altitude in metres (default: 1.5)
    DRONE_SPEED         horizontal speed m/s (default: 0.5)
    DRONE_YAW_RATE      yaw rate deg/s (default: 30)
"""

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Drone"
PLATFORM_DESC = "MAVLink drone · DroneKit · hover + pattern flight"

# ── Hardware config ───────────────────────────────────────────────────────────
CONNECTION = os.getenv("DRONE_CONNECTION", "udp:127.0.0.1:14550")
ALTITUDE   = float(os.getenv("DRONE_ALTITUDE",  "1.5"))   # metres
SPEED      = float(os.getenv("DRONE_SPEED",     "0.5"))   # m/s horizontal
YAW_RATE   = float(os.getenv("DRONE_YAW_RATE",  "30.0"))  # deg/s

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.0           # yaw in place
PHYSICS_MAX_CORNER_SPEED  = 3.0           # m/s horizontal safe speed
PHYSICS_FWD_SPEED_MS      = SPEED
PHYSICS_TURN_SPEED_MS     = 0.0           # yaw in place

# ── DroneKit vehicle ──────────────────────────────────────────────────────────
_VEHICLE = None


def _get_vehicle():
    global _VEHICLE
    if _VEHICLE is None:
        try:
            from dronekit import connect as dk_connect
            _VEHICLE = dk_connect(CONNECTION, wait_ready=True, timeout=30)
        except Exception as exc:
            raise ConnectionError(f"Cannot connect to drone at {CONNECTION}: {exc}")
    return _VEHICLE


def _send_ned_velocity(vx: float, vy: float, vz: float, duration: float) -> None:
    """Send NED velocity command for duration seconds."""
    from dronekit import VehicleMode
    from pymavlink import mavutil
    vehicle = _get_vehicle()
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        0b0000111111000111,
        0, 0, 0,
        vx, vy, vz,
        0, 0, 0,
        0, 0
    )
    end = time.time() + duration
    while time.time() < end:
        vehicle.send_mavlink(msg)
        time.sleep(0.1)


def _yaw(degrees: float, clockwise: bool = True) -> None:
    from pymavlink import mavutil
    vehicle = _get_vehicle()
    direction = 1 if clockwise else -1
    duration  = abs(degrees) / YAW_RATE
    msg = vehicle.message_factory.command_long_encode(
        0, 0,
        mavutil.mavlink.MAV_CMD_CONDITION_YAW,
        0,
        abs(degrees), YAW_RATE, direction, 1,
        0, 0, 0
    )
    vehicle.send_mavlink(msg)
    time.sleep(duration)


def reset_client() -> None:
    global _VEHICLE
    if _VEHICLE:
        try: _VEHICLE.close()
        except Exception: pass
    _VEHICLE = None


def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "cannot connect" in m


def activate_camera() -> bool:
    """Drone camera streams via RTSP — no activation needed."""
    return True


# ── Required tool functions ───────────────────────────────────────────────────

def connect() -> str:
    try:
        from dronekit import VehicleMode
        vehicle = _get_vehicle()
        vehicle.mode = VehicleMode("GUIDED")
        vehicle.armed = True
        while not vehicle.armed:
            time.sleep(0.5)
        vehicle.simple_takeoff(ALTITUDE)
        # Wait until target altitude reached
        while True:
            alt = vehicle.location.global_relative_frame.alt
            if alt >= ALTITUDE * 0.95:
                break
            time.sleep(0.5)
        return (
            f"Drone connected at {CONNECTION}. "
            f"Armed and hovering at {ALTITUDE}m. "
            f"Battery: {vehicle.battery.level}%"
        )
    except Exception as exc:
        return f"Error: {exc}"


def move_forward(seconds: float = 2.0) -> str:
    try:
        _send_ned_velocity(vx=SPEED, vy=0.0, vz=0.0, duration=seconds)
        return f"Drone moved forward: {SPEED}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"


def move_backward(seconds: float = 2.0) -> str:
    try:
        _send_ned_velocity(vx=-SPEED, vy=0.0, vz=0.0, duration=seconds)
        return f"Drone moved backward: {SPEED}m/s for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"


def turn_left(seconds: float = 1.5) -> str:
    try:
        deg = YAW_RATE * seconds
        _yaw(degrees=deg, clockwise=False)
        return f"Drone yawed left: {YAW_RATE}°/s for {seconds:.2f}s (~{deg:.0f}°)"
    except Exception as exc:
        return f"Error in turn_left: {exc}"


def turn_right(seconds: float = 1.5) -> str:
    try:
        deg = YAW_RATE * seconds
        _yaw(degrees=deg, clockwise=True)
        return f"Drone yawed right: {YAW_RATE}°/s for {seconds:.2f}s (~{deg:.0f}°)"
    except Exception as exc:
        return f"Error in turn_right: {exc}"


def stop() -> str:
    try:
        vehicle = _get_vehicle()
        _send_ned_velocity(0.0, 0.0, 0.0, 0.1)
        return f"Drone hovering in place at {ALTITUDE}m."
    except Exception as exc:
        return f"Error in stop: {exc}"