# Phase 1: Agentic Navigation Planner — Requirements

## Overview
A natural-language interface for controlling an AWS DeepRacer car. The user describes a driving sequence in plain English; an LLM agent converts it to a structured JSON plan; the user confirms; the plan executes step-by-step via the DeepRacer HTTP API.

## Requirements

### REQ-1: Natural Language Plan Generation
- The system MUST accept a free-text driving instruction from the user
- The system MUST send the instruction to a Strands Agent backed by Amazon Bedrock Nova Lite
- The agent MUST return a valid JSON object with a `"steps"` array
- Each step MUST have an `"action"` field; motion steps MUST have a `"seconds"` field
- The system MUST raise a `ValueError` if the response cannot be parsed as valid plan JSON

### REQ-2: Supported Actions
The planner MUST support exactly these action names:
- `connect` — verify connection and show vehicle info/battery
- `forward` — move forward for N seconds
- `backward` — move backward for N seconds
- `left` — turn left while moving forward for N seconds
- `right` — turn right while moving forward for N seconds
- `stop` — immediately halt the car (no `seconds` field)

### REQ-3: Plan Confirmation Gate
- CLI: the user MUST be shown the full plan and prompted `[y/N]` before execution
- Web UI: the plan panel MUST be visible with Execute/Cancel buttons before any movement
- Auto-execution without confirmation is NEVER permitted

### REQ-4: Sequential Plan Execution
- Steps MUST execute in order, one at a time
- A failed step MUST NOT abort remaining steps
- Each step result MUST be captured and returned to the caller

### REQ-5: DeepRacer Hardware Control
- The system MUST use `aws-deepracer-control-v2` to communicate with the car over HTTP
- The car client MUST be a module-level singleton (created once, reused)
- Every `client.move()` call MUST be followed by `client.stop_car()` in a `finally` block
- The system MUST call `set_manual_mode()` and `start_car()` before each movement

### REQ-6: Motion Tuning via Environment
- Forward throttle, turn throttle, max speed, and steer angle MUST be configurable via `.env`
- All motion parameters MUST have safe defaults if not set

### REQ-7: Terminal REPL Interface
- `main.py` MUST provide an interactive REPL loop
- MUST display a welcome message and example prompts on startup
- MUST support `help`, `exit`, `quit`, `bye` commands
- MUST handle `KeyboardInterrupt` gracefully without crashing

### REQ-8: Web UI Interface
- `app_ui.py` MUST serve a Flask app on port 5000
- MUST expose `GET /`, `POST /api/plan`, `POST /api/execute`
- The UI MUST show chat bubbles for user prompt and agent plan summary
- The UI MUST show a numbered step list in the plan panel
- Execute results MUST show success/error state visually

### REQ-9: Safety Constraints
- Default duration for unspecified motion steps MUST be 2.0 seconds
- The planner prompt MUST instruct the model to use 1.0–3.0 second durations
- Unsafe or unclear instructions MUST produce a conservative plan (single `stop` step)
- `DEEPRACER_PASSWORD` MUST never be logged or hardcoded

### REQ-10: Model Configuration
- Default model MUST be `us.amazon.nova-lite-v1:0`
- Model MUST be overridable via `MODEL` environment variable
- AWS region MUST be configurable via `AWS_REGION` (default `us-east-1`)
