# Agent Matrix

| Role | Owns | Must not own |
|---|---|---|
| Product/Orchestrator | PRD, scope, acceptance, task sequencing | Unapproved architecture changes |
| Backend Agent | FastAPI, services, repositories, schemas, migrations, backend tests | Frontend styling/copy |
| Frontend Agent | Wallet UI, conversion form, quote review, history, API client | Financial calculations/direct balance mutation |
| Design Agent | Tokens, components, interaction consistency | Workflow behaviour changes |
| QA Agent | Test plans, scenario verification, regression, correction record | Unilateral architecture changes |
| Documentation Agent | Runbook, API examples, demo script, evidence | Changing implementation decisions |

One active implementation agent at a time. Backend foundation before frontend integration. Product owner resolves conflicts.
