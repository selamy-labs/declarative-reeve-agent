# System Context

This repository is the source specification and reference implementation for a
career-steward agent. It does not deploy or operate a live agent. Downstream
infrastructure chooses whether to deploy the verified artifacts and supplies
credentials by reference.

```mermaid
flowchart LR
  operator["Operator"]
  source["Repository source\nmanifest, policy, skills, workflows, and code"]
  artifact["Verified artifacts\nreference OCI image and rendered configuration"]
  infrastructure["Downstream infrastructure\ndeployment and secret references"]
  runtime["Running career-steward agent"]
  principal["Principal\ndirectives and approvals"]
  services["Declared external services"]
  state["Private state and audit data"]
  telemetry["Observability sinks"]

  operator -->|"edits declarations and implementation"| source
  source -->|"builds and verifies"| artifact
  artifact -->|"pinned input"| infrastructure
  infrastructure -->|"deploys and configures"| runtime
  principal <-->|"requests, drafts, and approvals"| runtime
  runtime -->|"policy-gated calls"| services
  runtime <-->|"declared writes and reads"| state
  runtime -->|"logs, metrics, traces, and audit events"| telemetry
```

The repository boundary ends at the verified artifacts. Runtime side effects
are constrained by the declared approval, privacy, and write-boundary policies;
the no-real-accounts simulator exercises that boundary without live services.

See [`../architecture.md`](../architecture.md) for the container view and the
derivation of runtime abilities.
