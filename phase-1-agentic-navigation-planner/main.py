#!/usr/bin/env python3
"""
Phase 1: Terminal entrypoint for the Agentic Navigation Planner.

Run: python main.py

Handles REPL, welcome/help, user confirm, and printing plan/results.
Agent logic lives in agent.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from agent import (
    create_planner,
    plan_navigation,
    execute_plan,
    DEFAULT_MODEL,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL = os.getenv("MODEL", DEFAULT_MODEL)


def print_welcome() -> None:
    print("🏎️  Phase 1: Agentic Navigation Planner (DeepRacer)")
    print("=" * 52)
    print("For each prompt, the LLM creates a JSON plan; you confirm;")
    print("then the full sequence runs in one go.")
    print()
    print("Examples: Connect to the car | Move forward 2s, turn left 1s, stop")
    print("Type 'help' for more, 'exit' to quit.")
    print("=" * 52)
    print(f"Model: {MODEL}")


def print_help() -> None:
    print("\nExample prompts:")
    print("  - Connect to the car")
    print("  - Move forward for 3 seconds")
    print("  - Move backward 1.5 seconds and then stop")
    print("  - Go forward 2s, turn right 1s, then stop\n")


def main() -> None:
    print_welcome()
    try:
        planner = create_planner()
    except Exception as exc:
        print(f"\n❌ Failed to create planner agent: {exc}")
        print("Check AWS/Bedrock credentials, MODEL, and dependencies.")
        return

    while True:
        try:
            user_input = input("\n🏎️  > ").strip()
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
            continue

        if not user_input:
            continue

        lower = user_input.lower()
        if lower in {"exit", "quit", "bye"}:
            print("Exiting.")
            break
        if lower in {"help", "?"}:
            print_help()
            continue

        try:
            plan = plan_navigation(planner, user_input)
        except Exception as exc:
            print(f"\n❌ Failed to plan navigation: {exc}")
            continue

        steps = plan.get("steps", [])
        if not steps:
            print("Plan has no steps; nothing to execute.")
            continue

        print("\nPlanned steps:")
        for idx, step in enumerate(steps, start=1):
            action = step.get("action")
            seconds = step.get("seconds")
            if seconds is not None:
                print(f"  {idx}. {action} for {seconds} s")
            else:
                print(f"  {idx}. {action}")

        proceed = input("\nExecute this plan? [y/N]: ").strip().lower()
        if proceed not in ("y", "yes"):
            print("Plan execution cancelled.")
            continue

        print("\n🚗 Executing plan...")
        results = execute_plan(plan)
        for idx, (step, result) in enumerate(results, start=1):
            print(f"\nStep {idx}: {step.get('action')}")
            print(result)
        print("\n✅ Plan execution complete.")


if __name__ == "__main__":
    main()
