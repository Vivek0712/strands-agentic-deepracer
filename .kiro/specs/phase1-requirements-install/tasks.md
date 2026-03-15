# Phase 1: Dependency Installation — Tasks

## Task 1: Verify requirements.txt
- [ ] Confirm `strands-agents` is listed (no version pin)
- [ ] Confirm `strands-tools` is listed
- [ ] Confirm `python-dotenv` is listed
- [ ] Confirm `aws-deepracer-control-v2` is listed
- [ ] Confirm `flask` is listed
- [ ] Confirm no other packages are listed (keep it minimal)

## Task 2: Python Version Check
- [ ] Run `python --version` — confirm 3.10 or higher
- [ ] If using 3.9 or lower, update `agent.py` to use `Optional[str]` instead of `str | None`

## Task 3: Virtual Environment Setup (Recommended)
```bash
cd phase-1-agentic-navigation-planner
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```
- [ ] Confirm `.venv/` is listed in `.gitignore`
- [ ] Confirm `pip install -r requirements.txt` completes without errors

## Task 4: Import Smoke Tests
```bash
python -c "from strands import Agent, tool; print('strands-agents OK')"
python -c "import aws_deepracer_control_v2 as drctl; print('deepracer control OK')"
python -c "from flask import Flask; print('flask OK')"
python -c "from dotenv import load_dotenv; print('python-dotenv OK')"
```
- [ ] All four commands print OK

## Task 5: Full Module Load Test
```bash
python -c "from agent import create_planner, plan_navigation, execute_plan; print('agent OK')"
python -c "from deepracer_tools import deepracer_connect, deepracer_stop; print('tools OK')"
python -c "from app_ui import app; print('app_ui OK')"
```
- [ ] All three commands print OK (deepracer_tools will load even without a car connected)
