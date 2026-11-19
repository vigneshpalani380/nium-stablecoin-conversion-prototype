# P001 — Repository Discovery and Foundation

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** None  
**Read:** 00_MASTER_PRD.md, 08_BUILD_AND_AGENT_GUIDE.md

## Objective
Create minimal project skeleton after inspecting the repository.

## Scope
Inspect existing structure and conventions; establish backend, frontend, shared config and tests layout.

## Acceptance criteria
- Backend health endpoint and frontend shell run locally; no unrelated rewrites.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`README.md`, `AGENTS.md`, `CLAUDE.md`, `project config and app entrypoints`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
