# Reconciler Contract

## Role

The reconciler turns the declarative agent source into deployable artifacts. It never owns live deployment. Downstream infrastructure decides when generated artifacts are applied.

## Generated

Generated from `agent.manifest.yaml` and contracts:

- `runtime-config.yaml`
- `helm-values.yaml`
- `external-secrets.yaml`
- `schedules.yaml`
- `image-manifest.json`

## Validated

The reconciler validates:

- manifest schema and versioning
- workflow references exist
- skill references exist
- bundled skill frontmatter matches manifest refs
- workflow capabilities are covered by declared skill `provides` entries
- schedules reference known workflows
- connector secret references are declared
- secret contracts contain remote key, injection target, and verification
- approval gates exist for all external side effects
- forbidden actions include secret commits and raw private publication
- mutable and immutable runtime zones are declared
- required docs and ADRs exist
- capability parity inventory maps every capability to a declarative surface and test

## Drift Ownership

Source drift is owned by this repo. Generated artifact drift is owned by the reconciler. Live environment drift is owned by the downstream infrastructure repo and its GitOps controller.

If live state differs from generated artifacts, the downstream repo must either update its pinned artifact version or reconcile its environment. The source/spec repo must not mutate live clusters directly.

## Failure Mode

The reconciler fails closed. Missing secrets, missing skills, missing approval gates, unknown workflow references, and unfinished docs block verification before artifact publication.
