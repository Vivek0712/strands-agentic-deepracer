# Phase 2 Terminal REPL — Requirements

## Overview
The terminal REPL (`main.py`) is the primary interactive interface for the navigation
planner. It supports live Nova Lite planning, offline mock mode, and reference commands
for patterns and physics. It is the Phase 2 equivalent of the Phase 1 REPL with
significant enhancements.

## Functional Requirements

### FR-1: CLI Flags
- `--mock` — use `MockPolicy`, no Bedrock calls, no hardware needed
- `--model <id>` — override Bedrock model ID (default from `MODEL` env var)
- Both flags are optional; default is live Nova Lite

### FR-2: Built-in Commands
| Command | Aliases | Output |
|---|---|---|
| `help` | `?`, `h` | Navigation prompt examples + command list |
| `patterns` | `pattern`, `list` | All 15 named patterns with descriptions |
| `physics` | `limits`, `specs` | Vehicle physics + rotation calibration table |
| `exit` | `quit`, `bye`, `q` | Graceful exit |

### FR-3: Plan Display (print_plan)
- Shows: pattern name, reasoning (word-wrapped to 56+4 chars), numbered step list
- Each step: `{idx}. {action}  {seconds}s` (seconds omitted for connect/stop)
- Reasoning wrapped with `textwrap.fill()` using `subsequent_indent`

### FR-4: Result Display (print_results)
- Shows per-step pass/fail with icons: `✓` (ok), `✗` (failed), `⚡` (emergency)
- Emergency steps detected by `"[emergency]"` in message
- Summary line: `✅ Complete — N step(s)` or `❌ Aborted — N ok · N failed`

### FR-5: Confirmation Gate
- User MUST type `y` or `yes` to execute — any other input cancels
- Prompt: `"  Execute this plan? [y/N]: "`
- `KeyboardInterrupt` and `EOFError` during confirmation → print "Cancelled" and continue

### FR-6: Planning Flow
1. Print `"  ⏳ Planning…"`
2. Call `policy.plan(user_input)` (mock) or `plan_navigation(planner, user_input)` (live)
3. Call `validate_plan(plan)` — catches `ValueError`, prints error, continues loop
4. Call `print_plan(plan)`
5. Prompt for confirmation
6. On `y`/`yes`: print `"  🚗 Executing plan…"`, call `execute_plan(plan)`, call `print_results(results)`

### FR-7: Welcome Screen
- Shows: title, quick examples list, model name (or `[MOCK]`), limits, available commands
- Displayed once at startup

### FR-8: Physics Reference Screen
- Shows: min turning radius, max corner speed, forward speed, turn speed
- Shows: rotation calibration table (1.5 s ≈ 90°, full table)
- Shows: angle→duration formula
- Shows: planner safety caps (MAX_STEP_SECONDS, MAX_PLAN_STEPS)

## Non-Functional Requirements
- NFR-1: `KeyboardInterrupt` during input → print reminder, continue loop (do not exit)
- NFR-2: `EOFError` during input → print "Exiting" and break
- NFR-3: Planning exceptions are caught and displayed — REPL continues
- NFR-4: Execution exceptions are caught and displayed — REPL continues
