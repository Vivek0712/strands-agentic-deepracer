---
inclusion: manual
---

# Phase 1 — Extension Patterns

## Adding a New Movement Action

Follow this checklist in order. Every step is required.

### 1. `deepracer_tools.py`
```python
@tool
def deepracer_<name>(seconds: float = 2.0) -> str:
    """One-line description of what this action does."""
    return _move_for_duration(<steering>, <throttle>, seconds)
```
- Route through `_move_for_duration` — never call `client.move()` directly
- Use negative throttle for forward-direction moves
- Add to imports in `agent.py`

### 2. `agent.py` — execute_step() dispatch
```python
if action == "<name>":
    return deepracer_<name>(seconds=seconds)
```
- Place before the final `return f"Skipped unknown action..."` line
- Include the `seconds` defaulting block if it's a motion action

### 3. `agent.py` — PLANNER_PROMPT
Add to the "Allowed action_name values" list:
```
- "<name>"  : description of when to use it
```
Specify whether it takes a `"seconds"` field.

### 4. Specs to update
- `.kiro/specs/phase1-deepracer-tools/tasks.md` — add a task
- `.kiro/specs/phase1-planner-agent/requirements.md` — update REQ-PLAN-2 and REQ-PLAN-4
- `.kiro/specs/phase1-plan-json-schema/requirements.md` — update REQ-SCHEMA-3 action table

---

## Switching to a Different LLM

Only `.env` needs to change:
```
MODEL=us.amazon.nova-pro-v1:0
```
No code changes required. The fence-stripping parser in `plan_navigation()` handles models that wrap JSON in markdown.

---

## Adding a New Flask Endpoint

1. Add route in `app_ui.py` following the existing pattern
2. Validate input and return 400 for missing/invalid data
3. Return `{"error": "..."}` for all error cases
4. Never expose raw tool output strings in responses
5. Add the endpoint to `.kiro/specs/phase1-web-ui/requirements.md`

---

## Adding a New UI Panel

1. Add HTML section inside `.card.chat-layout` in `index.html`
2. Hide it by default with `style="display: none;"`
3. Show/hide via JS `style.display` (not CSS class toggling)
4. Follow the existing `.card` styling for consistency
5. Ensure it collapses correctly in the `@media (max-width: 768px)` breakpoint

---

## Porting to Phase 2

Phase 2 (`phase-2-strands-robots-deepracer`) uses a different architecture where the DeepRacer agent runs on the car itself. Key differences:
- `deepracer_agent_tool.py` wraps the car agent as a tool for a higher-level orchestrator
- The confirmation gate moves to the orchestrator level
- `deepracer_tools.py` is shared/adapted, not replaced
