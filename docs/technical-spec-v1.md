# Technical Spec v1: Career Steward Agent

## Objective

Define a buildable v1 specification and reference implementation for a career-steward agent. A fresh operator must be able to instantiate an equivalent agent for a new person from declarations alone, bringing only their own credentials, with no source-operator private data and no hidden imperative setup.

## Canonical Inputs

- `agent.manifest.yaml`: single source of truth for identity, runtime, capabilities, skills, knowledge, workflows, schedules, feature flags, observability, and validation.
- `contracts/required-secrets.yaml`: required secret references, scopes, injection paths, manual prerequisites, and verification checks.
- `policies/approval-gates.yaml`: non-removable approval and forbidden-action rules.
- `skills/*/SKILL.md`: bundled worker-readable methods for career-steward judgment and procedure.
- `workflows/*.yaml`: declarative workflow surfaces and state models.
- `schemas/agent.manifest.schema.json`: v1alpha1 schema and versioning contract.

## Generated Outputs

The reconciler generates these artifacts from the canonical inputs:

- runtime config
- Helm values
- ExternalSecret references
- schedule declarations
- image contents manifest

Generated artifacts are deployment inputs, not the source of truth.

## Runtime Contract

The v1 reference image contains:

- Hermes-compatible runtime entrypoint
- canonical `nousresearch/hermes-agent` runtime base
- manifest validator
- reconciler
- bundled skills
- workflow and policy manifests
- sim-mode career-steward loop
- conformance test runner
- schema files

The image does not contain real credentials, source-operator private tracker data, OAuth tokens, or deployment ownership.

## Workflow Contract

The career-steward loop is:

1. intake evidence
2. classify state
3. draft next action
4. require approval for external side effects
5. update private pipeline state
6. run privacy/public-safety validation
7. emit observability and audit records

The v1 sim mode must execute that loop using fake data only.

## Ability Contract

The agent derives abilities from declarations in layers:

- Manifest skill refs declare which bundled skills may be loaded.
- Skill files describe career-steward methods the worker reads into context.
- Workflow manifests bind skill-provided capabilities to recurring jobs and state models.
- Connectors and tools provide callable external capability behind secret references and policy gates.

Skills must not contain credential values or imperative setup. Any API call that needs credentials belongs in a connector/tool contract, not in prose hidden inside a skill.

## Compatibility

The schema is `agents.selamy.dev/v1alpha1` with semantic `x-versioning.schemaVersion`.

Backward-compatible changes may add optional fields and new enum values only when old manifests still validate and preserve behavior. Breaking changes require a major schema bump, migration plan, and changelog entry. Unknown fields are rejected to prevent accidental shadow configuration.

## Build Commands

```bash
make verify
make test
make sim
```

`make verify` is the required gate.
