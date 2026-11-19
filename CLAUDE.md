# AI Coding Instructions
Follow `AGENTS.md` and `nium_conversion_prototype_docs/08_BUILD_AND_AGENT_GUIDE.md`. Specs and tasks are in `nium_conversion_prototype_docs/`.
Stack: FastAPI + SQLAlchemy + SQLite (`backend/`), React + Vite + TS (`frontend/`), pytest (`tests/`). Python venv at `.venv` (`.venv/Scripts/python -m pytest`).
Balances: available/reserved/pending stored as integer minor units; Decimal in code; never floats. Check-and-reserve is one conditional UPDATE.
Implement small changes within allowed files. Add tests for every financial rule. Keep pricing/pair config out of UI logic; mock pricing behind an adapter. Never retry an uncertain conversion with a new idempotency key. After editing, run tests and report files, commands, results, deviations and limitations. Do not deploy.
