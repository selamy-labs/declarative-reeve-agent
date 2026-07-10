# Contributing

Keep changes focused, preserve `agent.manifest.yaml` as the source of truth, and
run `make verify` before opening a pull request. Do not commit credentials,
private tracker data, or environment-specific deployment state.

## Architecture diagrams

Architecture diagrams MUST be updated in the same PR that changes the behavior
or spec they describe.

When a source or specification change has no diagram impact, add the
`no-diagram-impact` label and include a one-line justification in the pull
request body:

```text
Diagram impact: none - <reason>
```
