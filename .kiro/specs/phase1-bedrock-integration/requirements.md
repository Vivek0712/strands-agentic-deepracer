# Phase 1: Amazon Bedrock Integration — Requirements

## Overview
The planner agent uses Amazon Bedrock Nova Lite via the Strands Agents framework. This spec covers model selection, credential handling, region configuration, and prompt design constraints.

## Requirements

### REQ-BEDROCK-1: Model Selection
- Default model MUST be `us.amazon.nova-lite-v1:0`
- Model MUST be overridable via the `MODEL` environment variable
- The model ID MUST be passed to `strands.Agent(model=...)` — not hardcoded in the Agent call
- The resolved model name MUST be displayed in the CLI welcome message

### REQ-BEDROCK-2: AWS Credentials
- Credentials MUST be sourced from the standard AWS credential chain (env vars, `~/.aws/credentials`, IAM role)
- Credentials MUST NOT be hardcoded anywhere in the codebase
- `AWS_REGION` env var MUST be respected by the Bedrock client
- If credentials are missing or invalid, the error from Strands/Bedrock MUST propagate to the user with a clear message

### REQ-BEDROCK-3: Prompt Design
- The system prompt MUST instruct the model to output ONLY valid JSON — no markdown, no prose
- The prompt MUST be concise enough to work efficiently with Nova Lite's context window
- The prompt MUST NOT use few-shot examples (keeps token usage low)
- The prompt MUST be a module-level constant (`PLANNER_PROMPT`) — not constructed dynamically

### REQ-BEDROCK-4: Response Parsing Robustness
- The parser MUST handle responses where the model wraps JSON in markdown fences (` ```json ... ``` `)
- The parser MUST handle responses where the model returns a raw dict (Strands may deserialise automatically)
- The parser MUST raise `ValueError` with a clear message if the response cannot be parsed
- The parser MUST validate the `"steps"` key exists and is a list before returning

### REQ-BEDROCK-5: Agent Lifecycle
- The planner agent MUST be created once per process — not per request
- CLI: created in `main()` before the REPL loop
- Web UI: created lazily on first request via `get_planner()` singleton
- Agent creation failure MUST be caught and reported with instructions to check credentials

### REQ-BEDROCK-6: No Tool Calls from Planner
- The planner agent MUST have `tools=[]`
- The planner MUST never be given access to `deepracer_tools` functions
- Tool execution is always explicit, user-confirmed, and handled by `execute_plan()`
