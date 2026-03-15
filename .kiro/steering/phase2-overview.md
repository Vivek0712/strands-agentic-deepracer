---
inclusion: always
---

# Phase 2: AgentTool Navigation Planner — Project Overview

## What This Is
A physics-aware, pattern-driven DeepRacer controller built on the Strands `AgentTool` architecture (modelled on strands-labs/robots). The user types a driving instruction; a Nova Lite planner produces a validated JSON plan with chain-of-thought reasoning; the user confirms; the plan executes with per-step pass/fail tracking and emergency stop on failure.

## Key Improvements Over Phase 1
- Physics constants baked into the prompt (rotation calibration: 1.5 s ≈ 90°)
- 15 named pattern library with pre-verified rotation math
- Mandatory `_reasoning` chain-of-thought (8 points) before any step is written
- `validate_plan()` — hard schema + safety cap + last-step-is-stop enforcement
- `stop_on_failure=True` — emergency stop sent on any hardware error
- `DeepRacerTool(AgentTool)` — 4-action interface: execute / start / status / stop
- `TaskStatus` state machine: IDLE → CONNECTING → PLANNING → RUNNING → COMPLETED/STOPPED/ERROR
- `ThreadPoolExecutor(max_workers=1)` + `threading.Event` for async task management
- Policy abstraction: `NovaPolicy`, `MockPolicy`, `ReplayPolicy`
- `--mock` flag for offline development (no Bedrock, no hardware)
- `reset_client()` for network recovery
- `is_error()` as single source of truth for error detection
- Fixed `finally` block bug from Phase 1 (success message was silently discarded)

## Key Files
| File | Purpose |
|---|---|
| `agent.py` | Planner prompt, policy abstraction, validation, StepResult/PlanResult, executors |
| `deepracer_tools.py` | Hardware interface — 6 @tool functions + physics constants + is_error() + reset_client() |
| `deepracer_agent_tool.py` | DeepRacerTool(AgentTool) — async task manager, 4-action interface |
| `main.py` | Terminal REPL — --mock/--model flags, patterns/physics commands |
| `app_ui.py` | Flask web UI with SSE streaming, /plan /execute /stop /stream routes |
| `templates/index.html` | Dashboard with quick prompts, pattern list, SSE step log |

## Architecture
```
User prompt
    │
    ▼
NavigationPolicy.plan()
  ├─ NovaPolicy   → Strands Agent (Nova Lite, tools=[], JSON+reasoning output)
  ├─ MockPolicy   → fixed canned plan (no Bedrock)
  └─ ReplayPolicy → named saved manoeuvre
    │
    ▼
validate_plan() → schema · safety caps · last-step-is-stop · rotation warning
    │
    ▼
User confirms (CLI y/N  or  Web Execute button)
    │
    ▼
execute_plan() / execute_plan_full()
  └─ execute_step() per step → deepracer_tools (@tool functions)
  └─ stop_on_failure=True → emergency deepracer_stop() on any error
    │
    ▼
aws-deepracer-control-v2 HTTP API → DeepRacer car

── OR via AgentTool ──

DeepRacerTool(AgentTool)
  action=execute → _sync_wrapper → _execute_task_async
  action=start   → ThreadPoolExecutor (non-blocking)
  action=status  → DeepRacerTaskState poll
  action=stop    → TaskStatus.STOPPED + deepracer_stop()
```

## Environment Variables (.env)
| Variable | Default | Purpose |
|---|---|---|
| MODEL | us.amazon.nova-lite-v1:0 | Bedrock model ID |
| DEEPRACER_IP | 192.168.0.3 | Car IP on local network |
| DEEPRACER_PASSWORD | (required) | DeepRacer web console password |
| AWS_REGION | us-east-1 | Bedrock region |
| DEEPRACER_MAX_STEP_SECS | 5.0 | Hard cap per step (clamp + reject) |
| DEEPRACER_FWD_THROTTLE | 0.30 | Forward/backward speed |
| DEEPRACER_TURN_THROTTLE | 0.20 | Turn speed (must stay < 1.5 m/s) |
| DEEPRACER_MAX_SPEED | 1.0 | Speed ceiling |
| DEEPRACER_STEER_ANGLE | 0.50 | Steering magnitude (half-lock = 0.35 m arc radius) |

## Rotation Calibration (do not change without re-measuring)
```
1.5 s ≈ 90°   →   duration = (angle / 90) × 1.5
```
| Angle | Duration |
|---|---|
| 60° | 1.0 s |
| 72° | 1.2 s |
| 90° | 1.5 s |
| 120° | 2.0 s |
| 180° | 3.0 s |
| 360° | 6.0 s (split into ≤5 s steps) |

## Running
```bash
python main.py                          # live Nova Lite
python main.py --mock                   # offline, no Bedrock/hardware
python main.py --model us.amazon.nova-pro-v1:0

python app_ui.py                        # web UI at http://127.0.0.1:5000
```
