# Phase 1: Planner Agent — Implementation Tasks

## Task 1: Constants & Imports
- [ ] Import `json`, `os`, `Path`, `typing` types, `dotenv.load_dotenv`, `strands.Agent`
- [ ] Import all 6 tool functions from `deepracer_tools`
- [ ] Load `.env` from `Path(__file__).resolve().parent / ".env"`
- [ ] Define `DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"`

## Task 2: PLANNER_PROMPT
- [ ] Write role declaration: navigation planner for AWS DeepRacer
- [ ] Write output instruction: respond ONLY with JSON, no markdown, no explanation
- [ ] Write JSON schema block showing `steps` array with `action` and optional `seconds`
- [ ] List all 6 allowed action names with descriptions
- [ ] Add rule: `"stop"` and `"connect"` must NOT include `"seconds"`
- [ ] Add rule: default duration ~2.0s when not specified; prefer 1.0–3.0s range
- [ ] Add rule: unsafe/unclear → conservative plan or single `"stop"` step
- [ ] Add rule: "full circle" / "u-turn" → chain same-direction turn steps, no single large-angle step

## Task 3: `create_planner(model=None)`
- [ ] Resolve model: argument → `MODEL` env var → `DEFAULT_MODEL`
- [ ] Return `Agent(model=m, tools=[], system_prompt=PLANNER_PROMPT)`
- [ ] Add return type annotation `-> Agent`

## Task 4: `plan_navigation(planner, user_request)`
- [ ] Call `planner(user_request)` and capture raw response
- [ ] If response is already a dict, use it directly
- [ ] If response is a string, strip markdown fences, then `json.loads()`
- [ ] Validate `"steps"` key exists and is a list — raise `ValueError` with clear message if not
- [ ] Return the validated plan dict
- [ ] Add type annotations: `(Agent, str) -> Dict[str, Any]`

## Task 5: `execute_step(step)`
- [ ] Extract `action = str(step.get("action", "")).lower()`
- [ ] Extract `seconds = step.get("seconds")`
- [ ] For motion actions, default and coerce `seconds` to `float`, fallback `2.0`
- [ ] Dispatch to correct tool function based on action
- [ ] Return skip message for unknown actions
- [ ] Add type annotation: `(Dict[str, Any]) -> str`

## Task 6: `execute_plan(plan)`
- [ ] Iterate `plan.get("steps", [])`
- [ ] Call `execute_step(step)` for each, append `(step, result)` to results list
- [ ] Return `List[Tuple[Dict[str, Any], str]]`
- [ ] Confirm: no print statements, no exceptions raised, no short-circuiting

## Task 7: Verification
- [ ] Confirm `create_planner()` passes `tools=[]`
- [ ] Confirm `plan_navigation()` handles both dict and string responses
- [ ] Confirm `execute_step()` returns a string for every possible input (including unknown actions)
- [ ] Confirm `execute_plan()` runs all steps even when one returns an error string
- [ ] Confirm `PLANNER_PROMPT` contains all 6 action names
