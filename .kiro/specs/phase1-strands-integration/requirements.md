# Phase 1: Strands Agents Integration — Requirements

## Overview
Phase 1 uses the Strands Agents framework for two purposes: the `@tool` decorator to register DeepRacer control functions, and the `Agent` class to create the navigation planner. This spec covers correct usage of both.

## Requirements

### REQ-STRANDS-1: @tool Decorator
- All six DeepRacer control functions MUST be decorated with `@tool` from `strands`
- Each decorated function MUST have a docstring — Strands uses it as the tool description
- Tool functions MUST have typed parameters — Strands uses type hints for schema generation
- The `@tool` decorator MUST be the outermost decorator on each function

### REQ-STRANDS-2: Agent Construction
- The planner MUST be created with `strands.Agent(model=..., tools=[], system_prompt=...)`
- `tools=[]` is intentional — the planner is a pure JSON generator, not a tool-caller
- The `system_prompt` MUST be passed as a keyword argument, not positional
- The model string MUST be a valid Bedrock cross-region inference profile ID

### REQ-STRANDS-3: Agent Invocation
- The planner is invoked by calling it directly: `planner(user_request)`
- The return value may be a dict (Strands auto-deserialised) or a string — both MUST be handled
- Do NOT call `planner.run()` or any other method — use direct call syntax

### REQ-STRANDS-4: Tool Imports
- Import `tool` from `strands` (not `strands.tools` or any submodule)
- Import `Agent` from `strands`
- Both are available from the top-level `strands` package

### REQ-STRANDS-5: Dependency Version
- `strands-agents` and `strands-tools` MUST both be listed in `requirements.txt`
- No version pins are required unless a breaking change is encountered
- `strands-tools` provides additional built-in tools (not used in Phase 1 but listed for completeness)
