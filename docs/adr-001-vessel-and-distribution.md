# ADR 001: Vessel And Distribution Model

## Status

Proposed.

## Context

The repository is not itself the deployed agent. It is the source specification for a career-steward agent.

The repository should be deployable in the sense that it produces deployable artifacts, but it should not assume ownership of any particular user's infrastructure. A downstream environment should be able to consume the artifact and wire it into its own Kubernetes, GitOps, secret store, and policy stack.

This creates three distinct vessels:

1. **Source vessel:** the repository, including `agent.manifest.yaml`, schemas, workflows, policies, scripts, tests, and docs.
2. **Delivery vessel:** an OCI image containing the reconciler/runtime payload for the declared agent.
3. **Deployment vessel:** a Helm chart or equivalent adapter that wires the image, manifest, secrets, schedules, PVCs, and policy into a target infrastructure repo.

## Decision

Use the repository as a source/specification package that produces versioned artifacts.

Primary artifacts:

- an OCI image pinned by digest
- a Helm chart packaged as an OCI artifact
- generated schema/docs/conformance outputs

Downstream infrastructure should consume pinned artifacts:

```yaml
agentImage:
  repository: ghcr.io/example/career-steward-agent
  digest: sha256:...

agentChart:
  repository: oci://ghcr.io/example/charts/career-steward-agent
  version: 0.1.0
```

The source repo may also be a Bazel module, but Bazel source consumption is an advanced path, not the default deployment contract.

## Bazel Position

Bazel is useful as the internal build and verification graph:

- validate manifests and schemas
- run tests
- package scripts and skills
- produce an OCI image
- render/package Helm artifacts
- generate conformance fixtures
- make builds reproducible from source

However, Bazel should not be the only consumption mechanism. A downstream repo that merely wants to run a career-steward agent should not need to become a Bazel workspace or depend on a source checkout as its deployment primitive.

Preferred shape:

```text
//agent:manifest_validate
//agent:image
//agent:helm_chart
//agent:image_structure_test
//agent:conformance_tests
```

CI runs those targets. Release automation publishes the image and chart.

If this repository adopts Bazel, image construction should use `rules_oci` or an equivalent OCI-native rule set. The current `make image-structure` target is the v1 non-Bazel equivalent of an image-build plus image-structure-test target; it should become part of the Bazel graph rather than remaining an external shell-only check.

## CI/CD Boundary

This repository should have continuous integration and continuous delivery of artifacts.

It should not continuously deploy into a user's environment by default.

- **CI:** schema validation, lint, tests, secret scan, policy checks, image build, chart render, kubeconform, SBOM/vulnerability scan.
- **CD:** publish immutable OCI image and Helm chart artifacts on tag or approved release.
- **Deployment:** owned by downstream infrastructure repos, which pin the image digest/chart version and reconcile through their own GitOps path.

This keeps the agent reproducible without collapsing source, package, and deployment ownership into one repo.

## Helm Position

Helm is still valuable, but not as the source of truth for the agent's behavior.

Helm is the Kubernetes packaging adapter. The source of truth is the agent manifest plus workflow/policy/secret contracts. The chart should be generated from, or validated against, that manifest.

## Consequences

- Users can inspect the repo as a complete agent spec.
- Users can deploy from standard OCI/Helm artifacts without adopting Bazel.
- Advanced users can use Bazel directly for hermetic builds and source-level composition.
- Downstream infra remains in control of secrets, cluster policy, release timing, and rollbacks.
- The agent repo can ship frequently without mutating any live deployment.

## Pushback On Alternatives

### Repository-As-Deployment

Making this repo directly deploy itself into environments couples the agent product to one infrastructure topology. That is wrong for a reusable career-steward agent.

### Bazel-Only Consumption

Depending on a Bazel Git target can work for internal mono/federated repos, but it forces every consumer to accept Bazel toolchains, source-level build latency, and source dependency coupling. An image digest is a cleaner contract for most deployments.

### Helm-As-Source-Of-Truth

A Helm chart alone can describe Kubernetes objects, but it is too low-level to describe the agent's semantic capabilities, approval gates, workflows, knowledge boundaries, and required accounts. Helm should package those declarations, not replace them.
