# Phase 1: Amazon Bedrock Integration — Tasks

## Task 1: Model Configuration
- [ ] Confirm `DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"` is a module-level constant in `agent.py`
- [ ] Confirm `create_planner()` resolves model as: arg → `os.getenv("MODEL", DEFAULT_MODEL)`
- [ ] Confirm `main.py` reads `MODEL = os.getenv("MODEL", DEFAULT_MODEL)` and prints it in welcome
- [ ] Confirm `.env.example` has `MODEL=us.amazon.nova-lite-v1:0`

## Task 2: Credential Chain Verification
- [ ] Confirm no `aws_access_key_id` or `aws_secret_access_key` appear anywhere in source files
- [ ] Confirm `AWS_REGION` is set in `.env` and `.env.example`
- [ ] Test with valid AWS credentials in `~/.aws/credentials` — confirm Bedrock call succeeds
- [ ] Test with missing credentials — confirm error propagates with a readable message

## Task 3: Response Parsing
- [ ] Confirm `plan_navigation()` handles `isinstance(raw, dict)` — passes through directly
- [ ] Confirm fence stripping handles ` ```json\n...\n``` ` format
- [ ] Confirm fence stripping handles ` ```\n...\n``` ` format (no language hint)
- [ ] Confirm `ValueError` is raised with message `"Planner response missing 'steps' list"` when invalid
- [ ] Confirm `ValueError` is raised on `json.loads()` failure (malformed JSON)

## Task 4: Agent Lifecycle
- [ ] CLI: confirm `create_planner()` is called once before the while loop in `main()`
- [ ] Web UI: confirm `get_planner()` uses `hasattr(get_planner, "_agent")` — not called per request
- [ ] Confirm agent creation failure in CLI prints credential hint and returns without entering loop
- [ ] Confirm agent creation failure in web UI surfaces as a 500 error on first `/api/plan` call

## Task 5: Prompt Integrity
- [ ] Confirm `PLANNER_PROMPT` is a module-level string constant
- [ ] Confirm it is NOT constructed dynamically (no f-string, no concatenation at call time)
- [ ] Confirm it contains the phrase "Do not include any explanation, markdown, or text outside the JSON"
- [ ] Confirm it lists all 6 action names
- [ ] Confirm it has the "full circle" / "u-turn" chaining rule
- [ ] Confirm it has the safety fallback rule for unsafe/unclear instructions

## Task 6: tools=[] Enforcement
- [ ] Confirm `Agent(tools=[], ...)` in `create_planner()` — no tool functions passed
- [ ] Confirm no deepracer_tools functions are imported inside `create_planner()`
- [ ] Confirm the planner agent object has no tool-calling capability
