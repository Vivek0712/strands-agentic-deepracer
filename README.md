<div align="center">

<img src="assets/strands-logo.png" alt="Strands" width="140" /> &nbsp; **×** &nbsp; <img src="assets/deepracer-logo.png" alt="AWS DeepRacer" width="140" />

# Strands Agentic DeepRacer

*Agentic navigation and control for AWS DeepRacer using [Strands](https://strandsagents.com) and natural language.*

[![Strands](https://img.shields.io/badge/Strands-Agentic-0969da?style=flat)](https://strandsagents.com) [![AWS DeepRacer](https://img.shields.io/badge/AWS-DeepRacer-FF9900?style=flat)](https://aws.amazon.com/deepracer/)

<br/>

</div>

---

## Phase 1: PC Operator — Agentic Planner

**PC (operator)** runs the agentic system. The **Planner** produces a navigation plan from natural language; the operator confirms; the plan is communicated to the DeepRacer and executed in one go.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PC (Operator)                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Agentic system — Planner                                            │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │ │
│  │  │ Natural      │───▶│ LLM (Nova)   │───▶│ JSON plan                │ │ │
│  │  │ language     │    │ Planner      │    │ [connect, fwd, left, …]  │ │ │
│  │  │ prompt       │    │              │    │                          │ │ │
│  │  └──────────────┘    └──────────────┘    └────────────┬─────────────┘ │ │
│  │                                                         │             │ │
│  │  Operator confirms (Execute / Cancel)                   ▼             │ │
│  │                                              ┌──────────────────────┐ │ │
│  │                                              │ Plan executor        │ │ │
│  │                                              │ (deepracer_tools)    │ │ │
│  │                                              └──────────┬───────────┘ │ │
│  └─────────────────────────────────────────────────────────┼─────────────┘ │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
                                    Plan / commands (e.g. web API)
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AWS DeepRacer (device)                                                  │
│  Receives and runs the plan (forward, turn left/right, stop, etc.)       │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Location:** [phase-1-agentic-navigation-planner](./phase-1-agentic-navigation-planner/)
- **Flow:** Prompt → LLM plan (JSON) → operator confirm → full plan sent to DeepRacer → execution via DeepRacer web API.

### Demo

**PC Agent Planner (UI)** — Planner web UI: prompt → plan → Execute / Cancel.

![PC Agent Planner UI](./phase-1-agentic-navigation-planner/demo/pc_agent_planner.gif)

**Execution**

*Move forward 2 seconds*

![Move forward 2 seconds](./phase-1-agentic-navigation-planner/demo/move_2sec.gif)

*Move forward and backward 2 seconds*

![Move forward and backward 2 seconds](./phase-1-agentic-navigation-planner/demo/move_fb_2sec.gif)

---

## Phase 2: Edge-Deployed LLM — Agentic Control

Prompts from the **PC** are sent to an **edge-deployed LLM** (on or near the device). The agentic system runs at the edge and controls the car directly (no “plan then execute” from the PC; the edge agent decides and acts).

- **PC:** Sends natural-language prompts (e.g. “go forward then turn left”).
- **Edge:** LLM + agentic system deployed on the edge; interprets prompts and issues control commands to the DeepRacer.
- **Outcome:** Lower latency, control loop stays at the edge; PC is the command source only.

*(Implementation: planned.)*

---

## Phase 3: Edge LLM + Camera Navigation & Adaptive Execution

Same as Phase 2 (PC prompts → edge-deployed LLM with agentic system controlling the car), plus:

- **Camera-based navigation:** Edge uses camera input for perception and navigation decisions.
- **Intermediate plan changes:** Plan can be updated during execution (e.g. replan based on camera or obstacles).
- **Outcome:** More adaptive, vision-aware driving with mid-execution plan updates.

*(Implementation: planned.)*

---

## Summary

| Phase | Description |
|-------|-------------|
| **Phase 1** | PC operator — Agentic Planner. Plan on PC, confirm, then send full plan to DeepRacer. |
| **Phase 2** | PC prompts → Edge-deployed LLM with agentic system → direct control of the car. |
| **Phase 3** | Same as Phase 2 + camera navigation and intermediate plan execution changes. |

---

## Requirements

- AWS DeepRacer on the same network (web console reachable for Phase 1)
- AWS credentials for Bedrock (Nova) for Phase 1
- Python 3.10+

See each phase’s directory and `README.md` for setup and run instructions.

---

<div align="center">

## Author

**Vivek Raja P S**

[![GitHub](https://img.shields.io/badge/GitHub-Vivek072-181717?style=flat&logo=github)](https://github.com/Vivek072) [![LinkedIn](https://img.shields.io/badge/LinkedIn-meetvivekraja-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/meetvivekraja)

</div>
