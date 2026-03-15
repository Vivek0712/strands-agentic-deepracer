# Phase 1: Connect Action — Tasks

## Task 1: deepracer_connect() Implementation
- [ ] Confirm `@tool` decorator is present
- [ ] Confirm docstring: "Connect to the DeepRacer via web API and show basic vehicle info."
- [ ] Confirm `buf = io.StringIO()` is created inside the function (not reused)
- [ ] Confirm `with redirect_stdout(buf): client.show_vehicle_info()` pattern
- [ ] Confirm `out = buf.getvalue().strip()`
- [ ] Confirm `return out or f"Connected to DeepRacer at {IP}."` fallback
- [ ] Confirm `show_vehicle_info()` is wrapped in try/except returning error string

## Task 2: execute_step() Connect Dispatch
- [ ] Confirm `if action == "connect": return deepracer_connect()` — no seconds argument
- [ ] Confirm `seconds` is NOT passed to `deepracer_connect()` even if present in the step

## Task 3: PLANNER_PROMPT Connect Rule
- [ ] Confirm `"connect"` is in the allowed actions list
- [ ] Confirm description: "check connection / battery before moving"
- [ ] Confirm rule: "For 'connect', omit 'seconds'"

## Task 4: Plan Schema for Connect
- [ ] Confirm `{"action": "connect"}` is a valid step (no seconds required)
- [ ] Confirm `{"action": "connect", "seconds": 1.0}` is also handled gracefully (seconds ignored)

## Task 5: Manual Tests
- [ ] Submit "Connect to the car" — confirm plan is `[{"action": "connect"}]`
- [ ] Execute the plan — confirm vehicle info or fallback string is printed
- [ ] Submit "Check the battery" — confirm plan includes a connect step
- [ ] With wrong IP: confirm error string starting with "Error" is returned and shown to user
