## Tasks

- [x] Update product docs and OpenSpec contracts for Coco-first visual hybrid
      evaluation.
- [x] Add model and config tests for optional expected outcome, hard
      evaluation, soft evaluation, path safety, old task compatibility, and
      `kind: "coco"`.
- [x] Implement task models, safe path validators, Coco profile kind, and
      editable model/export support.
- [x] Add hard evaluation tests for required paths, forbidden paths, validation
      requirement, snippet checks, score summaries, and sidecar artifacts.
- [x] Implement deterministic hard evaluation and wire it into the runner after
      diff/validation.
- [x] Add soft evaluation payload tests and implement payload-only artifact
      generation.
- [x] Extend local app API tests for load/save preservation, run plan flags,
      results summaries, and safe sidecar artifact reads.
- [x] Extend report/export tests for hard/soft fields and implement stable
      report/export summaries.
- [x] Extend frontend unit/E2E tests for Coco, expected outcome, hard/soft
      evaluation, run planning, and result review sections.
- [x] Add minimal `examples/coco-visual` files and docs links.
- [x] Run Python, frontend, OpenSpec, diff, and local-e2e verification gates.
