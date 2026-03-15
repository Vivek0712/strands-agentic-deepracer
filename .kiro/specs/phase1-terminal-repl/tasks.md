# Phase 1: Terminal REPL — Implementation Tasks

## Task 1: Imports & Setup
- [ ] Import `os`, `Path`, `load_dotenv`
- [ ] Import `create_planner`, `plan_navigation`, `execute_plan`, `DEFAULT_MODEL` from `agent`
- [ ] Load `.env` from `Path(__file__).resolve().parent / ".env"`
- [ ] Read `MODEL = os.getenv("MODEL", DEFAULT_MODEL)`

## Task 2: `print_welcome()`
- [ ] Print app title with 🏎️ emoji
- [ ] Print separator line (52 chars)
- [ ] Print one-line description of the plan-confirm-execute flow
- [ ] Print example prompts inline
- [ ] Print "Type 'help' for more, 'exit' to quit."
- [ ] Print current model name

## Task 3: `print_help()`
- [ ] Print at least 4 example prompts covering: connect, forward, forward+backward, multi-step with turn

## Task 4: `main()` — Startup
- [ ] Call `print_welcome()`
- [ ] Call `create_planner()` in try/except
- [ ] On failure: print `❌ Failed to create planner agent: <exc>` + credential hint, return

## Task 5: `main()` — REPL Loop
- [ ] `while True:` loop with `input("\n🏎️  > ").strip()`
- [ ] Handle `KeyboardInterrupt`: print message, `continue`
- [ ] Skip empty input with `continue`
- [ ] Handle `exit`/`quit`/`bye`: print "Exiting." and `break`
- [ ] Handle `help`/`?`: call `print_help()` and `continue`

## Task 6: `main()` — Plan & Confirm
- [ ] Call `plan_navigation(planner, user_input)` in try/except
- [ ] On failure: print `❌ Failed to plan navigation: <exc>`, `continue`
- [ ] If `steps` is empty: print message, `continue`
- [ ] Print "Planned steps:" header
- [ ] For each step: print `  {idx}. {action} for {seconds} s` or `  {idx}. {action}` (no seconds)
- [ ] Prompt `Execute this plan? [y/N]: `
- [ ] If not `y`/`yes`: print "Plan execution cancelled.", `continue`

## Task 7: `main()` — Execution
- [ ] Print `\n🚗 Executing plan...`
- [ ] Call `execute_plan(plan)`
- [ ] For each `(step, result)`: print step index, action, then result
- [ ] Print `\n✅ Plan execution complete.`

## Task 8: Entry Point
- [ ] `if __name__ == "__main__": main()`

## Task 9: Verification
- [ ] Confirm `KeyboardInterrupt` does not crash the loop
- [ ] Confirm `exit` exits cleanly
- [ ] Confirm empty input is silently ignored
- [ ] Confirm plan with 0 steps does not attempt execution
- [ ] Confirm `n` input at confirmation cancels without executing
