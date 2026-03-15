# Phase 2: AgentTool Navigation Planner — Design

## System Architecture

```
main.py / app_ui.py
        │
        ▼
NavigationPolicy.plan(instruction)
  ├─ NovaPolicy  → create_planner() → Agent(tools=[], system_prompt=PLANNER_PROMPT)
  │                → plan_navigation() → _strip_fences() → json.loads() → validate_plan()
  ├─ MockPolicy  → returns fixed dict
  └─ ReplayPolicy→ dict lookup by key
        │
        ▼
validate_plan(plan)
  ├─ Hard errors → ValueError
  ├─ Soft warnings → warnings.warn
  └─ _check_rotation() → warnings.warn on mismatch
        │
        ▼
execute_plan(plan, stop_on_failure=True)   ← main.py / app_ui.py
execute_plan_full(plan, stop_on_failure=True)  ← deepracer_agent_tool.py
        │
        ▼
execute_step(step) → StepResult
  └─ dispatch dict → deepracer_tools @tool functions
        │
        ▼
_move_for_duration(steering, throttle, seconds)
  └─ client.move() → time.sleep() → finally: stop_car() [stop_warning pattern]
        │
        ▼
aws-deepracer-control-v2 HTTP API → DeepRacer car

── AgentTool path ──────────────────────────────────────────────

DeepRacerTool(AgentTool)
  stream(tool_use) → dispatch action
    execute → _action_execute → _sync_wrapper → _execute_task_async
    start   → _action_start  → executor.submit(_sync_wrapper)
    status  → _action_status → DeepRacerTaskState snapshot
    stop    → _action_stop   → TaskStatus.STOPPED + deepracer_stop()
```

## Data Flow: Plan JSON

```json
{
  "_reasoning": "1.PATTERN:... 2.HEADING:... 3.MATH:... 4.VERIFY:... 5.PHYSICS:... 6.STAB:... 7.COUNT:... 8.SAFETY:...",
  "pattern": "square",
  "steps": [
    {"action": "forward",  "seconds": 2.0},
    {"action": "right",    "seconds": 1.5},
    {"action": "forward",  "seconds": 2.0},
    {"action": "right",    "seconds": 1.5},
    {"action": "forward",  "seconds": 2.0},
    {"action": "right",    "seconds": 1.5},
    {"action": "forward",  "seconds": 2.0},
    {"action": "right",    "seconds": 1.5},
    {"action": "stop"}
  ]
}
```

## StepResult / PlanResult

```python
@dataclass
class StepResult:
    step:    Dict[str, Any]
    ok:      bool
    message: str
    # display() → "  ✓ forward 2.0s  →  Moved: ..."

@dataclass
class PlanResult:
    results:      List[StepResult]
    aborted:      bool
    abort_reason: str
    pattern:      str
    reasoning:    str
    # all_ok → not aborted and all results ok
    # completed_steps → len(results)
```

## TaskStatus Transitions

```
IDLE
  │ _execute_task_async() called
  ▼
CONNECTING  → deepracer_connect() → is_error? → ERROR
  │
  ▼
PLANNING    → policy.plan() + validate_plan() → exception? → ERROR
  │
  ▼
RUNNING     → step loop
  │  step ok?  ──────────────────────────────────────────────────▶ COMPLETED
  │  step fail? → deepracer_stop() → aborted=True → break ──────▶ STOPPED
  │  shutdown_event set? → aborted=True → break ─────────────────▶ STOPPED
  │  _action_stop() called? → status=STOPPED → break ────────────▶ STOPPED
```

## SSE Event Flow (Web UI)

```
Browser                    Flask /execute thread           Flask /stream
   │                              │                              │
   │── POST /execute ────────────▶│                              │
   │◀─ {"ok": true} ─────────────│                              │
   │── GET /stream ──────────────────────────────────────────▶  │
   │                              │── push start event ─────────▶│── yield start
   │                              │── push step 1 ──────────────▶│── yield step
   │                              │── push step 2 ──────────────▶│── yield step
   │                              │── push done ────────────────▶│── yield done → break
   │◀─ SSE stream closed ─────────────────────────────────────── │
```

## Rotation Validation Design

```python
DEGREES_PER_SECOND = 90.0 / 1.5   # 60 °/s
FULL_ROTATION_SECS = 6.0           # 360° / 60 °/s

total_turn_secs = sum(s["seconds"] for s in steps if s["action"] in {"left","right"})
total_degrees   = total_turn_secs * DEGREES_PER_SECOND

# For circle/square/triangle/etc: expected = 360°
# For figure-8: expected = 720°
# Tolerance: 5° = 5 * SECONDS_PER_DEGREE = 0.083 s
```
