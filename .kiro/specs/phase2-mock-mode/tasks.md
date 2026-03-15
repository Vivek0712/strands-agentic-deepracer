# Phase 2 Mock Mode — Tasks

## Task 1: Verify --mock flag in main.py
- [ ] `argparse` has `--mock` with `action="store_true"`
- [ ] `args.mock` → `policy = create_policy("mock")`
- [ ] `planner = None` in mock mode (not used)
- [ ] Welcome screen shows `[MOCK — no Bedrock / no hardware]`

## Task 2: Verify MockPolicy implementation
- [ ] `plan()` ignores `user_request` parameter
- [ ] Default canned plan is `[forward(2.0), stop]`
- [ ] Custom `canned_plan` accepted in constructor
- [ ] `provider_name` returns `"mock"`

## Task 3: Verify validate_plan() called in mock mode
- [ ] `main.py` calls `validate_plan(plan)` after `policy.plan(user_input)` in mock branch
- [ ] Invalid custom canned plan would be caught here

## Task 4: Test full mock REPL flow
- [ ] Run `python main.py --mock`
- [ ] Type any instruction → fixed plan displayed
- [ ] Type `y` → execution attempted (will fail without hardware — that's expected)
- [ ] Type `patterns` → pattern list shown
- [ ] Type `physics` → physics reference shown
- [ ] Type `exit` → clean exit

## Task 5: Test MockPolicy with custom plan
- [ ] Create `MockPolicy(canned_plan={"_reasoning": "test", "pattern": "square", "steps": [..., {"action": "stop"}]})`
- [ ] Confirm `plan("anything")` returns the custom plan
- [ ] Confirm `validate_plan()` passes on the custom plan

## Task 6: Verify mock mode works without credentials
- [ ] Unset `DEEPRACER_PASSWORD` and `AWS_REGION`
- [ ] Run `python main.py --mock`
- [ ] Confirm no error at startup
- [ ] Confirm planning works (no Bedrock call)
- [ ] Confirm execution fails gracefully (no hardware) with error message
