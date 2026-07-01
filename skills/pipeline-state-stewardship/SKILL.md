---
name: pipeline-state-stewardship
description: Use when updating career pipeline state, throughput ledgers, contact/company pages, private knowledge entries, or durable career memory.
---

# Pipeline State Stewardship

Use this skill to maintain durable private career state without leaking or corrupting it.

## Procedure

1. Treat the pipeline row, company page, contact page, artifact links, and audit entry as a single state update.
2. Record source, timestamp, evidence pointer, classification, current state, next action, approval status, and owner.
3. Prefer append-only audit entries for meaningful decisions and external-action attempts.
4. Keep generated work under declared mutable roots.
5. Make updates idempotent: rerunning the same evidence should not duplicate contacts, rows, or notifications.

## Guardrails

- Do not write outside `/opt/data/**` at runtime.
- Do not mutate bundled repo files from inside the pod.
- Do not commit private state back to the source/spec repository.
