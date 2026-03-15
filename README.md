<div align="center">

<img src="/assets/strands-logo.png" alt="Strands" width="120" /> &nbsp; **×** &nbsp; <img src="/assets/deepracer-logo.png" alt="AWS DeepRacer" width="120" />

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
- `finally` block bug in `_move_for_duration` silently discarded every success message
- No way to stop a running plan without killing the process
- `execute_plan` continued running after a failed step
- No policy abstraction — testing required live Bedrock calls and a physical car
- No web UI — terminal only

Phase 2 fixes all of this and adds a full dashboard web UI. The terminal interface is unchanged — you still type, confirm, and watch the car move — but the underlying architecture is a proper Strands `AgentTool` system modelled on [strands-labs/robots](https://github.com/strands-labs/robots).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  main.py  (terminal REPL)                    app_ui.py  (Flask web UI)        │
│   --mock  ·  --model  ·  patterns            http://127.0.0.1:5000            │
│   physics  ·  help                           SSE live step streaming           │
└──────────────────────────┬───────────────────────────┬────────────────────────┘
                           │  user instruction         │  POST /plan  /execute
                           ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  agent.py                                                                     │
│                                                                               │
│  NavigationPolicy (abstract)                                                  │
│  ├─ NovaPolicy      → create_planner() → Strands Agent → LLM (Nova Lite)     │
│  ├─ MockPolicy      → returns fixed test plan (no Bedrock)                    │
│  └─ ReplayPolicy    → returns saved named manoeuvre (no Bedrock)              │
│                                                                               │
│  plan_navigation()   →  _strip_fences()  →  json.loads()                     │
│  validate_plan()     →  schema · safety caps · last-step-is-stop              │
│                      →  _check_rotation()  ← rotation mismatch warning        │
│                                                                               │
│  DEGREES_PER_SECOND = 60 °/s  ·  FULL_ROTATION_SECS = 6.0 s                 │
│                                                                               │
│  execute_step()      →  dispatch to deepracer_tools                           │
│  execute_plan()      →  List[Tuple[step, result]]   (main.py compatible)     │
│  execute_plan_full() →  PlanResult dataclass        (AgentTool compatible)   │
└───────────────────────────────────────────┬──────────────────────────────────┘
                                            │  (optional — agent-loop usage)
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  deepracer_agent_tool.py  —  DeepRacerTool(AgentTool)                        │
│                                                                               │
│  tool_spec: { action: execute | start | status | stop }                      │
│                                                                               │
│  DeepRacerTaskState  ──  TaskStatus enum                                      │
│  ├─ IDLE → CONNECTING → PLANNING → RUNNING → COMPLETED                       │
│  └─ STOPPED / ERROR  (+ emergency stop sent to hardware)                     │
│                                                                               │
│  ThreadPoolExecutor(max_workers=1)  — one plan runs at a time                │
│  threading.Event  — shutdown signal checked each step                        │
│  stream() AsyncGenerator  — Strands entry point                               │
└───────────────────────────────────────────┬──────────────────────────────────┘
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  deepracer_tools.py                                                           │
│                                                                               │
│  deepracer_connect()       deepracer_move_forward(seconds)                   │
│  deepracer_move_backward(seconds)                                             │
│  deepracer_turn_left(seconds)    deepracer_turn_right(seconds)                │
│  deepracer_stop()                                                             │
│                                                                               │
│  is_error(msg) → bool    reset_client()                                      │
│                                                                               │
│  STEER_ANGLE=0.50   → servo half-lock  → arc radius ≈ 0.35 m                │
│  TURN_THROTTLE=0.20 → ~0.25 m/s turn speed  (<< 1.5 m/s safe limit)        │
│  FWD_THROTTLE=0.30  → ~0.40 m/s forward speed                               │
└───────────────────────────────────────────┬──────────────────────────────────┘
                                            │  aws-deepracer-control-v2 HTTP API
                                            ▼
                                 AWS DeepRacer (device)
```

---

## File Guide

| File | Purpose |
|------|---------|
| `agent.py` | Planner prompt, policy abstraction, rotation validation, step + plan executors |
| `deepracer_tools.py` | Hardware interface — six `@tool` functions wrapping the DeepRacer web API |
| `deepracer_agent_tool.py` | `DeepRacerTool(AgentTool)` — async task manager, four-action interface |
| `main.py` | Terminal REPL — `--mock`, `--model`, plan display, confirmation, result output |
| `app_ui.py` | Flask web server — `/plan`, `/execute`, `/stop`, `/stream` (SSE) routes |
| `templates/index.html` | Dashboard UI — physics panel, quick prompts, pattern library, live results |
| `.env.example` | All environment variables with calibration warnings |
| `requirements.txt` | Python dependencies |

---

## Web UI

A full dashboard runs alongside the terminal REPL. Start it with:

```bash
python app_ui.py
# open http://127.0.0.1:5000
```

### Layout

Three-column dashboard:

```
┌────────────────┬──────────────────────────────────┬───────────────┐
│ Physics limits │                                  │ Pattern       │
│ Min radius     │  Instruction input               │ library       │
│ Max speed      │  [Get Plan]  [Execute] [Cancel]  │               │
│ Max step secs  │  [⏹ Stop]                        │ circle        │
│                │                                  │ u-turn        │
│ Calibration    │  Plan card                       │ figure-8      │
│ 1.5s → 90°Δ   │  pattern tag · step table        │ square        │
│ 3.0s → 180°Δ  │  action pills · duration         │ triangle      │
│ formula        │  Heading Δ column                │ ...           │
│                │                                  │               │
│ Quick prompts  │  Execution results card          │               │
│ drive a circle │  progress bar · live step rows   │               │
│ do a figure-8  │  ✓/✗ icons · summary banner     │               │
│ ...            │                                  │               │
└────────────────┴──────────────────────────────────┴───────────────┘
```

### Features

**Live step streaming via SSE** — execution results appear one row at a time as each step completes. The browser holds a persistent `EventSource` connection to `/stream`; the Flask backend pushes `step`, `done`, and `stopped` events via a thread-safe queue. No polling, no page refresh.

**Rotation validation warnings** — if `validate_plan()` emits a rotation mismatch warning (see [Rotation Bug and Validator](#rotation-bug-and-validator) below), it appears as an amber pill between the input and the plan table, visible before you click Execute.

**Emergency stop** — the `⏹ Stop` button POSTs to `/stop`, which sets `_stop_flag`, calls `deepracer_stop()` on the hardware directly, and pushes a `stopped` SSE event. The browser handles it identically to a natural plan completion: progress bar turns amber, summary banner appears, buttons reset.

**Heading Δ column** — the plan table and execution results both show the estimated car heading change alongside each turn step (e.g. `1.5s → 90°Δ`). This is the car's *nose rotation*, derived entirely from the calibration formula `(seconds / 1.5) × 90°`. It is explicitly labelled `Δ` and has a tooltip clarifying it is completely separate from `steering=+0.50`, which is a normalised servo command on a `-1.0 … +1.0` scale.

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

This means the Strands `Agent` can call `action="stop"` mid-conversation to abort a running plan naturally, through the agent loop, without any special-case handling.

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
    # Phase 3: observation = await asyncio.to_thread(camera.get_frame)
    #          if obstacle_detected(observation): replan and break
    sr = await asyncio.to_thread(execute_step, step)
    if not sr.ok:
        await asyncio.to_thread(deepracer_stop)
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

These constants are measured empirically at the default throttle and steering settings.

| Property | Value | Notes |
|----------|-------|-------|
| Minimum turning radius | 0.28 m | Full steering lock (`STEER_ANGLE = 1.0`) |
| Maximum safe corner speed | 1.5 m/s | Above this → skid / spin risk |
| Forward speed | ~0.40 m/s | At `FWD_THROTTLE = 0.30` |
| Turn speed | ~0.25 m/s | At `TURN_THROTTLE = 0.20` — safely below 1.5 m/s |
| Arc radius during turn | ~0.35 m | At `STEER_ANGLE = 0.50`, half-lock |

### Important: steering value vs heading change

`steering = +0.50` in the tool output is a **normalised servo command** on the range `-1.0 … +1.0`. It sets the physical angle of the front wheels. It has no unit of degrees in the navigational sense.

`90° Δ` shown in the UI is the **estimated car heading change** — the rotation of the car's nose — derived from the calibration formula `(seconds / 1.5) × 90°`. These are entirely separate quantities.

### Rotation calibration

The planner and validator both use one formula for all turn durations:

```
heading_change (°) = (turn_seconds / 1.5) × 90
turn_seconds       = (heading_change / 90) × 1.5
```

Module-level constants in `agent.py`:

```python
DEGREES_PER_SECOND = 90.0 / 1.5    # = 60 °/s
SECONDS_PER_DEGREE = 1.5  / 90.0   # = 0.01667 s/°
FULL_ROTATION_SECS = 6.0            # seconds for a complete 360°
```

| Angle | Duration | Use case |
|-------|----------|----------|
| 60° | 1.0 s | Hexagon corner |
| 72° | 1.2 s | Pentagon corner |
| 90° | 1.5 s | Square corner, circle quarter |
| 120° | 2.0 s | Triangle corner |
| 180° | 3.0 s | U-turn, oval end |
| 270° | 4.5 s | Split: 3.0 s + 1.5 s |
| 360° | 6.0 s | Full circle — split into steps ≤ 5.0 s |

### Tightest possible curve

The tightest circle requires full steering lock (`STEER_ANGLE = 1.0`, diameter ≈ 0.56 m). The current default of `STEER_ANGLE = 0.50` (half-lock, diameter ≈ 0.70 m) is used deliberately: it keeps the arc radius above the 0.28 m minimum, reduces tyre scrub, and maintains the validated 1.5 s ≈ 90° calibration constant. Changing `STEER_ANGLE` invalidates the calibration and requires re-measurement on the physical car.

### Stabilisation rule

After any left→right or right→left direction reversal the planner inserts `{"action":"forward","seconds":0.3}`. At 0.25 m/s, chassis flex and lateral momentum from a hard opposite-direction arc carry enough inertia to disturb the next arc if not settled first.

---

## Planner System Prompt Design

The system prompt in `agent.py` has four components working together.

### 1. Physics section

Hard limits the model must never violate. Explains *why* `TURN_THROTTLE` is low (to stay inside the 1.5 m/s corner-speed envelope) so the model does not try to change the throttle.

### 2. Rotation calibration table

Pre-computed lookup using `duration = (angle / 90) × 1.5`. Without this, the model hallucinates random durations. With it, any polygon is arithmetically solvable.

### 3. Named pattern library (15 patterns)

Exact step templates verified against the rotation formula. The model selects a pattern by name and fills in durations — it does not reinvent the structure each call. Each pattern entry in the prompt includes its rotation proof, e.g.:

```
── CIRCLE (tight, 360°) ──────────────────────────────────────
total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓

  4× {"action":"left","seconds":1.5}  +  stop

  ✗ WRONG (never use): 8× left(1.5) = 720° (TWO full rotations, not one)
```

### 4. Mandatory `_reasoning` field — 8-point chain-of-thought

The model must answer all eight points before writing a single step:

```
1. PATTERN  — which named pattern? sub-patterns for custom?
2. HEADING  — walk every step tracking heading in degrees
3. MATH     — duration = (angle/90)×1.5 s, shown for every corner
4. VERIFY   — total_turn_time = sum of ALL turn durations
               total_degrees  = total_turn_time × (90/1.5)
               complete loop  → must equal 360° (or abort and recalculate)
5. PHYSICS  — turn speed 0.25 m/s ≪ 1.5 m/s; anything risky?
6. STAB     — list every left↔right reversal; confirm fwd(0.3) inserted
7. COUNT    — total steps; > 20 → simplify
8. SAFETY   — any step > 5.0 s? split it; last step is stop?
```

Point 4 (VERIFY) is the key addition over earlier versions — it requires the model to explicitly compute the total rotation before committing to the step list.

---

## Rotation Bug and Validator

### The bug that was found

The original circle pattern in the prompt was `8× left(1.5) + stop`. Running it through the calibration formula:

```
total_turn_time = 8 × 1.5 = 12.0 s
total_degrees   = 12.0 × (90 / 1.5) = 720°
```

The car would have spun **twice** before stopping. The same error was in the large-diameter circle template (`8× [fwd + left(1.5)]` = 720°).

The model was also observed producing `8× right(0.3)` for a "tight circle" request, reasoning correctly about step count but not about total rotation:

```
8 × 0.3 s = 2.4 s → (2.4 / 1.5) × 90° = 144°   (not 360°)
```

The car would have turned 144° — about two-fifths of a circle — and stopped.

### The fix

**In the prompt**: Corrected patterns with rotation proofs, explicit `✗ WRONG (never use)` annotations, and the mandatory VERIFY step in chain-of-thought.

```
── CIRCLE (tight, 360°) ──────────────────────────────────────
total_turn_time = 4 × 1.5 = 6.0 s → 360°. ✓
  4× {"action":"left","seconds":1.5}  +  stop       ← correct: 5 steps total

── CIRCLE (large, option B — 8 segments) ─────────────────────
per-turn angle = 360° / 8 = 45° → duration = (45/90)×1.5 = 0.75 s
total_turn_time = 8 × 0.75 = 6.0 s → 360°. ✓
  8× [forward(F) + left(0.75)]  +  stop
```

**In Python**: `_check_rotation()` in `agent.py` replicates the VERIFY check at runtime. After `validate_plan()` passes the schema checks, it computes the total turn time, converts to degrees, and emits `warnings.warn` if the total deviates from 360° (or 720° for figure-8) by more than 5°:

```python
def _check_rotation(plan: Dict[str, Any]) -> None:
    total_turn_secs = sum(
        float(s.get("seconds", 0.0))
        for s in steps
        if str(s.get("action", "")).lower() in {"left", "right"}
    )
    total_degrees = total_turn_secs * DEGREES_PER_SECOND   # × 60 °/s

    if abs(total_turn_secs - FULL_ROTATION_SECS) > tolerance:
        warnings.warn(
            f"Rotation mismatch — pattern '{pattern}':\n"
            f"  total turn time : {total_turn_secs:.2f}s → {total_degrees:.0f}°\n"
            f"  expected        : {FULL_ROTATION_SECS:.1f}s → 360°"
        )
```

This warning surfaces in the web UI as an amber pill before execution, and in the terminal REPL as a Python warning printed to stderr.

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

| Pattern | Steps | Turn math | Description |
|---------|-------|-----------|-------------|
| `circle` (tight) | **5** | 4× 1.5 s = 6.0 s → 360° | 4 quarter-turns + stop |
| `circle` (large A) | **9** | 4× 1.5 s = 6.0 s → 360° | 4× [fwd + 90° turn] |
| `circle` (large B) | **17** | 8× 0.75 s = 6.0 s → 360° | 8× [fwd + 45° turn], rounder path |
| `figure-8` | 19 | 8× 1.5 s = 12.0 s → 720° | Left circle + stabilise + right circle |
| `square` | 9 | 4× 1.5 s = 6.0 s → 360° | 4× (forward + 90° turn) |
| `triangle` | 7 | 3× 2.0 s = 6.0 s → 360° | 3× (forward + 120° turn) |
| `pentagon` | 11 | 5× 1.2 s = 6.0 s → 360° | 5× (forward + 72° turn) |
| `hexagon` | 13 | 6× 1.0 s = 6.0 s → 360° | 6× (forward + 60° turn) |
| `oval` | 5 | 2× 3.0 s = 6.0 s → 360° | Straights + 180° semicircular ends |
| `slalom (N)` | 1+6N+1 | left 90° + right 90° per gate → net 0° | Weave through N cones |
| `chicane` | 6 | left 60° + right 60° → net 0° | Single S-bend avoidance |
| `lane-change` | 6 | 60° + 60° → net 0° | Smooth lateral offset |
| `spiral-out` | 17 | 2 rings × 4× 1.5 s → 360° per ring | Expanding-radius loops (2 rings, 20-step cap) |
| `zigzag` | variable | 90° + 90° per cycle → net 0° | Sharp alternating turns |
| `parallel-park` | 9 | Partial turns, net ≈ 0° | 3-phase parking sequence |
| `figure-forward` | 7 | 4× 1.5 s = 6.0 s → 360° | Sprint + 360° loop + return |
| `u-turn` | 5 | 2× 1.5 s = 3.0 s → 180° | Reverse heading and continue |

---

## Setup

```bash
cd phase-2-agentool-navigation-planner
cp .env.example .env
```

Edit `.env` — minimum required:

```env
DEEPRACER_IP=192.168.0.3
DEEPRACER_PASSWORD=your_password_here
AWS_REGION=us-east-1
```

Optional overrides (defaults are calibrated values — see calibration warning below):

```env
MODEL=us.amazon.nova-lite-v1:0
DEEPRACER_FWD_THROTTLE=0.30
DEEPRACER_TURN_THROTTLE=0.20
DEEPRACER_MAX_SPEED=1.0
DEEPRACER_STEER_ANGLE=0.50
DEEPRACER_MAX_STEP_SECS=5.0
```

> **Calibration warning**: `DEEPRACER_STEER_ANGLE` and `DEEPRACER_TURN_THROTTLE` are the two variables that, if changed, silently break all navigation patterns. The `1.5 s ≈ 90°` constant in the planner prompt and `DEGREES_PER_SECOND` in `agent.py` were measured at their default values. If you tune these, re-measure on the physical car and update both.

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run

### Terminal REPL

```bash
python main.py                              # live Nova Lite
python main.py --mock                       # offline, no Bedrock / no hardware
python main.py --model us.amazon.nova-pro-v1:0   # override model
```

### Web UI

```bash
python app_ui.py
# open http://127.0.0.1:5000
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
| `physics` | Vehicle limits + rotation calibration table |
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

| Tool | Default | Physics |
|------|---------|---------|
| `deepracer_connect()` | — | Checks IP, password, battery |
| `deepracer_move_forward(seconds)` | 2.0 s | ~0.40 m/s straight |
| `deepracer_move_backward(seconds)` | 2.0 s | ~0.40 m/s reverse |
| `deepracer_turn_left(seconds)` | 1.5 s | ~0.25 m/s, 1.5 s ≈ 90° heading Δ |
| `deepracer_turn_right(seconds)` | 1.5 s | ~0.25 m/s, 1.5 s ≈ 90° heading Δ |
| `deepracer_stop()` | — | Immediate throttle cut |

Helper functions (not `@tool`, used internally):

| Function | Purpose |
|----------|---------|
| `is_error(message)` | Single source of truth for classifying tool result strings as failures |
| `reset_client()` | Force a fresh HTTP connection on the next call — use after network drops |

---

## What Phase 3 Builds On

Phase 2 deliberately exposes the seam for Phase 3 camera feedback. In `_execute_task_async`, the observation hook goes here:

```python
for step in steps:
    # Phase 3 slot:
    # observation = await asyncio.to_thread(camera.get_frame)
    # if obstacle_detected(observation):
    #     revised_plan = await asyncio.to_thread(policy.plan, f"obstacle ahead, {instruction}")
    #     break and restart with revised_plan

    sr = await asyncio.to_thread(execute_step, step)
    ...
```

The `NavigationPolicy.plan()` interface supports mid-execution replanning: a future `CameraPolicy` can accept the current camera observation alongside the original instruction and return a revised plan at any step boundary — without changing any other part of the system.

---

## Safety

- Run in a clear, open area with no obstacles in the planned path.
- The `DEEPRACER_MAX_STEP_SECS=5.0` cap prevents runaway movement from malformed LLM output — `execute_step()` clamps durations to this value even if validation is bypassed.
- `stop_on_failure=True` (default) sends an emergency stop on any hardware error — the car halts before the next step runs.
- Every plan is validated for `stop` as the final step before execution begins — a plan without a terminal stop is rejected with `ValueError`.
- Use `--mock` when developing or testing plans indoors.

---

## Author

**Vivek Raja P S**

[![GitHub](https://img.shields.io/badge/GitHub-Vivek072-181717?style=flat&logo=github)](https://github.com/Vivek072)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-meetvivekraja-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/meetvivekraja)
