---
name: approval-gated-correspondence
description: Use when drafting email, LinkedIn, calendar, document, or public-post text that could be sent, shared, scheduled, or published after human approval.
---

# Approval-Gated Correspondence

Use this skill to draft communication while preserving a hard boundary between drafting and external action.

## Procedure

1. Draft in the principal's voice using only supplied evidence and declared private memory.
2. Include enough context for the principal to approve or reject without rereading the entire thread.
3. Keep the proposed outbound text exact and stable once it is placed behind an approval gate.
4. Create an approval request containing recipient, channel, exact text or artifact URL, expiry, and current-user approval requirement.
5. Mark the draft as blocked until the policy engine records exact current-user approval.

## Guardrails

- Never send, publish, invite, merge, or share as part of drafting.
- Never treat silence, historical preference, or inferred intent as approval.
- Escalate when the draft mentions compensation, legal status, medical details, confidential work, credentials, or private third-party content.
