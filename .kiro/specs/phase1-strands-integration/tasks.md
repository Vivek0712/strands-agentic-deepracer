# Phase 1: Strands Agents Integration — Tasks

## Task 1: Tool Decorator Audit
- [ ] Confirm `from strands import tool` is the import (not a submodule)
- [ ] Confirm `@tool` is present on: `deepracer_connect`, `deepracer_move_forward`, `deepracer_move_backward`, `deepracer_turn_left`, `deepracer_turn_right`, `deepracer_stop`
- [ ] Confirm each has a docstring (single line is fine)
- [ ] Confirm each has typed parameters: `seconds: float = 2.0` for motion tools, `-> str` return type

## Task 2: Agent Construction Audit
- [ ] Confirm `from strands import Agent` is the import
- [ ] Confirm `Agent(model=m, tools=[], system_prompt=PLANNER_PROMPT)` — all keyword args
- [ ] Confirm `tools=[]` — not `None`, not omitted
- [ ] Confirm model string is a valid cross-region inference profile (starts with `us.` for us-east-1)

## Task 3: Agent Invocation Audit
- [ ] Confirm `planner(user_request)` direct call syntax in `plan_navigation()`
- [ ] Confirm no `.run()`, `.invoke()`, or `.chat()` method calls
- [ ] Confirm both dict and string return types are handled

## Task 4: Requirements.txt
- [ ] Confirm `strands-agents` is listed
- [ ] Confirm `strands-tools` is listed
- [ ] Confirm `python-dotenv` is listed
- [ ] Confirm `aws-deepracer-control-v2` is listed
- [ ] Confirm `flask` is listed

## Task 5: Import Smoke Test
- [ ] Run `python -c "from strands import Agent, tool; print('OK')"` in the phase-1 directory
- [ ] Run `python -c "import aws_deepracer_control_v2; print('OK')"` to confirm control lib is installed
- [ ] Run `python -c "from agent import create_planner; print('OK')"` to confirm agent module loads
