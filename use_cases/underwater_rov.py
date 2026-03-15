#!/usr/bin/env python3
"""
underwater_rov.py — Underwater ROV (Remotely Operated Vehicle) tool layer.

USE_CASE=underwater_rov

Hardware: Small underwater ROV (e.g. BlueROV2, OpenROV, custom thruster build)
API:      MAVLink via UDP (ArduSub) or TCP REST API (BlueOS companion)
Camera:   Forward-facing underwater camera
Use case: Coral reef survey patterns, hull inspection, pipe inspection,
          stop on structural damage / crack / marine life of interest,
          replan around low-visibility areas or strong current.

Movement model: 6-DOF thruster array — forward/backward/up/down/yaw.
"forward/backward" = forward/backward thrusters
"turn left/right"  = differential yaw via port/starboard thrusters

Rotation calibration: At YAW_RATE=20 deg/s: 1.5 s ≈ 30° heading change.
Underwater drag means turning is slower than aerial.

Environment variables:
    ROV_CONNECTION      MAVLink string (default: udp:192.168.2.1:14550)
    ROV_DEPTH_M         operating depth hold in metres (default 1.0)
    ROV_SPEED           forward thrust -1.0 to 1.0 (default 0.4)
    ROV_YAW_RATE        yaw rate deg/s (default 20)
"""

import logging
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# ── Platform metadata ─────────────────────────────────────────────────────────
PLATFORM_NAME = "Underwater ROV"
PLATFORM_DESC = "ArduSub ROV · 6-DOF thruster · hull/reef inspection"

# ── Hardware config ───────────────────────────────────────────────────────────
CONNECTION = os.getenv("ROV_CONNECTION", "udp:192.168.2.1:14550")
DEPTH_M    = float(os.getenv("ROV_DEPTH_M",   "1.0"))
SPEED      = float(os.getenv("ROV_SPEED",     "0.4"))
YAW_RATE   = float(os.getenv("ROV_YAW_RATE",  "20.0"))

# ── Physics constants ─────────────────────────────────────────────────────────
PHYSICS_MIN_TURN_RADIUS_M = 0.5
PHYSICS_MAX_CORNER_SPEED  = 1.5
PHYSICS_FWD_SPEED_MS      = SPEED * 1.2
PHYSICS_TURN_SPEED_MS     = SPEED * 0.8

# ── ArduSub vehicle ───────────────────────────────────────────────────────────
_VEHICLE = None

def _get_vehicle():
    global _VEHICLE
    if _VEHICLE is None:
        from dronekit import connect as dk_connect
        _VEHICLE = dk_connect(CONNECTION, wait_ready=False, timeout=20)
    return _VEHICLE

def _set_rc_override(pitch=1500, roll=1500, throttle=1500, yaw=1500,
                     forward=1500, lateral=1500):
    """ArduSub uses 6-channel RC override for thruster control."""
    vehicle = _get_vehicle()
    msg = vehicle.message_factory.rc_channels_override_encode(
        0, 0, pitch, roll, throttle, yaw, forward, lateral, 0, 0
    )
    vehicle.send_mavlink(msg)

def _move(fwd: float, yaw_delta: float, duration: float):
    """
    fwd:       -1.0 to 1.0 (forward thrust)
    yaw_delta: -1.0 to 1.0 (yaw rate)
    """
    fwd_rc = int(1500 + fwd       * 400)
    yaw_rc = int(1500 + yaw_delta * 400)
    _set_rc_override(throttle=1500, yaw=yaw_rc, forward=fwd_rc)
    time.sleep(duration)
    _set_rc_override()  # neutral

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
        from dronekit import VehicleMode
        vehicle = _get_vehicle()
        vehicle.mode = VehicleMode("ALT_HOLD")
        return (
            f"ROV connected at {CONNECTION}. "
            f"Mode: ALT_HOLD at {DEPTH_M}m depth. "
            f"Battery: {vehicle.battery.voltage:.1f}V."
        )
    except Exception as exc:
        return f"Error: {exc}"

def move_forward(seconds: float = 2.0) -> str:
    try:
        _move(fwd=SPEED, yaw_delta=0.0, duration=seconds)
        return f"ROV moved forward: thrust={SPEED} for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_forward: {exc}"

def move_backward(seconds: float = 2.0) -> str:
    try:
        _move(fwd=-SPEED, yaw_delta=0.0, duration=seconds)
        return f"ROV moved backward: thrust={SPEED} for {seconds:.2f}s"
    except Exception as exc:
        return f"Error in move_backward: {exc}"

def turn_left(seconds: float = 1.5) -> str:
    try:
        _move(fwd=0.0, yaw_delta=-SPEED, duration=seconds)
        deg = YAW_RATE * seconds
        return f"ROV yawed left: ~{deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_left: {exc}"

def turn_right(seconds: float = 1.5) -> str:
    try:
        _move(fwd=0.0, yaw_delta=SPEED, duration=seconds)
        deg = YAW_RATE * seconds
        return f"ROV yawed right: ~{deg:.1f}° in {seconds:.2f}s"
    except Exception as exc:
        return f"Error in turn_right: {exc}"

def stop() -> str:
    try:
        _set_rc_override()  # all channels neutral
        return f"ROV stopped. Hovering at ~{DEPTH_M}m."
    except Exception as exc:
        return f"Error in stop: {exc}"
