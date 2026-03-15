# Phase 2: DeepRacerTool (AgentTool) — Implementation Tasks

## Task 1: Imports & Setup
- [ ] Import `AgentTool` from `strands.tools.tools`
- [ ] Import `ToolResultEvent` from `strands.types._events`
- [ ] Import `ToolSpec`, `ToolUse` from `strands.types.tools`
- [ ] Import `NavigationPolicy`, `PlanResult`, `StepResult`, `execute_step`, `execute_plan_full`, `validate_plan` from `agent`
- [ ] Import `deepracer_stop`, `reset_client`, `is_error` from `deepracer_tools`
- [ ] Set up `logger = logging.getLogger(__name__)`

## Task 2: TaskStatus Enum
- [ ] Define `TaskStatus(Enum)` with: IDLE, CONNECTING, PLANNING, RUNNING, COMPLETED, STOPPED, ERROR
- [ ] Confirm all 7 states are present

## Task 3: DeepRacerTaskState Dataclass
- [ ] Fields: `status`, `instruction`, `pattern`, `start_time`, `duration`, `completed_steps`, `total_steps`, `error_message`, `task_future`, `result`
- [ ] All fields have defaults — no required args

## Task 4: DeepRacerTool.__init__()
- [ ] Accept `policy: NavigationPolicy` and `tool_name: str = "deepracer"`
- [ ] Initialise `_task_state = DeepRacerTaskState()`
- [ ] Initialise `_shutdown_event = threading.Event()`
- [ ] Initialise `_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"{tool_name}_executor")`
- [ ] Log INFO: tool ready with policy provider name

## Task 5: tool_spec Property
- [ ] `name` = `self._tool_name_str`
- [ ] `action` enum = `["execute", "start", "status", "stop"]`
- [ ] `instruction` string field with description
- [ ] `required: ["action"]`

## Task 6: _execute_task_async()
- [ ] Phase 1 CONNECTING: call `deepracer_connect()`, check `is_error()`, set ERROR and return
- [ ] Phase 2 PLANNING: call `self._policy.plan(instruction)` + `validate_plan()`, catch exception → ERROR
- [ ] Set `total_steps`, `pattern`, transition to RUNNING
- [ ] Phase 3 loop: check `status != RUNNING` and `_shutdown_event.is_set()` at top of each iteration
- [ ] Call `execute_step(step)` via `asyncio.to_thread`
- [ ] On failure: call `deepracer_stop()` via `asyncio.to_thread`, set aborted, break
- [ ] Set duration, result, transition to COMPLETED or STOPPED
- [ ] Outer try/except: log ERROR, set ERROR state, call `deepracer_stop()`

## Task 7: _sync_wrapper()
- [ ] Try `asyncio.get_running_loop()` — if running, use nested ThreadPoolExecutor
- [ ] Except RuntimeError — use `asyncio.run(runner())`
- [ ] Return `self._build_payload()` after completion

## Task 8: _build_payload()
- [ ] Status icon ✅/❌ based on `status == COMPLETED`
- [ ] Lines: status, pattern, steps completed/total, duration, error if any
- [ ] Step log from `sr.display()` for each result
- [ ] Return `{"status": "success"|"error", "content": [{"text": "\n".join(lines)}]}`

## Task 9: Action Methods
- [ ] `_action_execute(instruction)` → `_sync_wrapper(instruction)`
- [ ] `_action_start(instruction)` → guard already-running → reset state → `_executor.submit(_sync_wrapper, instruction)`
- [ ] `_action_status()` → update duration if RUNNING → build status lines
- [ ] `_action_stop()` → check active states → set STOPPED → cancel future → call `deepracer_stop()` → return payload

## Task 10: stream() Entry Point
- [ ] Extract `tid`, `action`, `instruction` from `tool_use`
- [ ] Validate instruction present for execute/start → yield error event
- [ ] Dispatch dict to action methods
- [ ] Unknown action → yield error event
- [ ] Outer try/except → yield error event with exception message
- [ ] Yield exactly one `ToolResultEvent({"toolUseId": tid, **result})`

## Task 11: cleanup() / __del__
- [ ] `cleanup()`: set shutdown_event → check active states → call `_action_stop()` → `executor.shutdown(wait=True, cancel_futures=True)` → `reset_client()` → log INFO
- [ ] `__del__`: call `cleanup()` in try/except, swallow all exceptions

## Task 12: Integration Test
- [ ] Create `DeepRacerTool(policy=create_policy("mock"))` — confirm no errors
- [ ] Call `_action_execute("move forward")` with mock — confirm COMPLETED state
- [ ] Call `_action_start("move forward")` — confirm returns immediately
- [ ] Call `_action_status()` — confirm returns status dict
- [ ] Call `_action_stop()` — confirm STOPPED state and hardware stop attempted
- [ ] Call `cleanup()` — confirm executor shuts down cleanly
