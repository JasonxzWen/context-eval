# Concepts

context-eval compares context variants under controlled engineering conditions.
It is designed for coding agent workflows where the same repository, task, and
agent command should be run against different context assets.

## Repo

The repo is the target Git repository being evaluated. The MVP supports local
paths only. context-eval does not install dependencies or prepare build
environments for the target repository.

## Task

A task is a prompt plus optional metadata and validation commands. A task can
pin a specific `repo_ref`; otherwise the configured `repo.base_ref` is used.

## Context Variant

A variant is a named context environment. It can overlay files or directories
such as `AGENTS.md`, docs, rules, or skills into the temporary workspace before
the agent runs.

## Case

A case is one task run against one variant. Each case receives its own temporary
workspace and produces logs, a prompt file, a patch, diff stats, validation
results, and one JSONL result row.

## Confidence

Confidence describes the strength of the evaluation signal, not absolute
correctness. Validation commands improve confidence, but human review may still
be required.
