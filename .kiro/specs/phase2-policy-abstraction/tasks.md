# Phase 2 Policy Abstraction — Tasks

## Task 1: Verify NavigationPolicy interface
- [ ] Confirm `plan()` and `provider_name` raise `NotImplementedError` in base class
- [ ] Confirm all three subclasses implement both members

## Task 2: Verify NovaPolicy
- [ ] Constructor stores `self._agent = create_planner(model)`
- [ ] `plan()` delegates to `plan_navigation(self._agent, user_request)`
- [ ] `provider_name` returns the model ID from env or argument

## Task 3: Verify MockPolicy
- [ ] Default canned plan is `[forward(2.0), stop]`
- [ ] Custom `canned_plan` is accepted and stored
- [ ] `plan()` ignores `user_request` entirely
- [ ] Works with no network access

## Task 4: Verify ReplayPolicy
- [ ] Keys normalised to lowercase in `__init__`
- [ ] `plan()` raises `ValueError` listing available keys when not found
- [ ] Lookup is case-insensitive

## Task 5: Verify create_policy() factory
- [ ] `"nova"` → `NovaPolicy(**kwargs)`
- [ ] `"mock"` → `MockPolicy(**kwargs)`
- [ ] `"replay"` → `ReplayPolicy(**kwargs)`
- [ ] Unknown provider raises `ValueError` with available list
- [ ] `main.py` uses `create_policy("mock")` for `--mock` flag

## Task 6: Add ReplayPolicy usage example
- [ ] Document how to pre-load a named manoeuvre library
- [ ] Show example: `create_policy("replay", library={"circle": {...}})`
