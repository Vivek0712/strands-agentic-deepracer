# Phase 2 Terminal REPL — Tasks

## Task 1: Verify CLI argument parsing
- [ ] `--mock` sets `args.mock = True`, uses `create_policy("mock")`
- [ ] `--model <id>` overrides `effective_model`
- [ ] Default model falls back to `MODEL` env var then `DEFAULT_MODEL`
- [ ] Failed planner creation prints error and calls `sys.exit(1)`

## Task 2: Verify built-in commands
- [ ] `help` / `?` / `h` → `print_help()`
- [ ] `patterns` / `pattern` / `list` → `print_patterns()`
- [ ] `physics` / `limits` / `specs` → `print_physics()`
- [ ] `exit` / `quit` / `bye` / `q` → break with goodbye message

## Task 3: Verify print_plan() formatting
- [ ] Pattern name displayed
- [ ] Reasoning word-wrapped at W+4 = 60 chars with subsequent_indent
- [ ] Steps numbered from 1
- [ ] Seconds shown for movement steps, omitted for connect/stop

## Task 4: Verify print_results() icons
- [ ] `✓` for successful steps
- [ ] `✗` for failed steps (increments fail_count)
- [ ] `⚡` for emergency steps (not counted in ok or fail)
- [ ] Summary: `✅ Complete` when fail_count == 0
- [ ] Summary: `❌ Aborted` when fail_count > 0

## Task 5: Verify confirmation gate
- [ ] `y` or `yes` → execute
- [ ] Any other input → "Plan cancelled."
- [ ] `KeyboardInterrupt` → "Cancelled." and continue loop
- [ ] `EOFError` → "Cancelled." and continue loop

## Task 6: Verify print_physics() content
- [ ] Min turning radius: 0.28 m
- [ ] Max corner speed: 1.5 m/s
- [ ] Forward speed: ~0.40 m/s
- [ ] Turn speed: ~0.25 m/s
- [ ] Rotation table: 1.5 s ≈ 90°, 3.0 s ≈ 180°, 4.5 s ≈ 270°, 6.0 s ≈ 360°
- [ ] Formula: (angle / 90) × 1.5 s
- [ ] MAX_STEP_SECONDS and MAX_PLAN_STEPS shown

## Task 7: Verify print_patterns() lists all 15 patterns
- [ ] All 15 pattern names present with descriptions
- [ ] Descriptions match the pattern library in agent.py

## Task 8: Verify mock mode works offline
- [ ] `--mock` flag: no Bedrock call, no hardware call
- [ ] Plan is the fixed canned plan from MockPolicy
- [ ] validate_plan() still called on mock plan
- [ ] Full REPL flow works without network
