# Phase 1: Planner Agent — Requirements

## Overview
The planner agent converts a natural-language driving instruction into a structured JSON plan using Amazon Bedrock Nova Lite via the Strands Agents framework. It has no tools — it only generates plans.

## Requirements

### REQ-PLAN-1: Agent Configuration
- The agent MUST be created with `tools=[]` — it must never call tools directly
- The system prompt MUST be the module-level `PLANNER_PROMPT` constant
- Model resolution order: `create_planner(model)` argument → `MODEL` env var → `DEFAULT_MODEL`
- `DEFAULT_MODEL` MUST be `"us.amazon.nova-lite-v1:0"`

### REQ-PLAN-2: System Prompt Content
The `PLANNER_PROMPT` MUST:
- Instruct the model to respond with ONLY a JSON object — no markdown, no prose, no explanation
- Define the exact JSON schema: `{ "steps": [ { "action": "...", "seconds": <float> }, ... ] }`
- List all allowed `action_name` values: `connect`, `forward`, `backward`, `left`, `right`, `stop`
- Specify that `"stop"` and `"connect"` MUST NOT include a `"seconds"` field
- Specify default duration of ~2.0 seconds when user does not specify
- Specify preferred duration range of 1.0–3.0 seconds
- Specify that unsafe/unclear instructions produce a conservative plan or single `"stop"` step
- Specify how to handle "full circle", "u-turn", "go around" — chain same-direction turn steps

### REQ-PLAN-3: plan_navigation() Parsing
- MUST handle raw dict responses from the agent (pass through directly)
- MUST strip markdown code fences (``` blocks) from string responses before parsing
- MUST call `json.loads()` on the cleaned string
- MUST validate that `"steps"` key exists and is a list — raise `ValueError` otherwise
- MUST NOT mutate the returned plan dict

### REQ-PLAN-4: execute_step() Dispatch
- MUST normalise action to lowercase before dispatch
- MUST default `seconds` to `2.0` for motion actions when missing or unparseable
- `"stop"` and `"connect"` MUST NOT pass `seconds` to their tool functions
- Unknown actions MUST return a skip message string, not raise an exception
- MUST return the string result from the tool function

### REQ-PLAN-5: execute_plan() Execution
- MUST iterate ALL steps regardless of individual step failures
- MUST return `List[Tuple[Dict, str]]` — one tuple per step
- MUST NOT perform any I/O (no print statements)
- MUST NOT raise exceptions — all errors are captured as result strings
