# OCI Image Contents

## Decision

The v1 OCI image contains both the reference runtime payload and the reference reconciler tools. The image is a delivery artifact, not a deployment.

## Included

- Hermes-compatible entrypoint and runtime bootstrap hooks
- canonical `nousresearch/hermes-agent` runtime base
- `career_steward` Python reference package
- manifest validator
- reconciler
- sim-mode runner
- workflow manifests
- policy manifests
- schemas
- default fake fixtures for sim mode
- conformance test runner

## Excluded

- real credentials
- real OAuth tokens
- source-operator private data
- live browser profiles
- cluster-specific kubeconfig
- downstream secret-store values
- environment-specific deployment decisions

## Consumer Contract

Consumers pin published images by digest. The Helm chart mounts or embeds the selected manifest and wires declared secret references from the downstream environment.

## Verification

`make container-structure` builds the reference image layout under `generated/image-layout` and runs `image/container-structure-test.yaml` against its rootfs and image metadata. The tests prove required files, metadata, policy/config content, command wiring, and forbidden paths before artifact publication.

`make image-structure` applies the same structure spec to an actual Docker-built image from `image/Containerfile` when Docker and the canonical Hermes base image are available.
