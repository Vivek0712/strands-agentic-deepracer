---
inclusion: fileMatch
fileMatchPattern: "phase-1-agentic-navigation-planner/agent.py"
---

# Agent Logic — Coding Standards & Patterns

## Planner Agent
- Created via `create_planner()` — returns a `strands.Agent` with `tools=[]` (no tool calls, pure JSON output)
- System prompt is `PLANNER_PROMPT` — do not inline it; keep it as a module-level constant
- Model is resolved: argument → `MODEL` env var → `DEFAULT_MODEL` fallback

## plan_navigation()
- Always strip markdown fences from raw LLM output before `json.loads()`
- Validate that `"steps"` key exists and is a list — raise `ValueError` otherwise
- Never mutate the returned dict

## execute_step()
- Dispatch on `step["action"].lower()` — always lowercase before comparing
- Default `seconds = 2.0` when missing or unparseable for motion actions
- `"stop"` and `"connect"` never use a `seconds` argument
- Return the string result from the tool — never print inside this function

## execute_plan()
- No I/O — pure data in, list of `(step, result)` tuples out
- Iterate all steps even if one fails (don't short-circuit on error strings)

## Imports
When adding new tools, import them explicitly from `deepracer_tools` — do not use `*` imports.

## PLANNER_PROMPT Rules (do not weaken)
- Must instruct the model to output ONLY valid JSON, no markdown, no prose
- Must list all allowed `action_name` values
- Must specify that `"stop"` has no `"seconds"` field
- Must handle "full circle" / "u-turn" as chained same-direction turn steps
