# Approved semantic compiler implementation plan

Approved 2026-10-27. Implement in the current repository on the explicitly requested
`milestone-2-semantic-compiler` branch, preserving existing dependencies and data.
Design: [milestone-2-design.md](milestone-2-design.md).

- [x] Add failing v2 schema/evaluator tests: exact predicates and references,
  BEFORE/AFTER, overlap, missing/conflicting/repeated evidence, optional actions,
  required conditions and final states. Implement strict contracts and evaluation.
- [x] Add controlled-language compiler tests for the ten objective examples.
  Implement semantic compilation, with unsupported prose explicitly retained.
  Migrate the two reviewed fixture declarations; keep legacy schema parsing.
- [x] Add mocked Muse response contract tests; implement the disabled adapter
  interface, strict transport-schema conversion and safe response validation.
  Do not add paid dispatch without verified account access and cost bounds.
- [x] Add frontend tests for semantic program inspection, source labels and real
  temporal edges. Implement v2 display while retaining v1 audit rendering.
- [x] Integrate service/API: one compilation per upload after media validation,
  separate compiler/perception status, unchanged ledger and media boundaries.
- [x] Run all milestone checks, review requirements and code independently, fix
  regressions, and record exact validation and unavailable Docker/Meta access.
- [x] Update README/AGENTS/milestone docs and schema exports.
- Publication: commit, push and open an unmerged GitHub PR; verify remote state
  and checks before handoff. Remote results are recorded in the final handoff.

Tests precede production behavior changes. Use existing `.venv` tools if `uv`
cannot write its sandbox cache; never change persistent global configuration.
