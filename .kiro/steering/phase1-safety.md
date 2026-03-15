---
inclusion: always
---

# Phase 1 — Safety Rules (Non-Negotiable)

These rules apply to ALL code in phase-1-agentic-navigation-planner. Never weaken them.

## Physical Safety
- Always call `client.stop_car()` in a `finally` block after any `client.move()` call
- Default movement durations must be short (1.0–3.0 seconds max)
- Never generate a plan step with `seconds > 10.0` — clamp or reject
- The planner prompt must always include a conservative fallback to a single `"stop"` step for unsafe/unclear instructions

## Confirmation Gate
- CLI (`main.py`): user must type `y` or `yes` explicitly — any other input cancels
- Web UI (`app_ui.py`): plan must be displayed before the Execute button is clickable
- Never auto-execute a plan without user confirmation

## Error Propagation
- Tool functions return error strings — callers must check if result starts with `"Error"`
- A failed step must NOT prevent subsequent steps from running (non-short-circuit execution)
- Always surface errors to the user in both CLI and web UI

## No Reverse Turns
Steering is forward-only. There are no reverse-turn actions. `left` and `right` always combine with forward throttle.

## Credentials
- `DEEPRACER_PASSWORD` must never be hardcoded or logged
- `.env` is gitignored — never commit secrets
- Raise `RuntimeError` (not a silent failure) if `DEEPRACER_PASSWORD` is unset when a client is needed
