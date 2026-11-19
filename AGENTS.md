# Repository Agent Instructions
Specs: `nium_conversion_prototype_docs/` (start with `00_MASTER_PRD.md`; tasks in `tasks/`).
1. Read master PRD and relevant spec/task.
2. Obey task allowed-files list.
3. Implement assigned scope only.
4. Use Decimal; never float for money.
5. `accounts` owns current balances; frontend cannot update balances.
6. `conversion_transactions` is the single conversion/audit record; no separate ledger_entries table without approval.
7. Update both accounts and insert transaction atomically.
8. Enforce idempotency in backend and database.
9. Timeout is not proof of failure.
10. No live funds, blockchain, BitGo or paid APIs.
11. Run tests and report exact results.
12. No deployment or real credentials.
