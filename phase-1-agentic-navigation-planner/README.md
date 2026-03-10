# Phase 1: Agentic Navigation Planner

**PC (operator)** runs the agentic Planner; the plan is communicated to the DeepRacer and executed in one go. See the [project README](../README.md) for the full Phase 1 architecture and Phase 2/3 roadmap.

Natural-language navigation: the LLM (Nova) produces a **JSON plan** of steps; you confirm; the script runs the full sequence using the DeepRacer web API.

## Flow

1. You type a prompt (e.g. *"Move forward 2 seconds, turn left 1 second, then stop"*).
2. The planner agent returns a structured plan: `{ "steps": [ { "action": "forward", "seconds": 2 }, ... ] }`.
3. The plan is printed; you answer `y` to execute or `n` to cancel.
4. All steps run sequentially via `deepracer_tools` (connect, forward, backward, left, right, stop).

## Requirements

- Python 3.10+
- AWS DeepRacer on the same network, web UI reachable
- DeepRacer web console password
- AWS credentials with access to Amazon Bedrock (Nova)

## Setup

```bash
cd phase-1-agentic-navigation-planner
cp .env.example .env
# Edit .env: set DEEPRACER_IP, DEEPRACER_PASSWORD, and optionally MODEL, AWS_REGION
pip install -r requirements.txt
```

## Run

**Terminal (REPL):**

```bash
python main.py
```

**Web UI (plan + Execute / Cancel buttons, minimal output):**

```bash
python app_ui.py
```

Then open http://127.0.0.1:5000 in your browser. Enter a prompt, click **Get plan**, then **Execute** or **Cancel**.

### Demo

**PC Agent Planner (UI)** — Planner web UI: prompt → plan → Execute / Cancel.

![PC Agent Planner UI](demo/pc_agent_planner.gif)

**Execution**

*Move forward 2 seconds*

![Move forward 2 seconds](demo/move_2sec.gif)

*Move forward and backward 2 seconds*

![Move forward and backward 2 seconds](demo/move_fb_2sec.gif)

### Assets

For the branded UI, place the following files in `strands-agentic-deepracer/assets/`:

- `strands-logo.png`
- `deepracer-logo.png`
- `deepracer_bg.png`

At the terminal prompt try:

- **Connect to the car**
- **Move forward for 3 seconds**
- **Move forward 2 seconds, turn left 1 second, then stop**
- **Do a full circle** (planned as repeated same-direction turns until back to start)

## Tools (used by the executor)

| Tool                     | Description                          |
|--------------------------|--------------------------------------|
| `deepracer_connect`      | Show vehicle info / battery          |
| `deepracer_move_forward` | Move forward (seconds)               |
| `deepracer_move_backward`| Move backward (seconds)              |
| `deepracer_turn_left`    | Turn left while moving forward       |
| `deepracer_turn_right`   | Turn right while moving forward      |
| `deepracer_stop`         | Stop immediately                     |

Steering is aligned with forward direction (no reverse turns in this phase).

## Model

Default: **Nova Lite** (`us.amazon.nova-lite-v1:0`). Override with `MODEL` in `.env`.

## Safety

- Use in a safe, open area.
- Say **Stop** or cancel the plan if you need to halt.

## Author

Built by **Vivek Raja P S**  
GitHub: https://github.com/Vivek072  
LinkedIn: https://linkedin.com/in/meetvivekraja
