#!/usr/bin/env python3
"""
Phase 1: Agentic Navigation Planner — agent logic only.

Provides:
  - create_planner() -> Strands Agent that returns JSON plans
  - plan_navigation(planner, user_request) -> plan dict
  - execute_plan(plan) -> list of (step, result) tuples

No terminal I/O; use main.py for CLI.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from strands import Agent

from deepracer_tools import (
    deepracer_connect,
    deepracer_move_forward,
    deepracer_move_backward,
    deepracer_turn_left,
    deepracer_turn_right,
    deepracer_stop,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"

PLANNER_PROMPT = """
You are a navigation planner for an AWS DeepRacer car.
Given a natural-language driving request, you MUST respond with a JSON object
describing a sequence of high-level actions. Do not include any explanation,
markdown, or text outside the JSON.

The JSON format MUST be:
{
  "steps": [
    {
      "action": "<action_name>",
      "seconds": <float_seconds_optional>
    },
    ...
  ]
}

Allowed action_name values:
- "connect"   : check connection / battery before moving
- "forward"   : move forward
- "backward"  : move backward
- "left"      : turn left while moving slowly forward
- "right"     : turn right while moving slowly forward
- "stop"      : issue an immediate stop command

Rules:
- Prefer short durations (1.0–3.0 seconds) for movement actions.
- The "stop" action MUST NOT include a "seconds" field.
- For "connect", omit "seconds".
- If the user does not specify duration, choose a safe default (around 2.0).
- If the user clearly asks to stop at the end, make sure the last step is "stop".
- If the instruction is unsafe or unclear, create a conservative plan or a
  single "stop" step and rely on the caller to inform the user.

- For requests like "do a full circle", "go around completely", or "u-turn",
  approximate this by chaining multiple steps that keep the steering direction
  consistent (all "left" or all "right") until the car roughly returns to its
  starting orientation. Do NOT generate a single step that says things like
  "turn 180 degrees"; instead, break it into smaller same-direction turning
  segments with forward motion.
"""


def create_planner(model: str | None = None) -> Agent:
    """Build the navigation planner agent (no tools, JSON plan output)."""
    m = model or os.getenv("MODEL", DEFAULT_MODEL)
    return Agent(
        model=m,
        tools=[],
        system_prompt=PLANNER_PROMPT,
    )


def plan_navigation(planner: Agent, user_request: str) -> Dict[str, Any]:
    """Get a navigation plan (JSON) from the LLM. Raises on parse failure."""
    raw = planner(user_request)
    if isinstance(raw, dict):
        data = raw
    else:
        text = str(raw).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = "\n".join(text.split("\n")[1:])
        data = json.loads(text)
    if "steps" not in data or not isinstance(data["steps"], list):
        raise ValueError("Planner response missing 'steps' list")
    return data


def execute_step(step: Dict[str, Any]) -> str:
    """Run one step via deepracer_tools. Returns result message."""
    action = str(step.get("action", "")).lower()
    seconds = step.get("seconds")

    if action in {"forward", "backward", "left", "right"}:
        if seconds is None:
            seconds = 2.0
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            seconds = 2.0

    if action == "connect":
        return deepracer_connect()
    if action == "forward":
        return deepracer_move_forward(seconds=seconds)
    if action == "backward":
        return deepracer_move_backward(seconds=seconds)
    if action == "left":
        return deepracer_turn_left(seconds=seconds)
    if action == "right":
        return deepracer_turn_right(seconds=seconds)
    if action == "stop":
        return deepracer_stop()

    return f"Skipped unknown action '{action}'."


def execute_plan(plan: Dict[str, Any]) -> List[Tuple[Dict[str, Any], str]]:
    """
    Run all steps in the plan. No I/O; returns list of (step, result) for each step.
    """
    steps: List[Dict[str, Any]] = plan.get("steps", [])
    results: List[Tuple[Dict[str, Any], str]] = []
    for step in steps:
        result = execute_step(step)
        results.append((step, result))
    return results
