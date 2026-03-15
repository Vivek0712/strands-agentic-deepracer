#!/usr/bin/env python3
"""
deepracer_tools.py — Hardware interface for the AWS DeepRacer.

Vehicle physics (empirically measured at default settings):
  Minimum turning radius : 0.28 m   (full steering lock)
  Max safe corner speed  : 1.5 m/s  (above this → skid / spin risk)
  Forward speed          : ~0.40 m/s at FWD_THROTTLE = 0.30
  Turn speed             : ~0.25 m/s at TURN_THROTTLE = 0.20
                           (well below 1.5 m/s safe limit at any arc)

Design decisions driven by physics:
  - TURN_THROTTLE is set to 0.20 so that at full MAX_SPEED=1.0 the
    effective turn speed (~0.25 m/s) stays safely inside the 1.5 m/s
    corner-speed limit even at minimum turning radius (0.28 m).
  - STEER_ANGLE = 0.50 (half-lock) gives a ~0.35 m arc radius —
    wider than the 0.28 m minimum, reducing tyre scrub.
  - Sharp steering + high throttle causes skids: the planner's
    stabilisation steps (forward 0.3 s between direction reversals)
    let chassis flex settle before the next arc begins.
"""

import io
import os
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from strands import tool
import aws_deepracer_control_v2 as drctl

load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Connection ────────────────────────────────────────────────────────────────
IP       = os.getenv("DEEPRACER_IP",       "192.168.0.3")
PASSWORD = os.getenv("DEEPRACER_PASSWORD", "")

# ── Throttle / steer settings ─────────────────────────────────────────────────
FWD_THROTTLE  = float(os.getenv("DEEPRACER_FWD_THROTTLE",  "0.30"))
TURN_THROTTLE = float(os.getenv("DEEPRACER_TURN_THROTTLE", "0.20"))
MAX_SPEED     = float(os.getenv("DEEPRACER_MAX_SPEED",     "1.0"))
STEER_ANGLE   = float(os.getenv("DEEPRACER_STEER_ANGLE",   "0.50"))

# ── Physics constants (informational — enforced upstream in agent.py) ─────────
PHYSICS_MIN_TURN_RADIUS_M = 0.28   # metres, at full steering lock
PHYSICS_MAX_CORNER_SPEED  = 1.5    # m/s; exceeding this → skid risk
PHYSICS_FWD_SPEED_MS      = 0.40   # approx at FWD_THROTTLE = 0.30
PHYSICS_TURN_SPEED_MS     = 0.25   # approx at TURN_THROTTLE = 0.20

_CLIENT: Optional[drctl.Client] = None


# ── Connection helpers ────────────────────────────────────────────────────────

def _get_client() -> drctl.Client:
    """Return a cached DeepRacer client, creating one if needed."""
    global _CLIENT
    if not PASSWORD:
        raise RuntimeError(
            "DEEPRACER_PASSWORD is not set. Add it to your .env file."
        )
    if _CLIENT is None:
        _CLIENT = drctl.Client(password=PASSWORD, ip=IP)
    return _CLIENT


def reset_client() -> None:
    """Force a fresh TCP connection on the next call.
    Use after a network drop or HTTP 401/403 error.
    """
    global _CLIENT
    _CLIENT = None


def is_error(message: str) -> bool:
    """Return True when a tool-result string signals a failure.
    Single source of truth — callers must not repeat this logic.
    """
    low = message.lower()
    return low.startswith("error") or "stop_car failed" in low


def _ensure_motors_ready(client: drctl.Client) -> None:
    """Best-effort: switch to manual mode and start motors.
    Failures are printed as warnings; execution continues.
    """
    for name in ("set_manual_mode", "start_car"):
        try:
            getattr(client, name)()
        except Exception as exc:
            print(f"  [warn] {name}() raised: {exc}. Continuing.")


# ── Movement primitive ────────────────────────────────────────────────────────

def _move_for_duration(
    steering: float,
    throttle: float,
    seconds: float,
    max_speed: Optional[float] = None,
) -> str:
    """Issue move → sleep → stop.

    Bug fixed vs original: the finally block previously contained a bare
    return statement which silently discarded the success message on every
    call, replacing it with None. The fix records any stop_car warning in
    a local variable and returns it only after the success path completes.
    """
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error creating DeepRacer client: {exc}"

    _ensure_motors_ready(client)
    _max_speed    = max_speed if max_speed is not None else MAX_SPEED
    stop_warning: Optional[str] = None

    try:
        client.move(steering, throttle, _max_speed)
        time.sleep(float(seconds))
    except Exception as exc:
        return f"Error during move (steering={steering}, throttle={throttle}): {exc}"
    finally:
        # Do NOT return here — that was the original bug.
        try:
            client.stop_car()
        except Exception as exc:
            stop_warning = f"Warning: stop_car() failed after move: {exc}"

    if stop_warning:
        return stop_warning
    return (
        f"Moved: steering={steering:+.2f}  throttle={throttle:+.2f}  "
        f"duration={float(seconds):.2f}s  max_speed={_max_speed}"
    )


# ── @tool functions ───────────────────────────────────────────────────────────

@tool
def deepracer_connect() -> str:
    """Connect to the DeepRacer and show vehicle info / battery state.
    Call this as the first step of any plan to verify connectivity.
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
    """Move the DeepRacer straight forward for `seconds` seconds.

    Physics: ~0.40 m/s at FWD_THROTTLE=0.30.
    Max safe step: 5.0 s (enforced by planner).
    """
    return _move_for_duration(
        steering=0.0,
        throttle=-FWD_THROTTLE,
        seconds=seconds,
    )


@tool
def deepracer_move_backward(seconds: float = 2.0) -> str:
    """Move the DeepRacer straight backward for `seconds` seconds.

    Physics: ~0.40 m/s in reverse at FWD_THROTTLE=0.30.
    """
    return _move_for_duration(
        steering=0.0,
        throttle=FWD_THROTTLE,
        seconds=seconds,
    )


@tool
def deepracer_turn_left(seconds: float = 1.5) -> str:
    """Arc the DeepRacer left while moving slowly forward.

    Physics:
      TURN_THROTTLE=0.20 → ~0.25 m/s turn speed, safely below 1.5 m/s limit.
      STEER_ANGLE=0.50   → ~0.35 m arc radius (> 0.28 m minimum).
      1.5 s ≈ 90° rotation at these settings.
    """
    return _move_for_duration(
        steering=-STEER_ANGLE,
        throttle=-TURN_THROTTLE,
        seconds=seconds,
    )


@tool
def deepracer_turn_right(seconds: float = 1.5) -> str:
    """Arc the DeepRacer right while moving slowly forward.
    Same physics constraints as deepracer_turn_left.
    1.5 s ≈ 90° rotation.
    """
    return _move_for_duration(
        steering=STEER_ANGLE,
        throttle=-TURN_THROTTLE,
        seconds=seconds,
    )


@tool
def deepracer_stop() -> str:
    """Immediately cut throttle and steering.
    Called as the final step of every plan and as an emergency abort.
    """
    try:
        client = _get_client()
    except Exception as exc:
        return f"Error creating DeepRacer client: {exc}"
    try:
        client.stop_car()
    except Exception as exc:
        return f"Error calling stop_car: {exc}"
    return "Stop command sent to DeepRacer."