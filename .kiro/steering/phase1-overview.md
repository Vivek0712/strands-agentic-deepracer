---
inclusion: always
---

# Phase 1: Agentic Navigation Planner — Project Overview

## What This Is
A natural-language DeepRacer controller. The user types a driving instruction; a Strands Agent backed by Amazon Bedrock Nova Lite produces a structured JSON plan; the user confirms; the plan executes step-by-step via the DeepRacer HTTP API.

## Key Files
- `agent.py` — planner agent creation, plan_navigation(), execute_plan(), execute_step()
- `deepracer_tools.py` — @tool-decorated functions that call aws-deepracer-control-v2
- `main.py` — terminal REPL entrypoint
- `app_ui.py` — Flask web UI (port 5000)
- `templates/index.html` — single-page UI with chat bubbles, plan panel, execute/cancel

## Architecture
```
User prompt
    │
    ▼
create_planner() → Strands Agent (Nova Lite, no tools, JSON-only output)
    │
    ▼
plan_navigation() → { "steps": [ { "action": "...", "seconds": ... }, ... ] }
    │
    ▼
User confirms (CLI y/N  or  Web Execute/Cancel)
    │
    ▼
execute_plan() → execute_step() per step → deepracer_tools (@tool functions)
    │
    ▼
aws-deepracer-control-v2 HTTP API → DeepRacer car
```

## Environment Variables (.env)
| Variable | Default | Purpose |
|---|---|---|
| MODEL | us.amazon.nova-lite-v1:0 | Bedrock model ID |
| DEEPRACER_IP | 192.168.0.3 | Car IP on local network |
| DEEPRACER_PASSWORD | (required) | DeepRacer web console password |
| DEEPRACER_FWD_THROTTLE | 0.3 | Forward speed |
| DEEPRACER_TURN_THROTTLE | 0.2 | Turn speed |
| DEEPRACER_MAX_SPEED | 1.0 | Speed cap |
| DEEPRACER_STEER_ANGLE | 0.5 | Steering angle for turns |
| AWS_REGION | us-east-1 | Bedrock region |

## Available Actions
`connect`, `forward`, `backward`, `left`, `right`, `stop`

## Running
```bash
# Terminal REPL
python main.py

# Web UI
python app_ui.py   # then open http://127.0.0.1:5000
```

## Dependencies
strands-agents, strands-tools, python-dotenv, aws-deepracer-control-v2, flask
