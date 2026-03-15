# Tasks: Use Cases Base Tools

## Task 1: Verify RobotTools Protocol
- [ ] Confirm `@runtime_checkable` decorator is present on `RobotTools`
- [ ] Confirm all 9 functions are declared as protocol members
- [ ] Confirm all 4 physics constants are declared as protocol members
- [ ] Test `isinstance(load_tools("deepracer"), RobotTools)` returns True

## Task 2: Verify load_tools()
- [ ] Test `load_tools("deepracer")` loads `use_cases/deepracer.py`
- [ ] Test `load_tools("drone")` loads `use_cases/drone.py`
- [ ] Test `load_tools("nonexistent")` raises `ImportError` with clear message
- [ ] Confirm loaded module is registered in `sys.modules`

## Task 3: Verify validate_tools()
- [ ] Test `validate_tools(load_tools("deepracer"))` returns `[]`
- [ ] Test `validate_tools(load_tools("drone"))` returns `[]`
- [ ] Test that a module missing `stop` returns `["stop"]` in the list
- [ ] Confirm `validate_tools()` never raises

## Task 4: Validate All Existing Use Cases
- [ ] Run `validate_tools(load_tools(uc))` for every use case file in `use_cases/`
- [ ] All must return empty list
- [ ] Document any that fail and fix missing exports

## Task 5: Integration Test
- [ ] Confirm `USE_CASE=roomba python common/main.py --mock` starts without error
- [ ] Confirm `USE_CASE=drone python common/main.py --mock` starts without error
- [ ] Confirm missing `USE_CASE` defaults to `deepracer`
