<div align="center">

<img src="assets/strands-logo.png" alt="Strands" width="140" /> &nbsp; **×** &nbsp; <img src="assets/deepracer-logo.png" alt="AWS DeepRacer" width="140" />

# Strands Agentic DeepRacer

*Agentic navigation and control for AWS DeepRacer using [Strands Agents](https://strandsagents.com) and natural language.*

[![Strands](https://img.shields.io/badge/Strands-Agentic-0969da?style=flat)](https://strandsagents.com)
[![AWS DeepRacer](https://img.shields.io/badge/AWS-DeepRacer-FF9900?style=flat)](https://aws.amazon.com/deepracer/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Bedrock](https://img.shields.io/badge/Amazon-Bedrock-232F3E?style=flat&logo=amazon-aws)](https://aws.amazon.com/bedrock/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

<br/>

</div>

---

## What This Is

This project brings **agentic AI** to an AWS DeepRacer 1/18-scale autonomous car. Instead of writing control scripts, you describe what you want the car to do in plain English. An LLM (Amazon Nova via Bedrock) reasons about the request, decomposes it into a physics-aware sequence of movement steps, and executes the plan against the DeepRacer's web API.

The project is structured in three phases, each delegating more intelligence to the edge.

---

## Phase Overview

| Phase | Where the agent runs | What's new | Status |
|-------|---------------------|------------|--------|
| **Phase 1** | PC operator | LLM plans → human confirms → car executes | ✅ Complete |
| **Phase 2** | PC operator | `AgentTool` architecture · physics-aware planner · pattern library · async control | ✅ Complete |
| **Phase 3** | Car edge device | Edge-deployed LLM · camera perception · mid-execution replanning | 🗓 Planned |

---

## Phase 1: PC Operator — Agentic Planner

The first implementation. The LLM runs on the PC, produces a JSON plan from a natural-language prompt, the operator reviews and confirms, then the full sequence runs against the DeepRacer web API in one shot.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  PC (Operator)                                                        │
│                                                                       │
│   Natural language ──▶ LLM Planner ──▶ JSON plan                     │
│                         (Nova Lite)     [connect, fwd, left, …]       │
│                                                │                      │
│                         Operator confirms      ▼                      │
│                                         Plan executor                 │
│                                         (deepracer_tools)             │
└─────────────────────────────────────────────────────┼────────────────┘
                                                       │
                                         Web API (HTTP)
                                                       │
                                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  AWS DeepRacer (device)                                               │
│  Receives and runs the plan                                           │
└──────────────────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- Single-shot planning: plan once, confirm once, run once
- Simple `@tool` functions wrapping the DeepRacer HTTP API
- Basic step validation
- Terminal REPL + Flask web UI

📁 [`phase-1-agentic-navigation-planner/`](./phase-1-agentic-navigation-planner/)

---

## Phase 2: AgentTool Architecture — Physics-Aware Planner

A ground-up redesign that brings the system architecture in line with [Strands Robots](https://github.com/strands-labs/robots) and dramatically improves navigation capability. The interface stays the same (type, confirm, run) but everything underneath is rebuilt.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PC (Operator)                                                                │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Strands Agent                                                           │  │
│  │                                                                          │  │
│  │  Natural language ──▶  NavigationPolicy  ──▶  validate_plan()           │  │
│  │                        (Nova / Mock /         (schema + physics caps)    │  │
│  │                         Replay)                      │                   │  │
│  │                                                       ▼                  │  │
│  │                                            DeepRacerTool (AgentTool)     │  │
│  │                                            ┌──────────────────────────┐  │  │
│  │                                            │  execute / start /       │  │  │
│  │                                            │  status  / stop          │  │  │
│  │                                            │  TaskManager (async)     │  │  │
│  │                                            └────────────┬─────────────┘  │  │
│  └─────────────────────────────────────────────────────────┼────────────────┘  │
└────────────────────────────────────────────────────────────┼───────────────────┘
                                                             │
                                              Web API (HTTP)
                                                             │
                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  AWS DeepRacer (device)                                                       │
│  deepracer_tools: connect · forward · backward · left · right · stop          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key additions over Phase 1:**
- `DeepRacerTool` as a proper Strands `AgentTool` with `execute / start / status / stop` actions
- Physics-aware system prompt with rotation calibration, corner-speed limits, stabilisation rules
- Named pattern library: 15 manoeuvres (circle, figure-8, square, triangle, slalom, spiral, …)
- Mandatory chain-of-thought `_reasoning` field forces spatial decomposition before steps are committed
- Policy abstraction (`NovaPolicy`, `MockPolicy`, `ReplayPolicy`) — swap planners without touching the executor
- `StepResult` / `PlanResult` dataclasses replacing raw tuples
- `stop_on_failure` emergency abort — failed step halts the car immediately
- `--mock` flag for offline development and unit testing

📁 [`phase-2-agentool-navigation-planner/`](./phase-2-agentool-navigation-planner/)

---

## Phase 3: Edge LLM + Camera Navigation (Planned)

Moves the entire agentic system from the PC to the car's edge device. The PC sends only prompts; the edge LLM interprets, plans, and commands the car directly. Camera input enables perception-driven replanning mid-execution.

```
┌──────────────┐   prompt   ┌──────────────────────────────────────────┐
│  PC          │──────────▶│  Edge device (Jetson / DeepRacer compute) │
│  (command    │           │  ┌─────────────────────────────────────┐   │
│   source)    │           │  │  Edge LLM (small model)             │   │
└──────────────┘           │  │  AgentTool control loop             │   │
                           │  │  Camera perception                  │   │
                           │  │  Mid-execution replanning           │   │
                           │  └──────────────┬──────────────────────┘   │
                           │                 │ direct hardware API       │
                           │                 ▼                           │
                           │       AWS DeepRacer motors / servos         │
                           └──────────────────────────────────────────────┘
```

**Planned additions:**
- Edge-deployed LLM (small distilled model via Ollama or similar)
- Observation loop: camera frame → perception → action, closing the control loop at the edge
- Intermediate replanning: obstacle detected mid-plan → replan without returning to PC
- Reduced PC-to-car round-trip latency

---

## How Strands Robots Inspired Phase 2

Phase 2 architecture is directly and intentionally modelled on **[strands-labs/robots](https://github.com/strands-labs/robots)**, the physical-robot control library for Strands Agents. The table below maps each concept:

| strands-robots pattern | Phase 2 implementation |
|------------------------|------------------------|
| `Robot(AgentTool)` — robot as a first-class tool | `DeepRacerTool(AgentTool)` in `deepracer_agent_tool.py` |
| `execute / start / status / stop` action dispatch | Same four actions in `tool_spec` and `stream()` |
| `RobotTaskState` dataclass with `TaskStatus` enum | `DeepRacerTaskState` + `TaskStatus` |
| `ThreadPoolExecutor(max_workers=1)` single-worker | Identical executor for one-plan-at-a-time constraint |
| `_execute_task_async` / `_execute_task_sync` split | `_execute_task_async` + `_sync_wrapper` with same event-loop detection logic |
| `_shutdown_event = threading.Event()` | Identical — checked each step of the execution loop |
| `cleanup()` / `__del__` resource teardown | `cleanup()` calls `reset_client()` + executor shutdown |
| `Policy` abstraction (GR00T / Mock / Custom) | `NavigationPolicy` + `NovaPolicy` / `MockPolicy` / `ReplayPolicy` |
| `create_policy(provider, **kwargs)` factory | Same factory pattern in `agent.py` |
| `get_observation() → get_actions() → send_action()` loop | `execute_step()` loop with `stop_on_failure` abort |
| Non-blocking `start` + `status` poll for long tasks | `_action_start()` + `_action_status()` for multi-step plans |
| Structured result reporting | `StepResult` / `PlanResult` dataclasses |

The core insight borrowed from strands-robots: **a physical actuator (robot arm or RC car) should be a Strands `AgentTool` like any other tool**, with the same four lifecycle actions. This lets the Strands agent decide whether to run plans synchronously or asynchronously, poll progress, and abort — exactly as a human operator would.

---

## Repository Structure

```
strands-agentic-deepracer/
│
├── README.md                          ← this file
│
├── phase-1-agentic-navigation-planner/
│   ├── README.md
│   ├── agent.py                       ← planner + executor (Phase 1)
│   ├── deepracer_tools.py             ← @tool functions (Phase 1)
│   ├── main.py                        ← terminal REPL
│   ├── app_ui.py                      ← Flask web UI
│   ├── requirements.txt
│   └── .env.example
│
├── phase-2-agentool-navigation-planner/
│   ├── README.md
│   ├── agent.py                       ← planner, policy abstraction, executor
│   ├── deepracer_tools.py             ← @tool functions with physics notes
│   ├── deepracer_agent_tool.py        ← DeepRacerTool(AgentTool)
│   ├── main.py                        ← terminal REPL (--mock, --model)
│   ├── requirements.txt
│   └── .env.example
│
└── assets/
    ├── strands-logo.png
    ├── deepracer-logo.png
    └── deepracer_bg.png
```

---

## Requirements

| Requirement | Phase 1 | Phase 2 |
|-------------|---------|---------|
| Python 3.10+ | ✅ | ✅ |
| AWS DeepRacer on same network | ✅ | ✅ |
| DeepRacer web console password | ✅ | ✅ |
| AWS credentials + Bedrock access | ✅ | ✅ (or `--mock`) |
| `aws-deepracer-control-v2` | ✅ | ✅ |
| `strands-agents` | ✅ | ✅ |

---

## Author

**Vivek Raja P S**

[![GitHub](https://img.shields.io/badge/GitHub-Vivek072-181717?style=flat&logo=github)](https://github.com/Vivek072)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-meetvivekraja-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/meetvivekraja)
