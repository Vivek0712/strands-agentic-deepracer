#!/usr/bin/env python3
"""
main.py — Terminal REPL for the Agentic Navigation Planner.

Run:
    python main.py              # live Nova Lite model
    python main.py --mock       # offline, no Bedrock / no hardware
    python main.py --model <id> # override Bedrock model ID

Flow per prompt:
    1. LLM creates a JSON plan with named pattern + reasoning.
    2. Plan is printed (pattern, reasoning, numbered steps).
    3. You confirm with y / n.
    4. Steps execute sequentially; pass/fail shown per step.

Imports from agent.py to match original project structure.
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

from agent import (
    create_planner,
    create_policy,
    plan_navigation,
    execute_plan,
    validate_plan,
    DEFAULT_MODEL,
    MAX_STEP_SECONDS,
    MAX_PLAN_STEPS,
)

load_dotenv(Path(__file__).resolve().parent / ".env")
MODEL = os.getenv("MODEL", DEFAULT_MODEL)

# ── Display constants ─────────────────────────────────────────────────────────
W  = 56
HR = "─" * W
HR2 = "═" * W


# ── Welcome / help / reference screens ───────────────────────────────────────

def print_welcome(model: str, mock: bool) -> None:
    print()
    print(HR2)
    print("  🏎️   Phase 1 — Agentic Navigation Planner (DeepRacer)")
    print(HR2)
    print("  Type a driving instruction → plan shown → you confirm.")
    print()
    print("  Quick examples:")
    examples = [
        "connect to the car",
        "move forward 3 seconds",
        "drive a full circle",
        "do a figure-8",
        "slalom through 4 cones",
        "drive a square with 3-second sides",
        "spiral outward",
        "parallel park",
        "U-turn and come back",
    ]
    for ex in examples:
        print(f"    {ex}")
    print()
    print(f"  Model  : {'[MOCK — no Bedrock / no hardware]' if mock else model}")
    print(f"  Limits : {MAX_STEP_SECONDS}s max per step  ·  {MAX_PLAN_STEPS} steps max")
    print()
    print("  Type  help · patterns · physics · exit")
    print(HR2)
    print()


def print_help() -> None:
    print()
    print(HR)
    print("  Navigation prompts")
    print(HR)
    prompts = [
        "connect to the car",
        "move forward for 3 seconds",
        "move backward 1.5 seconds then stop",
        "go forward 2s, turn right 1s, then stop",
        "drive a square",
        "drive a triangle with 2-second sides",
        "do a figure-8",
        "slalom through 3 cones",
        "slalom through 5 cones, narrow gates",
        "spiral outward",
        "lane change to the right",
        "do a U-turn and come back 2 seconds",
        "parallel park",
        "drive an oval / racetrack loop",
    ]
    for p in prompts:
        print(f"    {p}")
    print()
    print("  Commands:  patterns · physics · help · exit")
    print(HR)
    print()


def print_patterns() -> None:
    print()
    print(HR)
    print("  Named navigation patterns")
    print(HR)
    rows = [
        ("circle",         "360° rotation, tight or large-diameter"),
        ("u-turn",         "Reverse heading and continue"),
        ("figure-8",       "Two opposite circles at a crossing"),
        ("square",         "4 sides, 90° right-angle corners"),
        ("triangle",       "3 sides, 120° exterior corners"),
        ("pentagon",       "5 sides, 72° exterior corners"),
        ("hexagon",        "6 sides, 60° exterior corners"),
        ("oval",           "Long straights + 180° semicircular ends"),
        ("slalom",         "Weave through N cones (specify count)"),
        ("chicane",        "Single S-bend obstacle avoidance"),
        ("lane-change",    "Smooth lateral offset left or right"),
        ("spiral-out",     "Expanding-radius loops outward"),
        ("zigzag",         "Sharp alternating direction changes"),
        ("parallel-park",  "3-phase simplified parking sequence"),
        ("figure-forward", "Sprint + tight 360° loop + return"),
    ]
    for name, desc in rows:
        print(f"    {name:<18} {desc}")
    print(HR)
    print()


def print_physics() -> None:
    print()
    print(HR)
    print("  Vehicle physics limits")
    print(HR)
    print("  Minimum turning radius  : 0.28 m  (full steering lock)")
    print("  Max safe corner speed   : 1.5 m/s (above → skid / spin risk)")
    print("  Forward speed (approx)  : ~0.40 m/s  FWD_THROTTLE=0.30")
    print("  Turn speed (approx)     : ~0.25 m/s  TURN_THROTTLE=0.20")
    print()
    print("  Rotation calibration (empirical):")
    print("    1.5 s  ≈  90°   quarter-turn")
    print("    3.0 s  ≈ 180°   U-turn core")
    print("    4.5 s  ≈ 270°   split: 3.0 s + 1.5 s")
    print("    6.0 s  ≈ 360°   split: 4× 1.5 s  or  2× 3.0 s")
    print()
    print("  Angle → duration:  (angle / 90) × 1.5 s")
    print("    60° → 1.0 s    120° → 2.0 s    72° → 1.2 s")
    print()
    print(f"  Planner safety caps:")
    print(f"    Max step duration  : {MAX_STEP_SECONDS}s")
    print(f"    Max steps per plan : {MAX_PLAN_STEPS}")
    print(HR)
    print()


# ── Plan / result display ─────────────────────────────────────────────────────

def print_plan(plan: dict) -> None:
    """Print pattern, reasoning (wrapped), and numbered step table."""
    print()
    print(HR)

    pattern   = plan.get("pattern",    "—")
    reasoning = plan.get("_reasoning", "").strip()
    steps     = plan.get("steps", [])

    print(f"  Pattern   : {pattern}")

    if reasoning:
        indent    = "              "
        wrapped   = textwrap.fill(
            reasoning, width=W + 4,
            initial_indent="  Reasoning : ",
            subsequent_indent=indent,
        )
        print(wrapped)

    print(f"  Steps ({len(steps)})  :")
    for idx, step in enumerate(steps, start=1):
        action  = step.get("action", "?")
        seconds = step.get("seconds")
        dur     = f"  {seconds}s" if seconds is not None else ""
        print(f"    {idx:>2}.  {action}{dur}")

    print(HR)
    print()


def print_results(results: list) -> None:
    """Print per-step pass/fail with icons."""
    print()
    print(HR)
    print("  Execution results")
    print(HR)

    ok_count   = 0
    fail_count = 0

    for idx, (step, message) in enumerate(results, start=1):
        action  = step.get("action", "?")
        seconds = step.get("seconds")
        dur     = f" {seconds}s" if seconds is not None else ""

        emergency = "[emergency]" in message
        if emergency:
            icon = "⚡"
        elif message.lower().startswith("error") or "failed" in message.lower():
            icon = "✗"
            fail_count += 1
        else:
            icon = "✓"
            ok_count += 1

        print(f"  {icon}  Step {idx:>2}  {action}{dur}")
        print(f"         {message}")

    print()
    if fail_count == 0 and ok_count > 0:
        print(f"  ✅ Complete — {ok_count} step(s) ran successfully.")
    else:
        print(f"  ❌ Aborted — {ok_count} ok · {fail_count} failed.")

    print(HR)
    print()


# ── REPL ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DeepRacer Phase 1 — Agentic Navigation Planner REPL"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="MockPolicy — no Bedrock calls, no hardware needed.",
    )
    parser.add_argument(
        "--model", default=None,
        help=f"Override Bedrock model ID (default: {MODEL}).",
    )
    args = parser.parse_args()

    effective_model = args.model or MODEL

    # ── Build planner ─────────────────────────────────────────────────────────
    if args.mock:
        policy  = create_policy("mock")
        planner = None   # not used by MockPolicy
    else:
        try:
            planner = create_planner(effective_model)
            policy  = None   # main loop calls plan_navigation(planner, …) directly
        except Exception as exc:
            print(f"\n❌  Failed to create planner: {exc}")
            print("    Check AWS credentials, MODEL env var, and Bedrock access.")
            sys.exit(1)

    print_welcome(effective_model, mock=args.mock)

    # ── REPL loop ─────────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("🏎️  > ").strip()
        except KeyboardInterrupt:
            print("\n  (KeyboardInterrupt — type 'exit' to quit)")
            continue
        except EOFError:
            print("\n  Exiting.")
            break

        if not user_input:
            continue

        lower = user_input.lower()

        # ── Built-in commands ─────────────────────────────────────────────────
        if lower in {"exit", "quit", "bye", "q"}:
            print("  Goodbye. 🏎️")
            break
        if lower in {"help", "?", "h"}:
            print_help()
            continue
        if lower in {"patterns", "pattern", "list"}:
            print_patterns()
            continue
        if lower in {"physics", "limits", "specs"}:
            print_physics()
            continue

        # ── Plan ──────────────────────────────────────────────────────────────
        print("\n  ⏳ Planning…")
        try:
            if args.mock:
                plan = policy.plan(user_input)
            else:
                plan = plan_navigation(planner, user_input)
        except Exception as exc:
            print(f"\n  ❌ Planning failed: {exc}\n")
            continue

        # Validate (plan_navigation already calls this, but MockPolicy doesn't)
        try:
            validate_plan(plan)
        except ValueError as exc:
            print(f"\n  ❌ Plan validation failed: {exc}\n")
            continue

        steps = plan.get("steps", [])
        if not steps:
            print("  Plan has no steps; nothing to execute.\n")
            continue

        print_plan(plan)

        # ── Confirm ───────────────────────────────────────────────────────────
        try:
            proceed = input("  Execute this plan? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")
            continue

        if proceed not in ("y", "yes"):
            print("  Plan cancelled.\n")
            continue

        # ── Execute ───────────────────────────────────────────────────────────
        print("\n  🚗 Executing plan…\n")
        try:
            results = execute_plan(plan)
        except Exception as exc:
            print(f"\n  ❌ Unexpected execution error: {exc}\n")
            continue

        print_results(results)


if __name__ == "__main__":
    main()