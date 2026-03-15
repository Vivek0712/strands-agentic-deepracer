#!/usr/bin/env python3
"""
agent.py — Agentic Navigation Planner for the AWS DeepRacer.

Public API (imported by main.py):
    create_planner()               -> Strands Agent
    plan_navigation(planner, req)  -> validated plan dict
    validate_plan(plan)            -> raises ValueError on hard violation
    execute_plan(plan)             -> List[Tuple[dict, str]]
    DEFAULT_MODEL                  -> str

Additional API (used by deepracer_agent_tool.py):
    NavigationPolicy, NovaPolicy, MockPolicy, ReplayPolicy
    create_policy(provider, **kw)  -> NavigationPolicy
    StepResult, PlanResult
    execute_step(step)             -> StepResult
    execute_plan_full(plan)        -> PlanResult

Rotation calibration (empirically measured):
    angle    = (duration / 1.5) × 90°
    duration = (angle    / 90)  × 1.5 s

FULL ROTATION CHECK — mandatory before finalising any closed-loop plan:
    total_turn_time = sum of ALL turn step durations in the plan
    total_degrees   = total_turn_time × (90 / 1.5)
    For a complete loop total_degrees MUST equal 360°.

Bug fixed vs previous version:
    Circle tight was 8× left(1.5) = 720° (two full rotations).
    Correct tight circle: 4× left(1.5) = 6.0 s → 360°.

    Large circle was 8× [fwd + left(1.5)] = 720°.
    Correct large circle option A: 4× [fwd + left(1.5)] = 6.0 s → 360°.
    Correct large circle option B: 8× [fwd + left(0.75)] = 6.0 s → 360°.
"""

import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from strands import Agent

from deepracer_tools import (
    deepracer_connect,
    deepracer_move_forward,
    deepracer_move_backward,
    deepracer_turn_left,
    deepracer_turn_right,
    deepracer_stop,
    is_error,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL    = "us.amazon.nova-lite-v1:0"
MAX_STEP_SECONDS = float(os.getenv("DEEPRACER_MAX_STEP_SECS", "5.0"))
MAX_PLAN_STEPS   = 20
VALID_ACTIONS    = frozenset({"connect", "forward", "backward", "left", "right", "stop"})

# Rotation calibration — single source of truth used in both prompt and validator
DEGREES_PER_SECOND   = 90.0 / 1.5     # 60 °/s
SECONDS_PER_DEGREE   = 1.5  / 90.0    # 0.01667 s/°
FULL_ROTATION_SECS   = (360.0 / 90.0) * 1.5   # 6.0 s for 360°

# Patterns that must complete exactly 360° of total heading change
_CLOSED_LOOP_PATTERNS = frozenset({
    "circle", "square", "triangle", "pentagon",
    "hexagon", "oval", "spiral-out", "figure-forward",
})
# figure-8 has two full circles → 720° total
_ROTATION_TOLERANCE_DEG = 5.0   # warning threshold


# ── System prompt ─────────────────────────────────────────────────────────────

PLANNER_PROMPT = """
You are a precision navigation planner for an AWS DeepRacer car.
Your ONLY output is a single raw JSON object — no explanation, no markdown,
no text outside the braces. Output starts with "{" and ends with "}".

══════════════════════════════════════════════════════════════
REQUIRED JSON FORMAT
══════════════════════════════════════════════════════════════

{
  "_reasoning": "<mandatory — fill ALL 8 chain-of-thought points>",
  "pattern":    "<closest named pattern, or 'custom'>",
  "steps": [
    { "action": "<action>", "seconds": <float> },
    ...
  ]
}

Action names — lowercase, exact spelling:
  connect   — health-check before movement; NO "seconds"
  forward   — straight ahead
  backward  — straight reverse
  left      — arc left while moving forward
  right     — arc right while moving forward
  stop      — immediate halt; MUST be the FINAL step; NO "seconds"

══════════════════════════════════════════════════════════════
VEHICLE PHYSICS  ← never violate these
══════════════════════════════════════════════════════════════

  Minimum turning radius : 0.28 m  (full steering lock)
  Max safe corner speed  : 1.5 m/s (above this → skid or spin)
  Forward speed          : ~0.40 m/s  (FWD_THROTTLE = 0.30)
  Turn speed             : ~0.25 m/s  (TURN_THROTTLE = 0.20)
                           → well below 1.5 m/s safe limit

  CRITICAL: sharp steering + high throttle CAUSES SKIDS.
  Do NOT request any change to throttle or steer angle values.

  Arc radius during a turn step ≈ 0.35 m (STEER_ANGLE = 0.50, half-lock).
  Control loop diameter with the forward segment duration between turns.

══════════════════════════════════════════════════════════════
ROTATION CALIBRATION  ← single source of truth for all angle maths
══════════════════════════════════════════════════════════════

  Core fact:   1.5 s of turn time ≈ 90°

  Formulas:
    angle    = (duration / 1.5) × 90°
    duration = (angle    / 90)  × 1.5 s

  Reference table:
     60°  →  1.0 s    (hexagon corner)
     72°  →  1.2 s    (pentagon corner)
     90°  →  1.5 s    (square corner · circle quarter)
    120°  →  2.0 s    (triangle corner)
    180°  →  3.0 s    (U-turn · oval end)
    270°  →  4.5 s    MUST split: 3.0 s + 1.5 s  (cap = 5.0 s per step)
    360°  →  6.0 s    MUST split into steps ≤ 5.0 s each

  ┌─────────────────────────────────────────────────────────────┐
  │  MANDATORY FULL ROTATION CHECK for every closed-loop plan   │
  │                                                             │
  │  total_turn_time = sum of ALL left/right step durations     │
  │  total_degrees   = total_turn_time × (90 / 1.5)            │
  │                                                             │
  │  Complete loop  → total_degrees MUST equal 360°             │
  │  U-turn         → total_degrees MUST equal 180°             │
  │  N-sided polygon→ total_degrees MUST equal 360°             │
  │  Figure-8       → total_degrees MUST equal 720° (2 circles) │
  │                                                             │
  │  If the check fails → RECALCULATE. Never proceed with wrong │
  │  totals. Write "VERIFY: Xs → Y°. ✓" or "VERIFY: WRONG,     │
  │  recalculating." in _reasoning before listing steps.        │
  └─────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════
STEP RULES
══════════════════════════════════════════════════════════════

1. "stop" MUST be the last step. No "seconds" on stop or connect.
2. No single step may exceed 5.0 s.
3. Default durations when user gives none:
     forward / backward → 2.0 s
     left / right       → use calibration table, not a guess
4. STABILISATION — after ANY left→right or right→left reversal insert:
   {"action":"forward","seconds":0.3}
5. Total steps ≤ 20. For longer manoeuvres repeat sub-patterns.
6. Unsafe or ambiguous → abort:
   {"_reasoning":"...","pattern":"abort","steps":[{"action":"stop"}]}

══════════════════════════════════════════════════════════════
NAMED PATTERN LIBRARY  ← rotation check verified for every pattern
══════════════════════════════════════════════════════════════

── CIRCLE (tight, 360°) ──────────────────────────────────────
total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓

  4× {"action":"left","seconds":1.5}   + stop   ← counter-clockwise
  4× {"action":"right","seconds":1.5}  + stop   ← clockwise

  ✗ WRONG (never use): 8× left(1.5) = 720° (TWO full rotations, not one)

── CIRCLE (large diameter, 360°) ─────────────────────────────
Option A — square-path, 4 arcs:
  total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓
  4× [forward(F) + left(1.5)]  + stop
  F controls diameter: 1.0 s → Ø≈0.25 m · 2.0 s → Ø≈0.50 m

Option B — rounder path, 8 shorter arcs:
  per turn = 360° / 8 = 45° → (45/90)×1.5 = 0.75 s
  total_turn_time = 8 × 0.75 = 6.0 s → 360°. ✓
  8× [forward(F) + left(0.75)]  + stop

  ✗ WRONG (never use): 8× [fwd + left(1.5)] = 720° (two rotations)

── U-TURN (180°) ─────────────────────────────────────────────
total_turn_time = 2 × 1.5 = 3.0 s → 180°. ✓

  forward(2.0)
  right(1.5) + right(1.5)
  forward(2.0)
  stop

── FIGURE-8 ──────────────────────────────────────────────────
Phase 1 left circle:  4 × 1.5 = 6.0 s → 360°. ✓
Phase 2 right circle: 4 × 1.5 = 6.0 s → 360°. ✓
Total heading change: 720°. ✓

  4× [forward(1.0) + left(1.5)]
  forward(0.5)
  forward(0.3)                     ← stabilisation (left→right reversal)
  4× [forward(1.0) + right(1.5)]
  stop

── SQUARE ────────────────────────────────────────────────────
4 × 90° = 360°. total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓

  4× [forward(S) + right(1.5)]  + stop
  Default S = 2.0 s. Counter-clockwise: swap right → left.

── TRIANGLE ──────────────────────────────────────────────────
3 × 120° = 360°. duration = (120/90)×1.5 = 2.0 s.
total_turn_time = 3 × 2.0 = 6.0 s → 360°. ✓

  3× [forward(S) + right(2.0)]  + stop

── PENTAGON ──────────────────────────────────────────────────
5 × 72° = 360°. duration = (72/90)×1.5 = 1.2 s.
total_turn_time = 5 × 1.2 = 6.0 s → 360°. ✓

  5× [forward(S) + right(1.2)]  + stop

── HEXAGON ───────────────────────────────────────────────────
6 × 60° = 360°. duration = (60/90)×1.5 = 1.0 s.
total_turn_time = 6 × 1.0 = 6.0 s → 360°. ✓

  6× [forward(S) + right(1.0)]  + stop

── OVAL / RACETRACK ──────────────────────────────────────────
2 × 180° = 360°. duration = (180/90)×1.5 = 3.0 s.
total_turn_time = 2 × 3.0 = 6.0 s → 360°. ✓

  forward(3.0) + right(3.0) + forward(3.0) + right(3.0)  + stop

── SLALOM (N gates) ──────────────────────────────────────────
Each gate: left 90° + right 90° → net 0° heading change. ✓

  forward(1.0)
  N× [ left(T) + forward(0.3) + forward(G)
       + right(T) + forward(0.3) + forward(G) ]
  stop
  Default T = 1.5 s (90°). Narrow gates: T = 1.0 s (60°).
  G = gate spacing duration (default 1.0 s).

── CHICANE ───────────────────────────────────────────────────
left 60° + right 60° → net 0°. total_turn = 2 × 1.0 = 2.0 s → 120°
(symmetric → net heading 0°). ✓

  forward(1.5) + left(1.0) + forward(0.3) + right(1.0) + forward(1.5)
  stop

── LANE CHANGE LEFT ──────────────────────────────────────────
left 60° + right 60° → net 0°. ✓

  forward(1.5) + left(1.0) + forward(0.3) + right(1.0) + forward(2.0)
  stop

── LANE CHANGE RIGHT ─────────────────────────────────────────
  forward(1.5) + right(1.0) + forward(0.3) + left(1.0) + forward(2.0)
  stop

── SPIRAL OUT ────────────────────────────────────────────────
Two rings of 4 arcs each. All left turns (no reversal).
Each ring: 4 × 1.5 = 6.0 s → 360°. ✓ Per ring. ✓

  4× [forward(0.5) + left(1.5)]    ← inner ring
  4× [forward(1.5) + left(1.5)]    ← outer ring
  stop   (swap left → right for clockwise)

  Steps: 4×2 + 4×2 + stop = 17 ≤ 20. ✓
  3-ring version = 25 steps → EXCEEDS cap. Use 2-ring only.

── ZIGZAG ────────────────────────────────────────────────────
Each cycle: left 90° + right 90° → net 0°. ✓

  N× [left(1.5) + forward(0.3) + right(1.5) + forward(0.3)]
  stop

── PARALLEL PARK ─────────────────────────────────────────────
Partial turns, net heading ≈ 0° by end.

  forward(2.0)
  backward(0.5) + right(1.5)
  backward(1.5) + left(1.0)
  forward(0.5)
  stop

── FIGURE-FORWARD ────────────────────────────────────────────
Sprint + 360° loop + return.
total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓

  forward(3.0)
  right(1.5) + right(1.5) + right(1.5) + right(1.5)
  forward(3.0)
  stop

══════════════════════════════════════════════════════════════
MANDATORY CHAIN-OF-THOUGHT  (fill all 8 points in _reasoning)
══════════════════════════════════════════════════════════════

  1. PATTERN  — Which named pattern? Sub-patterns if custom?
  2. HEADING  — Walk every step tracking heading in degrees.
                Start = 0°. left(1.5)→−90°. right(1.5)→+90°.
  3. MATH     — For each corner: duration = (angle/90)×1.5 s.
                Show the arithmetic.
  4. VERIFY   — State: "total_turn_time = Xs → Ydeg."
                Complete loop → Y must equal 360°.
                U-turn → Y must equal 180°.
                Figure-8 → Y must equal 720°.
                If wrong: write "VERIFY: WRONG, recalculating."
                then redo steps 2–3 before continuing.
  5. PHYSICS  — Turn speed 0.25 m/s ≪ 1.5 m/s. Anything risky?
  6. STAB     — List every left↔right reversal; confirm fwd(0.3) inserted.
  7. COUNT    — Total steps. If > 20, simplify.
  8. SAFETY   — Any step > 5.0 s? Split it. Last step is stop?

══════════════════════════════════════════════════════════════
WORKED EXAMPLES
══════════════════════════════════════════════════════════════

── tight circle left ─────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: circle tight left. 2.HEADING: 4×(−90°)=−360°=0°. 3.MATH: 360°→(360/90)×1.5=6.0 s total; 6.0/4=1.5 s per step. 4.VERIFY: total_turn_time=4×1.5=6.0 s → 6.0×(90/1.5)=360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: no reversals. 7.COUNT: 4+stop=5≤20. 8.SAFETY: max 1.5 s≤5.0 s, last=stop. ✓",
  "pattern": "circle",
  "steps": [
    {"action":"left","seconds":1.5},
    {"action":"left","seconds":1.5},
    {"action":"left","seconds":1.5},
    {"action":"left","seconds":1.5},
    {"action":"stop"}
  ]
}

── large circle right, option A ──────────────────────────────
{
  "_reasoning": "1.PATTERN: circle large option-A, 4 arcs. 2.HEADING: 4×(+90°)=+360°=0°. 3.MATH: 360°→6.0 s; 4 turns×1.5 s. F=1.5 s for medium diameter. 4.VERIFY: total_turn_time=4×1.5=6.0 s → 360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: no reversals. 7.COUNT: 4×2+stop=9≤20. 8.SAFETY: max 1.5 s≤5.0 s. ✓",
  "pattern": "circle",
  "steps": [
    {"action":"forward","seconds":1.5},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"right","seconds":1.5},
    {"action":"stop"}
  ]
}

── large circle left, option B (8-segment rounder path) ──────
{
  "_reasoning": "1.PATTERN: circle large option-B, 8 arcs. 2.HEADING: 8×(−45°)=−360°=0°. 3.MATH: per-segment angle=360°/8=45°; duration=(45/90)×1.5=0.75 s. 4.VERIFY: total_turn_time=8×0.75=6.0 s → 6.0×(90/1.5)=360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: no reversals. 7.COUNT: 8×2+stop=17≤20. 8.SAFETY: max 0.75 s≤5.0 s. ✓",
  "pattern": "circle",
  "steps": [
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":0.75},
    {"action":"stop"}
  ]
}

── square ────────────────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: square. 2.HEADING: 0→+90→+180→+270→+360=0. 3.MATH: 90°→(90/90)×1.5=1.5 s. 4.VERIFY: total_turn_time=4×1.5=6.0 s → 360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: no reversals. 7.COUNT: 4×2+stop=9≤20. 8.SAFETY: max 2.0 s≤5.0 s. ✓",
  "pattern": "square",
  "steps": [
    {"action":"forward","seconds":2.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":2.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":2.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":2.0},{"action":"right","seconds":1.5},
    {"action":"stop"}
  ]
}

── triangle ──────────────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: triangle. 2.HEADING: 0→+120→+240→+360=0. 3.MATH: 120°→(120/90)×1.5=2.0 s. 4.VERIFY: total_turn_time=3×2.0=6.0 s → 360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: no reversals. 7.COUNT: 3×2+stop=7≤20. 8.SAFETY: max 2.0 s≤5.0 s. ✓",
  "pattern": "triangle",
  "steps": [
    {"action":"forward","seconds":2.0},{"action":"right","seconds":2.0},
    {"action":"forward","seconds":2.0},{"action":"right","seconds":2.0},
    {"action":"forward","seconds":2.0},{"action":"right","seconds":2.0},
    {"action":"stop"}
  ]
}

── figure-8 ──────────────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: figure-8. 2.HEADING ph1: 4×(−90°)=−360°=0°. ph2: 4×(+90°)=+360°=0°. 3.MATH: 90°→1.5 s each. 4.VERIFY ph1: 4×1.5=6.0 s→360°. ✓ ph2: 4×1.5=6.0 s→360°. ✓ Total: 12.0 s→720°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: left→right at transition → fwd(0.3) inserted. 7.COUNT: 8+2+8+stop=19≤20. 8.SAFETY: max 1.5 s≤5.0 s. ✓",
  "pattern": "figure-8",
  "steps": [
    {"action":"forward","seconds":1.0},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":0.5},
    {"action":"forward","seconds":0.3},
    {"action":"forward","seconds":1.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"right","seconds":1.5},
    {"action":"forward","seconds":1.0},{"action":"right","seconds":1.5},
    {"action":"stop"}
  ]
}

── slalom 3 cones ────────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: slalom N=3. Each gate: left 90° then right 90° → net 0° heading. 3.MATH: 90°→1.5 s each. 4.VERIFY: each gate turn total=1.5+1.5=3.0 s→180° (symmetric, net 0°). ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: left→right each gate → fwd(0.3) after each turn. 7.COUNT: 1+3×6+stop=20≤20. 8.SAFETY: max 1.5 s≤5.0 s. ✓",
  "pattern": "slalom",
  "steps": [
    {"action":"forward","seconds":1.0},
    {"action":"left","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"right","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"left","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"right","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"left","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"right","seconds":1.5},{"action":"forward","seconds":0.3},{"action":"forward","seconds":1.0},
    {"action":"stop"}
  ]
}

── spiral out ────────────────────────────────────────────────
{
  "_reasoning": "1.PATTERN: spiral-out 2-ring. 2.HEADING: ring1 4×(−90°)=−360°=0°; ring2 same. 3.MATH: 90°→1.5 s. 4.VERIFY: ring1: 4×1.5=6.0 s→360°. ✓ ring2: 4×1.5=6.0 s→360°. ✓ 5.PHYSICS: 0.25 m/s ≪1.5 m/s. 6.STAB: all left → no reversal. 7.COUNT: 4×2+4×2+stop=17≤20. 8.SAFETY: max 1.5 s≤5.0 s. ✓",
  "pattern": "spiral-out",
  "steps": [
    {"action":"forward","seconds":0.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":0.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":0.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":0.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"left","seconds":1.5},
    {"action":"forward","seconds":1.5},{"action":"left","seconds":1.5},
    {"action":"stop"}
  ]
}
"""


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    """Outcome of one executed plan step."""
    step:    Dict[str, Any]
    ok:      bool
    message: str

    def display(self) -> str:
        action  = self.step.get("action", "?")
        seconds = self.step.get("seconds")
        icon    = "✓" if self.ok else "✗"
        dur     = f" {seconds}s" if seconds is not None else ""
        return f"  {icon} {action}{dur}  →  {self.message}"


@dataclass
class PlanResult:
    """Aggregate outcome of execute_plan_full()."""
    results:      List[StepResult] = field(default_factory=list)
    aborted:      bool             = False
    abort_reason: str              = ""
    pattern:      str              = "unknown"
    reasoning:    str              = ""

    @property
    def all_ok(self) -> bool:
        return not self.aborted and all(r.ok for r in self.results)

    @property
    def completed_steps(self) -> int:
        return len(self.results)


# ── Policy abstraction ────────────────────────────────────────────────────────

class NavigationPolicy:
    def plan(self, user_request: str) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        raise NotImplementedError


class NovaPolicy(NavigationPolicy):
    def __init__(self, model: Optional[str] = None):
        self._agent = create_planner(model)

    def plan(self, user_request: str) -> Dict[str, Any]:
        return plan_navigation(self._agent, user_request)

    @property
    def provider_name(self) -> str:
        return os.getenv("MODEL", DEFAULT_MODEL)


class MockPolicy(NavigationPolicy):
    def __init__(self, canned_plan: Optional[Dict[str, Any]] = None):
        self._plan = canned_plan or {
            "_reasoning": "Mock policy fixed plan.",
            "pattern": "mock",
            "steps": [
                {"action": "forward", "seconds": 2.0},
                {"action": "stop"},
            ],
        }

    def plan(self, _: str) -> Dict[str, Any]:
        return self._plan

    @property
    def provider_name(self) -> str:
        return "mock"


class ReplayPolicy(NavigationPolicy):
    def __init__(self, library: Dict[str, Dict[str, Any]]):
        self._library = {k.lower(): v for k, v in library.items()}

    def plan(self, user_request: str) -> Dict[str, Any]:
        key = user_request.strip().lower()
        if key not in self._library:
            raise ValueError(
                f"No saved manoeuvre '{key}'. Available: {sorted(self._library)}"
            )
        return self._library[key]

    @property
    def provider_name(self) -> str:
        return "replay"


def create_policy(provider: str = "nova", **kwargs) -> NavigationPolicy:
    table = {"nova": NovaPolicy, "mock": MockPolicy, "replay": ReplayPolicy}
    cls = table.get(provider.lower())
    if cls is None:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {sorted(table)}."
        )
    return cls(**kwargs)


# ── Planner agent ─────────────────────────────────────────────────────────────

def create_planner(model: Optional[str] = None) -> Agent:
    m = model or os.getenv("MODEL", DEFAULT_MODEL)
    return Agent(model=m, tools=[], system_prompt=PLANNER_PROMPT)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$",          "", text)
    return text.strip()


def plan_navigation(planner: Agent, user_request: str) -> Dict[str, Any]:
    raw = planner(user_request)
    if isinstance(raw, dict):
        data = raw
    else:
        data = json.loads(_strip_fences(str(raw)))
    validate_plan(data)
    return data


# ── Rotation checker ──────────────────────────────────────────────────────────

def _check_rotation(plan: Dict[str, Any]) -> None:
    """
    Emit a warning when total turn time is inconsistent with the pattern.

    Uses the calibration constant:  degrees = seconds × (90 / 1.5)

    Closed-loop patterns must accumulate exactly 360° of turn.
    figure-8 must accumulate 720° (two circles).
    Tolerance = 5° to allow for minor floating-point rounding.

    This is a warning, not a hard error, so partial-arc custom plans
    are not rejected.
    """
    pattern = plan.get("pattern", "").lower()
    steps   = plan.get("steps", [])

    total_turn_secs = sum(
        float(s.get("seconds", 0.0))
        for s in steps
        if str(s.get("action", "")).lower() in {"left", "right"}
    )
    total_degrees = total_turn_secs * DEGREES_PER_SECOND

    if pattern == "figure-8":
        expected_secs = 2.0 * FULL_ROTATION_SECS   # 12.0 s → 720°
        expected_deg  = 720.0
    elif pattern in _CLOSED_LOOP_PATTERNS:
        expected_secs = FULL_ROTATION_SECS           # 6.0 s → 360°
        expected_deg  = 360.0
    else:
        return

    tolerance_secs = _ROTATION_TOLERANCE_DEG * SECONDS_PER_DEGREE
    if abs(total_turn_secs - expected_secs) > tolerance_secs:
        warnings.warn(
            f"\n  ⚠ Rotation mismatch — pattern '{pattern}':\n"
            f"    total turn time : {total_turn_secs:.2f}s "
            f"→ {total_degrees:.0f}° actual\n"
            f"    expected        : {expected_secs:.1f}s "
            f"→ {expected_deg:.0f}°\n"
            f"    The car will NOT complete the expected manoeuvre.\n"
            f"    Check the VERIFY step in _reasoning.",
            stacklevel=3,
        )


# ── Validation ────────────────────────────────────────────────────────────────

def validate_plan(plan: Dict[str, Any]) -> None:
    """
    Validate plan dict. Raises ValueError on hard violations.
    Emits warnings for soft violations and rotation mismatches.
    """
    if not isinstance(plan, dict):
        raise ValueError(f"Plan must be a dict, got {type(plan).__name__}.")
    if "steps" not in plan or not isinstance(plan["steps"], list):
        raise ValueError("Plan is missing a 'steps' list.")
    if not plan["steps"]:
        raise ValueError("Plan 'steps' list is empty.")

    if not str(plan.get("_reasoning", "")).strip():
        warnings.warn(
            "Plan has no '_reasoning' field — spatial decomposition skipped.",
            stacklevel=2,
        )

    n = len(plan["steps"])
    if n > MAX_PLAN_STEPS:
        warnings.warn(
            f"Plan has {n} steps (recommended ≤ {MAX_PLAN_STEPS}).",
            stacklevel=2,
        )

    for i, step in enumerate(plan["steps"]):
        if not isinstance(step, dict):
            raise ValueError(
                f"Step {i}: expected dict, got {type(step).__name__}."
            )
        action = str(step.get("action", "")).lower()
        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Step {i}: unknown action '{action}'. "
                f"Allowed: {sorted(VALID_ACTIONS)}."
            )
        seconds = step.get("seconds")
        if action in {"connect", "stop"} and seconds is not None:
            raise ValueError(
                f"Step {i}: '{action}' must not have a 'seconds' field."
            )
        if action in {"forward", "backward", "left", "right"} and seconds is not None:
            try:
                s = float(seconds)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Step {i}: 'seconds' must be a number, got {seconds!r}."
                )
            if s <= 0:
                raise ValueError(f"Step {i}: 'seconds' must be > 0, got {s}.")
            if s > MAX_STEP_SECONDS:
                raise ValueError(
                    f"Step {i}: {s}s exceeds the {MAX_STEP_SECONDS}s "
                    "safety cap. Split into shorter steps."
                )

    last = str(plan["steps"][-1].get("action", "")).lower()
    if last != "stop":
        raise ValueError(f"Last step must be 'stop', got '{last}'.")

    # Rotation sanity — warning only
    _check_rotation(plan)


# ── Executors ─────────────────────────────────────────────────────────────────

def execute_step(step: Dict[str, Any]) -> StepResult:
    """Execute one plan step. Returns StepResult; never raises."""
    action  = str(step.get("action", "")).lower()
    raw_sec = step.get("seconds")

    if action in {"forward", "backward", "left", "right"}:
        try:
            seconds = min(float(raw_sec), MAX_STEP_SECONDS) if raw_sec is not None else 2.0
        except (TypeError, ValueError):
            seconds = 2.0
    else:
        seconds = None

    dispatch = {
        "connect":  deepracer_connect,
        "forward":  lambda: deepracer_move_forward(seconds=seconds),
        "backward": lambda: deepracer_move_backward(seconds=seconds),
        "left":     lambda: deepracer_turn_left(seconds=seconds),
        "right":    lambda: deepracer_turn_right(seconds=seconds),
        "stop":     deepracer_stop,
    }

    fn = dispatch.get(action)
    if fn is None:
        return StepResult(
            step=step, ok=False,
            message=f"Unknown action '{action}' — skipped."
        )

    try:
        msg = fn()
        ok  = not is_error(str(msg))
        return StepResult(step=step, ok=ok, message=str(msg))
    except Exception as exc:
        return StepResult(
            step=step, ok=False,
            message=f"Exception in '{action}': {exc}"
        )


def execute_plan(
    plan: Dict[str, Any],
    stop_on_failure: bool = True,
) -> List[Tuple[Dict[str, Any], str]]:
    """Execute all steps. Returns List[Tuple[step_dict, result_str]].
    Preserves the original return type so main.py unpacks (step, result).
    """
    steps:  List[Dict[str, Any]]           = plan.get("steps", [])
    output: List[Tuple[Dict[str, Any], str]] = []

    for step in steps:
        sr = execute_step(step)
        output.append((sr.step, sr.message))
        if not sr.ok and stop_on_failure:
            emergency = execute_step({"action": "stop"})
            output.append((emergency.step, f"[emergency] {emergency.message}"))
            break

    return output


def execute_plan_full(
    plan: Dict[str, Any],
    stop_on_failure: bool = True,
) -> PlanResult:
    """Like execute_plan but returns the richer PlanResult dataclass."""
    result = PlanResult(
        pattern   = plan.get("pattern",    "unknown"),
        reasoning = plan.get("_reasoning", ""),
    )
    steps: List[Dict[str, Any]] = plan.get("steps", [])

    for step in steps:
        sr = execute_step(step)
        result.results.append(sr)
        if not sr.ok and stop_on_failure:
            emergency = execute_step({"action": "stop"})
            if not emergency.ok:
                result.results.append(emergency)
            result.aborted      = True
            result.abort_reason = f"Step '{step.get('action')}' failed: {sr.message}"
            break

    return result