# Designer UI Simplification Design

## Goal

Reduce the local app's first-screen cognitive load for planners who only need
to configure test cases, compare `AGENTS.md`/`skills` context schemes, and save
manual feedback.

## Approach

Use one simple explanation, one three-step workflow, and progressive disclosure:

1. Keep the top explanation to one sentence: run the same test cases against
   different `AGENTS.md`/`skills` context schemes and compare local evidence.
2. Keep the main page focused on three actions: configure test cases, configure
   context schemes, then review results and leave feedback.
3. Show only required fields by default. Move secondary fields into advanced
   details blocks.

## UI Changes

- The guide band becomes compact and task-oriented.
- The test-case editor default view shows title, task instruction, expected
  result, acceptance points, and validation commands.
- Category, difficulty, expected files, hard checks, and feedback rubrics move
  under "高级验收设置".
- The context-scheme editor default view shows scheme name, description, and
  context files. Target paths and destructive controls remain available but are
  visually deemphasized.
- Results keep the scoring boundary visible, while detailed execution metrics
  stay behind collapsible panels.

## Non-Goals

- Do not remove YAML editing, hard checks, telemetry, exports, or existing
  schema fields.
- Do not add hosted services, public benchmarks, leaderboards, or automatic LLM
  judges.
- Do not change run semantics or artifact structure.

## Acceptance

- The first viewport makes the repository purpose clear in one sentence.
- A planner can find the three main actions without reading long explanatory
  copy.
- The test-case editor is shorter by default but still preserves all existing
  fields behind advanced controls.
- The context-scheme editor emphasizes `AGENTS.md` and `skills`.
- Results still explain that validation is evidence, not absolute truth.
- Frontend tests, E2E, and browser acceptance pass.
