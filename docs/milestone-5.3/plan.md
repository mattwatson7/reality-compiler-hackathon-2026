# Milestone 5.3 work plan

**Goal:** Supply exact acquisition advice and reproducible offline evaluation while
preserving the completed generated-input submission and paid controls.

**Architecture:** Reuse existing ingestion, source-PTS mapping, expectation freeze,
deterministic import and captured-evidence replay. Add research and audit documents
only; leave application providers and public delivery authorization unchanged.

**Stack:** Existing Python/OpenCV/FFmpeg, pytest/Ruff/mypy, React/Vitest/Vite;
authenticated GitHub/Hugging Face connectors and official publisher web pages.

- [x] Inspect existing recording guide, originals, provenance and camera results.
- [x] Research original dataset publishers; select only exact verified files.
- [x] Record the absence of a verified controlled trio and shortest capture procedure.
- [x] Document metadata/hash preservation, PTS inspection, annotation freeze and import.
- [x] Audit preserved demo/source archive and runtime hashes; read ledger without writes.
- [x] Run existing project checks; record results and external access limits.
- [x] Leave camera capture, human annotation and publication/submission decisions explicit.

All work is performed inline. No new dependencies or model dispatch are necessary.
