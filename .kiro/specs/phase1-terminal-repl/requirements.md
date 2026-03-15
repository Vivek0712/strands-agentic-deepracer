# Phase 1: Terminal REPL — Requirements

## Overview
`main.py` provides an interactive command-line interface for the navigation planner. It handles all terminal I/O, leaving agent logic in `agent.py`.

## Requirements

### REQ-REPL-1: Startup
- MUST print a welcome banner showing the model name on startup
- MUST print example prompts in the welcome message
- MUST create the planner agent once before entering the loop
- MUST print a clear error and exit gracefully if agent creation fails

### REQ-REPL-2: Input Loop
- MUST loop indefinitely until the user types `exit`, `quit`, or `bye`
- MUST ignore empty input (just re-prompt)
- MUST handle `KeyboardInterrupt` with a message, NOT crash
- MUST support `help` and `?` commands that print example prompts

### REQ-REPL-3: Plan Display
- MUST print each step with its index, action name, and duration (if applicable)
- Format: `  1. forward for 2.0 s` or `  1. stop` (no seconds for stop/connect)

### REQ-REPL-4: Confirmation
- MUST prompt `Execute this plan? [y/N]: ` after displaying the plan
- MUST only proceed if the user types `y` or `yes` (case-insensitive)
- Any other input MUST cancel with a "Plan execution cancelled." message

### REQ-REPL-5: Execution Output
- MUST print `🚗 Executing plan...` before execution starts
- MUST print each step's action and result as it completes
- MUST print `✅ Plan execution complete.` after all steps finish

### REQ-REPL-6: Error Handling
- Planning failures MUST print `❌ Failed to plan navigation: <error>` and re-prompt
- Empty plans (no steps) MUST print a message and re-prompt without executing
- Agent creation failure MUST print instructions to check credentials and exit

### REQ-REPL-7: Separation of Concerns
- `main.py` MUST NOT contain any agent logic or tool calls
- All agent operations MUST be delegated to `agent.py` functions
- `main.py` only handles I/O, formatting, and the confirmation gate
