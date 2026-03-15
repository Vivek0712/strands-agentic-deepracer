# Tasks: Use Case Library

## Task 1: Inventory Check
- [ ] List all `*.py` files in `use_cases/` (excluding `common/`)
- [ ] Cross-reference against README table — flag any missing or undocumented files
- [ ] Confirm `warehouse_robot.py` exists (listed in README but not yet verified)

## Task 2: Validate All Use Cases
- [ ] Run `validate_tools(load_tools(name))` for every use case
- [ ] All must return empty list — fix any that don't

## Task 3: Rotation Calibration Audit
- [ ] Confirm each use case docstring documents angular rate and default turn angle
- [ ] Flag any use cases where physics constants appear to be unverified placeholders
- [ ] Confirm ROS2 use cases use `math.degrees(ANGULAR_VEL * seconds)` in return strings

## Task 4: Vision Prompt Review
- [ ] Review each use case for domain-specific hazards
- [ ] Add recommended `VISION_SYSTEM_PROMPT` to docstring for: pipeline_crawler (cracks/corrosion), drone (people/obstacles), boat (swimmers/debris), robot_arm (hand-in-workspace)
- [ ] Confirm all use cases work with default VisionAssessor prompt

## Task 5: README Accuracy
- [ ] Verify every row in the "Available Use Cases" table matches the actual implementation
- [ ] Update turning model column for any use cases where it's incorrect
- [ ] Add `warehouse_robot.py` row if missing

## Task 6: End-to-End Smoke Test (--mock)
- [ ] Run `USE_CASE={name} python common/main.py --mock` for each use case
- [ ] Confirm startup, planning, and mock execution complete without error
- [ ] Document any use cases that fail mock mode and why
