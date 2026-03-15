#!/usr/bin/env python3
"""
main.py — Terminal REPL for the Agentic Navigation Planner (Phase 2 + 3).

Run:
    python main.py                        # Phase 2: LLM planner only
    python main.py --vision               # Phase 3: LLM planner + Nova Pro vision
    python main.py --mock                 # Offline testing (no Bedrock / no hardware)
    python main.py --model <id>           # Override planner model
    python main.py --vision --model <id>  # Phase 3 with custom planner model

Phase 3 vision mode:
    --vision starts the DeepRacer camera stream and enables Nova Pro frame
    assessment between each plan step. Vision decisions (continue / replan /
    abort) are printed in real time as the plan executes.
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

from agent import (
    DEFAULT_MODEL,
    MAX_PLAN_STEPS,
    MAX_REPLANS,
    MAX_STEP_SECONDS,
    VISION_ASSESS_TIMEOUT,
    VISION_MIN_STEP_SECS,
    create_planner,
    create_policy,
    execute_plan,
    plan_navigation,
    validate_plan,
)

load_dotenv(Path(__file__).resolve().parent / ".env")
MODEL = os.getenv("MODEL", DEFAULT_MODEL)

W   = 56
HR  = "─" * W
HR2 = "═" * W


# ── Display helpers ────────────────────────────────────────────────────────────

def print_welcome(model: str, mock: bool, vision: bool) -> None:
    print()
    print(HR2)
    phase = "Phase 3 — Vision + Navigation Planner" if vision else "Phase 2 — Navigation Planner"
    print(f"  DeepRacer  {phase}")
    print(HR2)
    print()
    if vision:
        print("  Vision mode ACTIVE — Nova Pro monitors each step.")
        print("  Actions per step: continue / replan / abort")
        print()
    print("  Quick examples:")
    examples = [
        "connect to the car",
        "drive a full circle",
        "do a figure-8",
        "slalom through 3 cones",
        "drive a square",
        "spiral outward",
        "U-turn and come back",
    ]
    for ex in examples:
        print(f"    {ex}")
    print()
    print(f"  Planner : {'[MOCK]' if mock else model}")
    if vision:
        print(f"  Vision  : {os.getenv('VISION_MODEL','us.amazon.nova-pro-v1:0')}")
        print(f"  Timeout : {VISION_ASSESS_TIMEOUT}s per check  ·  Max replans: {MAX_REPLANS}")
    print(f"  Limits  : {MAX_STEP_SECONDS}s max step  ·  {MAX_PLAN_STEPS} steps max")
    print()
    print("  Commands: help · patterns · physics · exit")
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
        "drive a square",
        "drive a triangle with 2-second sides",
        "do a figure-8",
        "slalom through 3 cones",
        "slalom through 5 cones, narrow gates",
        "spiral outward",
        "lane change to the right",
        "do a U-turn and come back",
        "parallel park",
        "drive an oval loop",
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
        ("circle",         "360° rotation  (tight: 4×1.5s / large: 4×[fwd+1.5s])"),
        ("u-turn",         "Reverse heading, 2×1.5s = 180°"),
        ("figure-8",       "Two opposite circles, 8×1.5s total = 720°"),
        ("square",         "4 sides, 4×1.5s = 360°"),
        ("triangle",       "3 sides, 3×2.0s = 360°"),
        ("pentagon",       "5 sides, 5×1.2s = 360°"),
        ("hexagon",        "6 sides, 6×1.0s = 360°"),
        ("oval",           "2×3.0s = 360° (two 180° semicircles)"),
        ("slalom",         "Weave N cones: N×(left+right)"),
        ("chicane",        "Single S-bend"),
        ("lane-change",    "Smooth lateral offset"),
        ("spiral-out",     "2 rings × 4 arcs = 720° heading total"),
        ("zigzag",         "Sharp alternating turns"),
        ("parallel-park",  "3-phase parking"),
        ("figure-forward", "Sprint + 360° loop + return"),
    ]
    for name, desc in rows:
        print(f"    {name:<18} {desc}")
    print(HR)
    print()


def print_physics() -> None:
    print()
    print(HR)
    print("  Vehicle physics")
    print(HR)
    print("  Min turning radius  : 0.28 m  (full lock)")
    print("  Max corner speed    : 1.5 m/s (above → skid risk)")
    print("  Forward speed       : ~0.40 m/s  (FWD_THROTTLE=0.30)")
    print("  Turn speed          : ~0.25 m/s  (TURN_THROTTLE=0.20)")
    print()
    print("  Rotation calibration:  duration = (angle/90) × 1.5 s")
    print("    90°  → 1.5 s    180° → 3.0 s    360° → 6.0 s (split)")
    print(f"  Max step: {MAX_STEP_SECONDS}s  ·  Max steps: {MAX_PLAN_STEPS}")
    print(HR)
    print()


def print_plan(plan: dict) -> None:
    print()
    print(HR)
    pattern   = plan.get("pattern",    "—")
    reasoning = plan.get("_reasoning", "").strip()
    steps     = plan.get("steps", [])

    print(f"  Pattern   : {pattern}")
    if reasoning:
        wrapped = textwrap.fill(
            reasoning, width=W + 4,
            initial_indent   ="  Reasoning : ",
            subsequent_indent="              ",
        )
        print(wrapped)

    print(f"  Steps ({len(steps)})  :")
    for idx, step in enumerate(steps, start=1):
        action  = step.get("action", "?")
        seconds = step.get("seconds")
        dur     = f"  {seconds}s" if seconds is not None else ""
        # Show rotation delta for turn steps
        deg = ""
        if action in ("left", "right") and seconds is not None:
            d = (float(seconds) / 1.5) * 90
            deg = f"  ({d:.0f}°Δ)"
        print(f"    {idx:>2}.  {action}{dur}{deg}")
    print(HR)
    print()


def print_results(results: list, vision_events: list = None) -> None:
    print()
    print(HR)
    print("  Execution")
    print(HR)

    ok_count = fail_count = 0
    for idx, (step, message) in enumerate(results, start=1):
        action  = step.get("action", "?")
        seconds = step.get("seconds")
        dur     = f" {seconds}s" if seconds is not None else ""
        emg     = "[emergency]" in message
        ok      = not (message.lower().startswith("error") or emg)
        icon    = "⚡" if emg else ("✓" if ok else "✗")
        if ok and not emg:
            ok_count += 1
        else:
            fail_count += 1
        print(f"  {icon}  Step {idx:>2}  {action}{dur}")
        print(f"         {message}")

    # Print vision events if any
    if vision_events:
        print()
        print(f"  Vision log ({len(vision_events)} checks):")
        for ve in vision_events:
            icon = {"continue": "·", "replan": "↺", "abort": "⚠"}
            flag = icon.get(ve.action, "?")
            print(
                f"    {flag}  step {ve.step_index}: {ve.action}"
                f"  ({ve.confidence:.0%})  {ve.reasoning}"
            )

    print()
    if fail_count == 0:
        print(f"  Complete — {ok_count} step(s).")
    else:
        print(f"  Aborted — {ok_count} ok · {fail_count} failed.")
    print(HR)
    print()


# ── REPL ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DeepRacer Agentic Navigation Planner"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="MockPolicy — no Bedrock / no hardware needed.",
    )
    parser.add_argument(
        "--vision", action="store_true",
        help="Enable Phase 3: Nova Pro vision assessment between steps.",
    )
    parser.add_argument(
        "--model", default=None,
        help=f"Override Bedrock planner model (default: {MODEL}).",
    )
    args = parser.parse_args()

    effective_model = args.model or MODEL
    vision_log      = []   # populated during execution for print_results

    # ── Build policy ───────────────────────────────────────────────────────────
    camera_policy = None   # kept for cleanup in finally

    if args.mock:
        policy = create_policy("mock")
    elif args.vision:
        # Phase 3: camera + vision
        try:
            from camera_policy import create_camera_policy
            print("\n  Starting camera stream…")
            camera_policy = create_camera_policy(model=effective_model)
            policy = camera_policy
            print("  Camera stream ready.")
        except Exception as exc:
            print(f"\n  Failed to start Phase 3 camera policy: {exc}")
            print("  Check DEEPRACER_IP, DEEPRACER_PASSWORD, and VISION_MODEL.")
            sys.exit(1)
    else:
        # Phase 2: LLM planning only
        try:
            policy = create_policy("nova", model=effective_model)
        except Exception as exc:
            print(f"\n  Failed to create planner: {exc}")
            print("  Check AWS credentials, MODEL env var, and Bedrock access.")
            sys.exit(1)

    print_welcome(effective_model, mock=args.mock, vision=args.vision)

    # ── REPL loop ──────────────────────────────────────────────────────────────
    try:
        while True:
            try:
                user_input = input("DeepRacer > ").strip()
            except KeyboardInterrupt:
                print("\n  (KeyboardInterrupt — type 'exit' to quit)")
                continue
            except EOFError:
                print("\n  Exiting.")
                break

            if not user_input:
                continue

            lower = user_input.lower()

            if lower in {"exit", "quit", "bye", "q"}:
                print("  Goodbye.")
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

            # ── Plan ───────────────────────────────────────────────────────────
            print("\n  Planning…")
            try:
                plan = policy.plan(user_input)
            except Exception as exc:
                print(f"\n  Planning failed: {exc}\n")
                continue

            try:
                validate_plan(plan)
            except ValueError as exc:
                print(f"\n  Validation failed: {exc}\n")
                continue

            steps = plan.get("steps", [])
            if not steps:
                print("  Plan has no steps.\n")
                continue

            print_plan(plan)

            # ── Confirm ─────────────────────────────────────────────────────────
            try:
                answer = input("  Execute? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue

            if answer not in ("y", "yes"):
                print("  Cancelled.\n")
                continue

            # ── Execute ─────────────────────────────────────────────────────────
            if args.vision:
                # Phase 3: use DeepRacerTool for vision-in-the-loop execution
                from deepracer_agent_tool import DeepRacerTool

                vision_log_ref = []

                def _callback(event: str, data: dict) -> None:
                    if event == "vision":
                        icon = {"continue": "·", "replan": "↺", "abort": "⚠"}.get(
                            data.get("action", ""), "?"
                        )
                        print(
                            f"\n  [Vision] {icon} step {data.get('step')}: "
                            f"{data.get('action')}  ({data.get('confidence', 0):.0%})  "
                            f"— {data.get('reasoning', '')}"
                        )
                    elif event == "replan":
                        print(
                            f"\n  [Vision] ↺ Replan #{data.get('count')}: "
                            f"'{data.get('instruction')}'  "
                            f"({data.get('new_steps')} steps)"
                        )
                    elif event == "vision_abort":
                        print(f"\n  [Vision] ABORT: {data.get('reasoning')}")
                    elif event == "step":
                        icon = "✓" if data.get("ok") else "✗"
                        action  = data.get("action", "?")
                        seconds = data.get("seconds")
                        dur     = f" {seconds}s" if seconds is not None else ""
                        print(f"  {icon}  Step {data.get('index'):>2}  {action}{dur}")
                        print(f"         {data.get('message', '')}")

                print("\n  Executing with vision monitoring…\n")
                tool = DeepRacerTool(
                    policy         = camera_policy,
                    tool_name      = "deepracer",
                    event_callback = _callback,
                )

                import asyncio
                asyncio.run(tool._execute_task_async(user_input))

                state = tool._task_state
                print()
                if state.status.value == "completed":
                    print(f"  Complete — {state.completed_steps} steps  "
                          f"replans={state.replan_count}  "
                          f"vision_checks={len(state.vision_log)}")
                else:
                    print(f"  {state.status.value.upper()}  "
                          f"steps={state.completed_steps}  "
                          f"replans={state.replan_count}")
                    if state.result and state.result.abort_reason:
                        print(f"  Reason: {state.result.abort_reason}")
                print()

            else:
                # Phase 2: plain execution
                print("\n  Executing…\n")
                try:
                    results = execute_plan(plan)
                except Exception as exc:
                    print(f"\n  Execution error: {exc}\n")
                    continue
                print_results(results)

    finally:
        # Clean up camera stream on exit
        if camera_policy is not None:
            try:
                camera_policy.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    main()