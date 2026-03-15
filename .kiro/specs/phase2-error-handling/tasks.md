# Phase 2 Error Handling — Tasks

## Task 1: Audit is_error() usage across all files
- [ ] `agent.py` imports `is_error` from `deepracer_tools` — uses it in `execute_step()`
- [ ] `deepracer_agent_tool.py` imports `is_error` from `deepracer_tools` — uses it in `_execute_task_async()`
- [ ] `app_ui.py` does NOT import or call `is_error()` — uses inline ok computation
- [ ] No file duplicates the `startswith("error")` logic inline

## Task 2: Verify stop_on_failure emergency stop pattern
- [ ] `execute_plan()`: on `not sr.ok`, calls `execute_step({"action": "stop"})`
- [ ] Emergency result appended with `"[emergency]"` prefix
- [ ] Loop breaks after emergency stop
- [ ] `execute_plan_full()`: sets `result.aborted = True` and `result.abort_reason`

## Task 3: Verify execute_step() never raises
- [ ] All tool calls wrapped in try/except
- [ ] Exceptions become `StepResult(ok=False, message=f"Exception in '{action}': {exc}")`
- [ ] Unknown action returns `StepResult(ok=False, message="Unknown action...")`

## Task 4: Verify planning error propagation
- [ ] `main.py`: `except Exception as exc: print(f"❌ Planning failed: {exc}")` then continue
- [ ] `app_ui.py`: `except Exception as exc: return jsonify({"ok": False, "error": str(exc)}), 500`
- [ ] `deepracer_agent_tool.py`: `except Exception as exc: self._task_state.status = TaskStatus.ERROR`

## Task 5: Verify connection error handling
- [ ] `_get_client()` raises `RuntimeError` (not returns error string) when PASSWORD empty
- [ ] `_move_for_duration()` catches RuntimeError from `_get_client()` and returns error string
- [ ] `deepracer_connect()` catches all exceptions and returns error string
- [ ] `_execute_task_async()` checks `is_error(connect_msg)` and sets ERROR state

## Task 6: Verify cleanup error handling
- [ ] `cleanup()` has outer try/except
- [ ] `__del__` has try/except around `cleanup()` call
- [ ] `_action_stop()` catches hardware stop exception and includes in response text

## Task 7: Verify finally-block fix
- [ ] `_move_for_duration()` finally block has NO return statement
- [ ] `stop_warning` captured in local variable
- [ ] `stop_warning` checked AFTER try/finally block
- [ ] Success message returned only when no stop_warning
