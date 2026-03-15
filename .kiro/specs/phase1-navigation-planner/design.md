# Phase 1: Agentic Navigation Planner — Design

## System Architecture

```
User (CLI or Browser)
        │
        ▼
  [Confirmation Gate]
        │
   ┌────┴────┐
   │         │
main.py   app_ui.py (Flask :5000)
   │         │
   └────┬────┘
        │
        ▼
    agent.py
  ┌─────────────────────────────────────┐
  │  create_planner()                   │
  │    └─ strands.Agent(               │
  │         model=Nova Lite,            │
  │         tools=[],                   │
  │         system_prompt=PLANNER_PROMPT│
  │       )                             │
  │                                     │
  │  plan_navigation(planner, request)  │
  │    └─ planner(request) → raw str   │
  │    └─ strip markdown fences         │
  │    └─ json.loads() → plan dict      │
  │                                     │
  │  execute_plan(plan)                 │
  │    └─ for each step:                │
  │         execute_step(step)          │
  └─────────────────────────────────────┘
        │
        ▼
  deepracer_tools.py
  ┌─────────────────────────────────────┐
  │  @tool deepracer_connect()          │
  │  @tool deepracer_move_forward()     │
  │  @tool deepracer_move_backward()    │
  │  @tool deepracer_turn_left()        │
  │  @tool deepracer_turn_right()       │
  │  @tool deepracer_stop()             │
  │                                     │
  │  _get_client() → drctl.Client       │
  │  _ensure_motors_ready(client)       │
  │  _move_for_duration(s, t, sec, ms)  │
  └─────────────────────────────────────┘
        │
        ▼
  aws-deepracer-control-v2 HTTP API
        │
        ▼
  AWS DeepRacer (local network)
```

## Component Responsibilities

### agent.py
- Pure logic, no I/O
- `create_planner()` — builds the Strands Agent with the system prompt
- `plan_navigation()` — calls the agent, parses JSON, validates structure
- `execute_step()` — dispatches one step to the correct tool function
- `execute_plan()` — iterates all steps, collects results

### deepracer_tools.py
- All hardware interaction lives here
- Module-level singleton client via `_get_client()`
- `_move_for_duration()` is the single movement primitive
- All functions return strings (never raise to callers)

### main.py
- REPL loop with welcome, help, exit handling
- Calls `plan_navigation()` → prints plan → prompts `[y/N]` → calls `execute_plan()`
- Prints step-by-step results

### app_ui.py
- Flask app, stateless beyond planner singleton
- `/api/plan` — calls `plan_navigation()`, returns plan JSON
- `/api/execute` — calls `execute_plan()`, returns minimal summary (no raw tool output)
- Plan state lives in the browser between `/api/plan` and `/api/execute`

### templates/index.html
- Single-page app, vanilla JS (no framework)
- Two-column layout: chat panel (left) + plan panel (right)
- Chat bubbles for user prompt and agent plan summary
- Plan panel: numbered step list + Execute/Cancel buttons
- Result box: loading / success / error states

## Data Shapes

### Plan JSON
```json
{
  "steps": [
    { "action": "connect" },
    { "action": "forward", "seconds": 2.0 },
    { "action": "left",    "seconds": 1.0 },
    { "action": "stop" }
  ]
}
```

### Execute API Response
```json
{
  "ok": true,
  "results": [
    { "step": 1, "action": "connect",  "seconds": null, "ok": true },
    { "step": 2, "action": "forward",  "seconds": 2.0,  "ok": true },
    { "step": 3, "action": "left",     "seconds": 1.0,  "ok": true },
    { "step": 4, "action": "stop",     "seconds": null, "ok": true }
  ]
}
```

## Key Design Decisions

1. Planner has `tools=[]` — it only generates JSON, never calls tools directly. Execution is always explicit and user-confirmed.
2. Plan state is browser-side — the server never stores pending plans, keeping the Flask app stateless.
3. `_move_for_duration` centralises the stop-in-finally safety pattern — no movement code should bypass it.
4. Error strings (not exceptions) propagate from tools — this keeps `execute_plan` non-short-circuiting.
5. The planner singleton uses `hasattr` caching — avoids re-initialising the Bedrock client on every request.
