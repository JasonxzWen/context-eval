# Changelog

## Unreleased

- Add the initial SDD/TDD development roadmap.
- Add runner correctness improvements, strict validation, task filters, fixture
  examples, dry-run previews, init, trials, inspect/compare commands, and a
  local static UI generator.
- Modernize package metadata to use SPDX license metadata instead of
  table-form license metadata.
- Document Python and platform support expectations for release readiness.
- Add automated package artifact inspection for wheel and sdist release checks.
- Add a release-state check for hidden local release blockers.
- Add development plan status reconciliation and an active backlog handoff that
  names validation command timeout defaults as the next planned work.
- Add validation command timeout defaults with `evaluation.timeout_seconds` and
  `task.validation.timeout_seconds`.
- Replan the development roadmap around larger capability PRs and replace the fine-grained active backlog with six capability epics.
- Clarify that Ralph stories remain SDD/TDD units inside a capability PR.
- Add a release preparation entrypoint with a manual tag and publish checkpoint.
- Specify a local-e2e CI smoke and test taxonomy as the next pre-feature
  capability gate.
