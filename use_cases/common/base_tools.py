#!/usr/bin/env python3
"""
base_tools.py — Abstract interface for any robot tool layer.

Every use case file ({use_case}.py) must implement this protocol.
The common code (agent.py, camera_policy.py, deepracer_agent_tool.py)
imports tools through this interface, making the execution engine
hardware-agnostic.

REQUIRED exports from every {use_case}.py:
  Functions (callable, no decorator required):
    connect()              → str
    move_forward(seconds)  → str
    move_backward(seconds) → str
    turn_left(seconds)     → str
    turn_right(seconds)    → str
    stop()                 → str
    is_error(message)      → bool
    reset_client()         → None
    activate_camera()      → bool   (return True if no camera)

  Physics constants (float):
    PHYSICS_MIN_TURN_RADIUS_M   minimum arc radius in metres
    PHYSICS_MAX_CORNER_SPEED    max safe speed in m/s
    PHYSICS_FWD_SPEED_MS        typical forward speed in m/s
    PHYSICS_TURN_SPEED_MS       typical turning speed in m/s

  Optional:
    PLATFORM_NAME       str  — displayed in dashboard title
    PLATFORM_DESC       str  — one-line description for the UI
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class RobotTools(Protocol):
    """
    Structural protocol — any module that exposes these names satisfies it.
    Use `isinstance(module_or_obj, RobotTools)` to check at runtime.
    """

    def connect(self) -> str: ...
    def move_forward(self, seconds: float) -> str: ...
    def move_backward(self, seconds: float) -> str: ...
    def turn_left(self, seconds: float) -> str: ...
    def turn_right(self, seconds: float) -> str: ...
    def stop(self) -> str: ...
    def is_error(self, message: str) -> bool: ...
    def reset_client(self) -> None: ...
    def activate_camera(self) -> bool: ...

    PHYSICS_MIN_TURN_RADIUS_M: float
    PHYSICS_MAX_CORNER_SPEED:  float
    PHYSICS_FWD_SPEED_MS:      float
    PHYSICS_TURN_SPEED_MS:     float


def load_tools(use_case: str):
    """
    Dynamically load a use case tool module by name.

    Usage:
        tools = load_tools("deepracer")    # loads deepracer.py
        tools = load_tools("drone")        # loads drone.py
        tools = load_tools("warehouse_robot")

    The returned module is used to monkey-patch the common agent.py
    execution layer at startup. See main.py for the --use-case flag.
    """
    import importlib
    import sys
    import os

    # Look in the use_cases directory
    use_cases_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir    = os.path.dirname(use_cases_dir)

    for search_dir in [use_cases_dir, parent_dir]:
        candidate = os.path.join(search_dir, f"{use_case}.py")
        if os.path.isfile(candidate):
            spec   = importlib.util.spec_from_file_location(use_case, candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules[use_case] = module
            spec.loader.exec_module(module)
            return module

    raise ImportError(
        f"No tool module found for use case '{use_case}'. "
        f"Expected a file named '{use_case}.py' in {use_cases_dir}"
    )


# ── Required attribute names ──────────────────────────────────────────────────
# Use these constants in use case files to avoid typos.

REQUIRED_FUNCTIONS = (
    "connect",
    "move_forward",
    "move_backward",
    "turn_left",
    "turn_right",
    "stop",
    "is_error",
    "reset_client",
    "activate_camera",
)

REQUIRED_PHYSICS = (
    "PHYSICS_MIN_TURN_RADIUS_M",
    "PHYSICS_MAX_CORNER_SPEED",
    "PHYSICS_FWD_SPEED_MS",
    "PHYSICS_TURN_SPEED_MS",
)


def validate_tools(module) -> list[str]:
    """
    Return a list of missing required names from a tool module.
    Empty list means the module is valid.

    Usage:
        errors = validate_tools(load_tools("drone"))
        if errors:
            raise RuntimeError(f"drone.py is missing: {errors}")
    """
    missing = []
    for name in REQUIRED_FUNCTIONS + REQUIRED_PHYSICS:
        if not hasattr(module, name):
            missing.append(name)
    return missing