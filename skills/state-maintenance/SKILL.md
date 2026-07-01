---
name: state-maintenance
description: Use when planning retention, cache pruning, log pruning, SQLite cleanup, or restart-safe maintenance for long-running private agent state.
---

# State Maintenance

Use this skill for bounded maintenance of private runtime state.

## Procedure

1. Identify the declared mutable root and the specific maintenance target.
2. Respect retention windows, max-delete limits, and workflow ownership.
3. Prefer dry-run counts and audit entries before destructive cleanup.
4. Delete only generated cache, expired logs, or state covered by the workflow contract.
5. Leave source/spec files and immutable runtime paths untouched.

## Guardrails

- Do not prune credentials, active approvals, current workflow locks, or live audit records.
- Do not cross filesystem boundaries outside declared mutable state.
- Treat uncertain ownership as a reason to skip and report, not delete.
