#!/usr/bin/env python3
"""
DeepRacer navigation tools for Phase 1 agentic navigation planner.

Uses the DeepRacer web console control library (aws-deepracer-control-v2)
to drive the car via its HTTP API. Steering follows the direction of movement
(forward = negative throttle; turns use same forward direction).
"""

import io
import os
import time
from contextlib import redirect_stdout
from pathlib import Path

from dotenv import load_dotenv
from strands import tool

import aws_deepracer_control_v2 as drctl

# Load .env from this package directory
load_dotenv(Path(__file__).resolve().parent / ".env")

IP = os.getenv("DEEPRACER_IP", "192.168.0.3")
PASSWORD = os.getenv("DEEPRACER_PASSWORD")

FWD_THROTTLE = float(os.getenv("DEEPRACER_FWD_THROTTLE", "0.3"))
TURN_THROTTLE = float(os.getenv("DEEPRACER_TURN_THROTTLE", "0.2"))
MAX_SPEED = float(os.getenv("DEEPRACER_MAX_SPEED", "1.0"))
STEER_ANGLE = float(os.getenv("DEEPRACER_STEER_ANGLE", "0.5"))

_CLIENT = None


def _get_client():
    """Create or return a cached DeepRacer Client."""
    global _CLIENT
    if PASSWORD is None or PASSWORD == "":
        raise RuntimeError("DEEPRACER_PASSWORD is not set in environment")
    if _CLIENT is None:
        _CLIENT = drctl.Client(password=PASSWORD, ip=IP)
    return _CLIENT


def _ensure_motors_ready(client):
    """Best-effort: put car into manual mode and start motors."""
    try:
        client.set_manual_mode()
    except Exception as exc:
        print(f"Warning: set_manual_mode failed: {exc}. Continuing.")
    try:
        client.start_car()
    except Exception as exc:
        print(f"Warning: start_car failed: {exc}. Continuing.")


def _move_for_duration(steering, throttle, seconds, max_speed=None):
    """Common movement helper: client.move + sleep + stop."""
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error creating DeepRacer client: {exc}"

    _ensure_motors_ready(client)
    if max_speed is None:
        max_speed = MAX_SPEED

    try:
        client.move(steering, throttle, max_speed)
        time.sleep(float(seconds))
    except Exception as exc:
        return f"Error during move: {exc}"
    finally:
        try:
            client.stop_car()
        except Exception as exc:
            return f"Warning: stop_car failed after move: {exc}"

    return (
        f"Moved steering={steering}, throttle={throttle} "
        f"for {float(seconds):.2f}s (max_speed={max_speed})."
    )


@tool
def deepracer_connect() -> str:
    """
    Connect to the DeepRacer via web API and show basic vehicle info.
    Use this first to verify IP/password and battery state.
    """
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error creating DeepRacer client: {exc}"

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            client.show_vehicle_info()
    except Exception as exc:
        return f"Error calling show_vehicle_info: {exc}"

    out = buf.getvalue().strip()
    return out or f"Connected to DeepRacer at {IP}."


@tool
def deepracer_move_forward(seconds: float = 2.0) -> str:
    """Move the DeepRacer forward for the given number of seconds."""
    return _move_for_duration(0.0, -FWD_THROTTLE, seconds)


@tool
def deepracer_move_backward(seconds: float = 2.0) -> str:
    """Move the DeepRacer backward for the given number of seconds."""
    return _move_for_duration(0.0, FWD_THROTTLE, seconds)


@tool
def deepracer_turn_left(seconds: float = 2.0) -> str:
    """Turn the DeepRacer left while moving slowly forward."""
    return _move_for_duration(-STEER_ANGLE, -TURN_THROTTLE, seconds)


@tool
def deepracer_turn_right(seconds: float = 2.0) -> str:
    """Turn the DeepRacer right while moving slowly forward."""
    return _move_for_duration(STEER_ANGLE, -TURN_THROTTLE, seconds)


@tool
def deepracer_stop() -> str:
    """Immediately stop the DeepRacer."""
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error creating DeepRacer client: {exc}"

    try:
        client.stop_car()
    except Exception as exc:
        return f"Error calling stop_car: {exc}"
    return "Sent stop command to DeepRacer."
