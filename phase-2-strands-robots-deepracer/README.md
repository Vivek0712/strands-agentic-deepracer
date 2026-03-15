<div align="center">

<img src="../assets/strands-logo.png" alt="Strands" width="120" /> &nbsp; **×** &nbsp; <img src="../assets/deepracer-logo.png" alt="AWS DeepRacer" width="120" />

# Phase 2 — AgentTool Navigation Planner

*Physics-aware, pattern-driven agentic navigation for AWS DeepRacer using Strands `AgentTool` architecture.*

[![Strands](https://img.shields.io/badge/Strands-AgentTool-0969da?style=flat)](https://strandsagents.com)
[![AWS DeepRacer](https://img.shields.io/badge/AWS-DeepRacer-FF9900?style=flat)](https://aws.amazon.com/deepracer/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)

</div>

---

## What Changed from Phase 1

Phase 1 was a working proof of concept: a Strands `Agent` called an LLM, got back a JSON list of steps, and executed them with bare `@tool` functions. It worked for simple prompts but had real limitations:

- The LLM had no rotation math — it guessed durations for "do a circle"
- No pattern vocabulary — figure-8 produced different (often wrong) plans every run
- `finally` block bug silently discarded every success message
- No way to stop a running plan without killing the process
- `execute_plan` continued running after a failed step
- No policy abstraction — testing required live Bedrock calls and a physical car

Phase 2 fixes all of this. The interface is identical — you still type, confirm, and watch the car move — but the underlying architecture is a proper Strands `AgentTool` system modelled on [strands-labs/robots](https://github.com/strands-labs/robots).

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│  main.py  (terminal REPL)                                                  │
│   --mock  │  --model  │  patterns  │  physics  │  help                    │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │  user instruction
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  agent.py                                                                  │
│                                                                            │
│  NavigationPolicy (abstract)                                               │
│  ├─ NovaPolicy      → create_planner() → Strands Agent → LLM (Nova Lite)  │
│  ├─ MockPolicy      → returns fixed test plan (no Bedrock)                 │
│  └─ ReplayPolicy    → returns saved named manoeuvre (no Bedrock)           │
│                                                                            │
│  plan_navigation()  →  _strip_fences()  →  json.loads()                   │
│  validate_plan()    →  schema · safety caps · last-step-is-stop rule       │
│                                                                            │
│  execute_step()     →  dispatch to deepracer_tools                        │
│  execute_plan()     →  List[Tuple[step, result]]  (main.py compatible)    │
│  execute_plan_full()→  PlanResult  (deepracer_agent_tool compatible)       │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   │  (optional — agent-loop usage)
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  deepracer_agent_tool.py  —  DeepRacerTool(AgentTool)                     │
│                                                                            │
│  tool_spec: { action: execute | start | status | stop }                   │
│                                                                            │
│  DeepRacerTaskState  ──  TaskStatus enum                                   │
│  ├─ IDLE → CONNECTING → PLANNING → RUNNING → COMPLETED                    │
│  └─ STOPPED / ERROR (+ emergency stop sent to hardware)                   │
│                                                                            │
│  ThreadPoolExecutor(max_workers=1)  — one plan runs at a time             │
│  threading.Event  — shutdown signal checked each step                     │
│  stream() AsyncGenerator  — Strands entry point                            │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  deepracer_tools.py                                                        │
│                                                                            │
│  deepracer_connect()       deepracer_move_forward(seconds)                │
│  deepracer_move_backward(seconds)                                          │
│  deepracer_turn_left(seconds)   deepracer_turn_right(seconds)              │
│  deepracer_stop()                                                          │
│                                                                            │
│  Physics:  FWD_THROTTLE=0.30 → ~0.40 m/s                                  │
│            TURN_THROTTLE=0.20 → ~0.25 m/s  (< 1.5 m/s safe limit)        │
│            STEER_ANGLE=0.50  → ~0.35 m arc radius (> 0.28 m minimum)     │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │  aws-deepracer-control-v2 HTTP API
                                   ▼
                        AWS DeepRacer (device)
```

---

## File Guide

| File | Purpose |
|------|---------|
| `agent.py` | Planner prompt, policy abstraction, validation, step + plan executors |
| `deepracer_tools.py` | Hardware interface — six `@tool` functions wrapping the DeepRacer web API |
| `deepracer_agent_tool.py` | `DeepRacerTool(AgentTool)` — async task manager, four-action interface |
| `main.py` | Terminal REPL — prompts, plan display, confirmation, result output |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |

---

## How the Strands Robots Architecture Is Applied

[strands-labs/robots](https://github.com/strands-labs/robots) defines a clean pattern for controlling any physical robot through a Strands Agent. Phase 2 applies this pattern to the DeepRacer, mapping every concept directly.

### 1. Robot as `AgentTool`

In strands-robots, `Robot` subclasses `AgentTool`. The tool exposes four actions through its `tool_spec`:

```python
"action": { "enum": ["execute", "start", "status", "stop"] }
```

Phase 2 does exactly the same in `DeepRacerTool`:

```python
class DeepRacerTool(AgentTool):
    @property
    def tool_spec(self) -> ToolSpec:
        return {
            "name": self._tool_name_str,
            "inputSchema": {
                "json": {
                    "properties": {
                        "action": { "enum": ["execute", "start", "status", "stop"] },
                        "instruction": { "type": "string" }
                    }
                }
            }
        }
```

This means the Strands `Agent` can call `action="stop"` mid-conversation to abort a running plan — naturally, through the agent loop, without any special-case handling.

### 2. `TaskStatus` state machine

strands-robots defines `TaskStatus` as an `Enum` (`IDLE / CONNECTING / RUNNING / COMPLETED / STOPPED / ERROR`). Phase 2 adds a `PLANNING` state between `CONNECTING` and `RUNNING` to distinguish "waiting for Bedrock" from "sending motor commands":

```
IDLE → CONNECTING → PLANNING → RUNNING → COMPLETED
                                      ↘ STOPPED (user abort)
                                      ↘ ERROR   (step failure)
```

### 3. `ThreadPoolExecutor(max_workers=1)` + `threading.Event`

strands-robots uses a single-worker executor so only one robot task runs at a time, and a `threading.Event` to signal shutdown across threads. Phase 2 copies this exactly:

```python
self._executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix=f"{tool_name}_executor",
)
self._shutdown_event = threading.Event()
```

The shutdown event is checked at the start of every step in the execution loop — if set, the loop breaks and an emergency stop is sent.

### 4. `_execute_task_async` / `_sync_wrapper` split

strands-robots separates async task logic (`_execute_task_async`) from the sync wrapper that handles running it in any context (`_execute_task_sync`). The sync wrapper detects whether it is already inside a running event loop and handles both cases:

```python
def _sync_wrapper(self, instruction: str) -> Dict[str, Any]:
    async def runner():
        await self._execute_task_async(instruction)
    try:
        asyncio.get_running_loop()           # already inside a loop?
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as ex:
            ex.submit(lambda: asyncio.run(runner())).result()
    except RuntimeError:
        asyncio.run(runner())                # no loop — create one
```

Phase 2 uses the same pattern verbatim.

### 5. Policy abstraction

strands-robots defines an abstract `Policy` class with `GR00TPolicy`, `MockPolicy`, and the hook for custom policies. Phase 2 defines `NavigationPolicy` with three implementations:

| strands-robots | Phase 2 |
|----------------|---------|
| `Gr00tPolicy` — live VLA model inference | `NovaPolicy` — live LLM via Bedrock |
| `MockPolicy` — returns random actions (testing) | `MockPolicy` — returns fixed plan (testing) |
| Custom subclass hook | `ReplayPolicy` — returns saved named manoeuvre |

The factory pattern is identical:

```python
# strands-robots
policy = create_policy("groot", data_config="so100_dualcam", port=8000)

# Phase 2
policy = create_policy("nova", model="us.amazon.nova-lite-v1:0")
policy = create_policy("mock")
policy = create_policy("replay", library={"figure-8": saved_plan})
```

### 6. Observation → action loop

strands-robots runs `get_observation() → get_actions() → send_action()` at 50 Hz inside the execution loop. Phase 2's equivalent is the step-execution loop in `_execute_task_async`:

```python
for step in steps:
    if self._task_state.status != TaskStatus.RUNNING:
        break                                    # user stopped
    if self._shutdown_event.is_set():
        break                                    # tool shutdown

    sr = await asyncio.to_thread(execute_step, step)   # send action
    if not sr.ok:
        await asyncio.to_thread(deepracer_stop)         # emergency stop
        break
```

The seam for Phase 3 camera feedback is exactly here — `get_observation()` slots in before each `execute_step()` call.

### 7. `cleanup()` / `__del__`

strands-robots always provides explicit `cleanup()` and `__del__` methods that stop any running task, shut down the executor, and disconnect hardware. Phase 2 does the same, additionally calling `reset_client()` to clear the cached DeepRacer HTTP connection:

```python
def cleanup(self) -> None:
    self._shutdown_event.set()
    if self._task_state.status in (RUNNING, PLANNING, CONNECTING):
        self._action_stop()
    self._executor.shutdown(wait=True, cancel_futures=True)
    reset_client()
```

---

## Vehicle Physics

These constants are measured empirically at the default throttle and steering settings. They are baked into the planner prompt so the LLM can do rotation arithmetic without guessing.

| Property | Value | Notes |
|----------|-------|-------|
| Minimum turning radius | 0.28 m | Full steering lock |
| Maximum safe corner speed | 1.5 m/s | Above this → skid / spin risk |
| Forward speed | ~0.40 m/s | At `FWD_THROTTLE = 0.30` |
| Turn speed | ~0.25 m/s | At `TURN_THROTTLE = 0.20` — safely below 1.5 m/s |
| Arc radius (during turn) | ~0.35 m | At `STEER_ANGLE = 0.50`, half-lock |

### Rotation calibration

The planner uses one formula for all turn durations:

```
duration (s) = (angle / 90) × 1.5
```

| Angle | Duration | Use case |
|-------|----------|----------|
| 60° | 1.0 s | Hexagon corner |
| 72° | 1.2 s | Pentagon corner |
| 90° | 1.5 s | Square corner, circle segment |
| 120° | 2.0 s | Triangle corner |
| 180° | 3.0 s | U-turn, oval end |
| 270° | 4.5 s | Three-quarter — split: 3.0 s + 1.5 s |
| 360° | 6.0 s | Full circle — split: 4× 1.5 s |

### Stabilisation rule

After any left→right or right→left direction reversal, the planner inserts `{"action":"forward","seconds":0.3}`. At 0.25 m/s, chassis flex and lateral momentum from a hard opposite-direction arc carry enough inertia to disturb the next arc if not settled first.

---

## Planner System Prompt Design

The system prompt in `agent.py` has four components that work together:

### 1. Physics section
Hard limits the model must never violate. Explains *why* `TURN_THROTTLE` is low (to stay inside the 1.5 m/s corner-speed envelope) so the model does not try to "fix" the throttle.

### 2. Rotation calibration table
Pre-computed lookup for the `duration = (angle / 90) × 1.5` formula. Without this, the model hallucinates random durations. With it, any polygon is arithmetically solvable.

### 3. Named pattern library (15 patterns)
Exact step templates for: `circle`, `u-turn`, `figure-8`, `square`, `triangle`, `pentagon`, `hexagon`, `oval`, `slalom`, `chicane`, `lane-change`, `spiral-out`, `zigzag`, `parallel-park`, `figure-forward`. The model selects a pattern by name and fills in durations — it does not reinvent the structure each call.

### 4. Mandatory `_reasoning` field (chain-of-thought)
The model must answer seven questions before writing a single step:

```
1. PATTERN  — which named pattern? sub-patterns for custom?
2. HEADING  — walk every step tracking car heading in degrees
3. MATH     — show turn-duration arithmetic for every corner
4. PHYSICS  — anything risking the 1.5 m/s corner-speed limit?
5. STAB     — list every left↔right reversal; confirm stab step inserted
6. COUNT    — total steps; > 20 → simplify
7. SAFETY   — any step > 5.0 s? split it; last step is stop?
```

This forces spatial reasoning before steps are committed — the same principle as chain-of-thought for math problems. The `_reasoning` field is stripped during validation and never sent to the car.

---

## Navigation Patterns

```
circle          figure-8        square          triangle
  ┌──┐           ┌─┐ ┌─┐       ┌────┐          ┌─────┐
  │  │           │ │×│ │       │    │           │     │
  └──┘           └─┘ └─┘       └────┘            └───┘

slalom          u-turn          spiral-out      lane-change
──●──●──●──     ──▶ ──┐         ┌──┐            ──┐
                      └──◀──    │┌┐│             └──▶──
                                └┘└┘
```

| Pattern | Steps | Description |
|---------|-------|-------------|
| `circle` | 9 | 8× left/right 1.5 s + stop |
| `figure-8` | 19 | Left circle + stabilise + right circle |
| `square` | 9 | 4× (forward + 90° turn) |
| `triangle` | 7 | 3× (forward + 120° turn) |
| `pentagon` | 11 | 5× (forward + 72° turn) |
| `hexagon` | 13 | 6× (forward + 60° turn) |
| `oval` | 5 | forward + 180° + forward + 180° |
| `slalom (N)` | 1+6N+1 | Weave through N cones |
| `chicane` | 6 | Single S-bend |
| `lane-change` | 6 | Smooth lateral offset |
| `spiral-out` | 17 | 3 rings of increasing radius |
| `zigzag` | variable | Sharp alternating turns |
| `parallel-park` | 9 | 3-phase parking sequence |
| `figure-forward` | 7 | Sprint + 360° loop + return |
| `u-turn` | 5 | Forward + 2× 90° + forward |

---

## Setup

```bash
cd phase-2-agentool-navigation-planner
cp .env.example .env
```

Edit `.env`:

```env
DEEPRACER_IP=192.168.0.3
DEEPRACER_PASSWORD=your_password_here

# Optional overrides
MODEL=us.amazon.nova-lite-v1:0
AWS_REGION=us-east-1
DEEPRACER_FWD_THROTTLE=0.30
DEEPRACER_TURN_THROTTLE=0.20
DEEPRACER_MAX_SPEED=1.0
DEEPRACER_STEER_ANGLE=0.50
DEEPRACER_MAX_STEP_SECS=5.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run

### Terminal REPL (primary interface)

```bash
python main.py
```

With offline mock (no Bedrock, no hardware):

```bash
python main.py --mock
```

Override model:

```bash
python main.py --model us.amazon.nova-pro-v1:0
```

### As a Strands Agent tool

```python
from agent import create_policy
from deepracer_agent_tool import DeepRacerTool
from strands import Agent

tool  = DeepRacerTool(policy=create_policy("nova"), tool_name="deepracer")
agent = Agent(tools=[tool])

# Blocking execution
agent("Drive a figure-8")

# Non-blocking with status polling
agent("Start a slalom through 4 cones")
agent("What is the status?")
agent("Stop the car")
```

---

## REPL Commands

| Input | Action |
|-------|--------|
| Any driving instruction | Plan → confirm → execute |
| `patterns` | List all 15 named patterns |
| `physics` | Show vehicle limits and rotation calibration |
| `help` / `?` | Example prompts |
| `exit` / `quit` | Exit |

### Example prompts

```
drive a full circle
do a figure-8
slalom through 4 cones
drive a square with 3-second sides
drive a triangle
spiral outward
lane change to the right
do a U-turn and come back
parallel park
drive an oval loop
connect to the car
move forward 3 seconds then stop
```

---

## Tools Reference

| Tool | Signature | Physics |
|------|-----------|---------|
| `deepracer_connect()` | → str | Checks IP, password, battery |
| `deepracer_move_forward(seconds)` | default 2.0 s | ~0.40 m/s |
| `deepracer_move_backward(seconds)` | default 2.0 s | ~0.40 m/s reverse |
| `deepracer_turn_left(seconds)` | default 1.5 s | ~0.25 m/s, 1.5 s ≈ 90° |
| `deepracer_turn_right(seconds)` | default 1.5 s | ~0.25 m/s, 1.5 s ≈ 90° |
| `deepracer_stop()` | → str | Immediate throttle cut |

All tools are safe to call independently. `deepracer_stop()` is also used as an emergency abort if any step fails during `execute_plan`.

---

## What Phase 3 Builds On

Phase 2 deliberately exposes the seam for Phase 3 camera feedback. In `_execute_task_async`, the observation hook goes here:

```python
for step in steps:
    # Phase 3: observation = await asyncio.to_thread(camera.get_frame)
    #          if obstacle_detected(observation): replan and break
    sr = await asyncio.to_thread(execute_step, step)
    ...
```

The `NavigationPolicy.plan()` interface also supports mid-execution replanning: a future `CameraPolicy` implementation can take the current observation alongside the original instruction and return a revised plan at any step boundary.

---

## Safety

- Run in a clear, open area with no obstacles in the planned path.
- The 5.0 s per-step cap prevents runaway movement from malformed LLM output.
- `stop_on_failure=True` (default) sends an emergency stop on any hardware error — the car halts before the next step runs.
- The `stop` action (last step of every plan) is validated before execution begins — a plan without a terminal stop is rejected.
- Use `--mock` when developing or testing plans indoors.

---

## Author

**Vivek Raja P S**

[![GitHub](https://img.shields.io/badge/GitHub-Vivek072-181717?style=flat&logo=github)](https://github.com/Vivek072)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-meetvivekraja-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/meetvivekraja)