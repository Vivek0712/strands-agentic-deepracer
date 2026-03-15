# Phase 1: Plan JSON Schema — Requirements

## Overview
The navigation plan is the central data contract between the planner agent and the executor. This spec defines the exact schema, validation rules, and edge cases.

## Requirements

### REQ-SCHEMA-1: Top-Level Structure
```json
{
  "steps": [ ... ]
}
```
- The root object MUST have exactly one key: `"steps"`
- `"steps"` MUST be a non-null array (may be empty, but empty plans are handled gracefully)
- Any additional top-level keys MUST be ignored by the executor

### REQ-SCHEMA-2: Step Object
```json
{ "action": "<string>", "seconds": <float> }
```
- `"action"` MUST be present and MUST be a string
- `"seconds"` is OPTIONAL — present for motion actions, absent for `stop` and `connect`
- Any additional keys in a step MUST be ignored by the executor

### REQ-SCHEMA-3: Action Values
| action | seconds required | description |
|---|---|---|
| `"connect"` | no | Check connection and battery |
| `"forward"` | yes (default 2.0) | Move forward |
| `"backward"` | yes (default 2.0) | Move backward |
| `"left"` | yes (default 2.0) | Turn left while moving forward |
| `"right"` | yes (default 2.0) | Turn right while moving forward |
| `"stop"` | no | Immediate halt |

### REQ-SCHEMA-4: seconds Field
- MUST be a positive float when present
- MUST be coerced to `float` by the executor (model may return int or string)
- If unparseable, executor MUST default to `2.0`
- Recommended range: `1.0–3.0` (enforced by planner prompt)
- Hard maximum: `10.0` (executor clamps)

### REQ-SCHEMA-5: Action Case Handling
- The executor MUST normalise action to lowercase before dispatch
- The planner prompt instructs lowercase, but the executor MUST be defensive

### REQ-SCHEMA-6: Unknown Actions
- Unknown action values MUST produce a skip result string: `"Skipped unknown action '<action>'."`
- Unknown actions MUST NOT raise exceptions or abort the plan

### REQ-SCHEMA-7: Example Valid Plans
```json
{ "steps": [{ "action": "connect" }] }

{ "steps": [
    { "action": "forward", "seconds": 2.0 },
    { "action": "stop" }
]}

{ "steps": [
    { "action": "connect" },
    { "action": "forward", "seconds": 2.0 },
    { "action": "left",    "seconds": 1.0 },
    { "action": "right",   "seconds": 1.0 },
    { "action": "backward","seconds": 1.5 },
    { "action": "stop" }
]}
```
