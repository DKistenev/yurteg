# Research Summary: v0.9 Backend Hardening

**Project:** ЮрТэг v0.9
**Domain:** Legal document processing desktop app — backend subsystems
**Researched:** 2026-03-26
**Confidence:** HIGH (direct codebase analysis + verified external sources)

---

## Executive Summary

ЮрТэг v0.9 is a backend hardening milestone with four distinct workstreams: word-level redline DOCX generation, logprobs-based confidence scoring, GBNF grammar cleanup, and surgical removal of dead code (validator + Excel reporter). The core finding across all four research areas is that the foundation is already correct — python-docx OxmlElement approach for track changes is valid OOXML, MiniLM-L12-v2 is adequate for Russian contract similarity, and llama-server does expose logprobs — but each subsystem has a specific known bug or gap that blocks production quality. None of these require new dependencies. All changes are code-level within existing files.

The recommended approach is to sequence the work in dependency order: delete dead code first (unblocks clean controller.py), then implement logprobs (unblocks real confidence), then improve redline and vector caching in parallel, then wire everything to the UI. This order avoids the most dangerous failure modes: importing from deleted modules causes total app startup failure, and logprobs must be implemented before removing the validator's L3 confidence check.

The single most critical architectural risk is the GBNF/logprobs incompatibility: in llama-server b5606, grammar-constrained decoding makes logprobs meaningless because token probabilities are computed before grammar filtering. This is not a bug that will be fixed — it is a design choice in llama.cpp. The team must either use grammar via the per-request body (not server flag) to allow toggling, or implement a two-pass approach: one grammar-constrained call for output structure, one unconstrained call for confidence measurement.

---

## Key Findings

### Recommended Stack

Zero new runtime packages needed for v0.9. All four features are achievable through algorithm improvements and bug fixes in existing code. The existing python-docx OxmlElement approach for track changes is the correct architecture — third-party redline libraries are either text-only (redlines/houfu) or require .NET Core 8 runtime (Python-Redlines/JSv4), making both unsuitable for a macOS/Windows DMG build. The existing sentence-transformers/MiniLM-L12-v2 embedding stack is sufficient for Russian contract version matching.

**Core technologies — changes only:**
- `python-docx`: redline generation via w:ins/w:del — already correct, needs word-level algorithm (~30 LOC change)
- `sentence-transformers` + MiniLM-L12-v2: version and template matching — sufficient, needs 8000→3000 char truncation fix
- `llama-server` OpenAI-compatible API: logprobs via `logprobs=True` parameter — supported, incompatible with server-level grammar flag
- `data/contract_05b.gbnf`: structured output constraints — needs `confidence` field removal, date/number rule tightening, `contract_number` field addition

**What NOT to add:** python-redlines, Python-Redlines, Aspose.Words, multilingual-e5-large, RuBERT, llama-cpp-python, faiss, chromadb — all surveyed and rejected with rationale in STACK.md.

### Expected Features

**Must have (table stakes — blocks trust without these):**
- Word-level granularity in `generate_redline_docx()` — sentence-level is not usable for legal review, industry standard is word-by-word
- Real confidence from logprobs — model self-reported `confidence: 0.87` from GBNF output is invented; lawyers see false precision
- Remove `validator.py` and `reporter.py` — dead weight that actively misleads (L3 validation depends on model-reported confidence, which is invalid)
- Wire full document text through redline path — current implementation only diffs subject field in some call paths

**Should have (differentiators, already 80% built):**
- Template review path exports DOCX redline — backend function exists, not wired to review flow
- Surface vector template matching in UI — `match_template()` in `review_service` works, not exposed
- Per-field confidence as amber highlights — requires logprobs implementation first

**Defer (too complex for v0.9):**
- Paragraph-anchored redline (High complexity — requires paragraph-level DOCX extraction from both source files)
- Side-by-side version timeline (UI milestone, not backend)
- Promote-to-template from version group (nice to have, not blocking)
- Word comment annotations (`w:comment`) — separate XML subsystem, v1.0+

### Architecture Approach

The architecture change is subtractive, not additive. The pipeline shrinks: `AI Extractor → PostProcessor → Validator → Database` becomes `AI Extractor (+logprobs) → PostProcessor → Database`. The validator's structural guarantees move to GBNF (which already enforces them), and the validator's confidence check moves to logprobs. Zero new modules; the only new file is a revised `data/contract_v2.gbnf`.

**Modified components and their new responsibilities:**
1. `providers/ollama.py` — add `return_logprobs=False` parameter; compute `confidence = exp(mean(logprobs))` from first ~20 response tokens
2. `services/version_service.py` — two fixes: word-level diff (two-pass SequenceMatcher), and embedding truncation 8000→3000 chars
3. `services/review_service.py` — add `template_embeddings` caching; fix `mark_contract_as_template()` to use full document text, not just subject
4. `controller.py` — remove validator and reporter import/call sites (surgical, exactly 3 references for validator, 2 for reporter)
5. `modules/database.py` — migration v8: `template_embeddings` table; add `delete_contracts(ids)` method
6. `data/contract_v2.gbnf` — remove `confidence` field, tighten date/number rules, add `contract_number`

**Dependency order (critical):** reporter removal → validator removal → logprobs in provider → confidence in extractor → redline improvement → embedding cache → UI wire-up.

### Critical Pitfalls

1. **GBNF + logprobs are incompatible in b5606** — grammar filtering happens after logprob computation, so grammar-forced tokens report near-zero confidence. Use grammar via per-request body (`grammar` field in JSON), not `--grammar-file` server flag, which allows toggling per-request. Test with curl before any code is written.

2. **Deleting validator.py crashes the app on startup** — `controller.py` has eager import-level `from modules.validator import validate_batch, validate_metadata`. Remove call sites in controller.py first, then delete the file, in the same commit as the test patches. Do not delete the file without updating the importer.

3. **Reporter removal breaks stats dict** — `stats["report_path"]` propagates through `pipeline_service.py`, UI callbacks, and `test_controller.py` patches. Full consumer search via grep required before removing. Safe approach: keep `stats["report_path"] = None` in the return dict.

4. **python-docx redline XML fails Word validation silently** — runs inside `w:ins`/`w:del` need `w:delText` (not `w:t`) for deleted content, and matching `rPr`. LibreOffice accepts malformed XML; Word 365 shows "repair document" dialog and strips track changes. Validate by unzipping generated DOCX and inspecting `word/document.xml`. Test in Word, not only LibreOffice.

5. **Embedding text truncation bug produces wrong embeddings** — current `text[:8000]` passes ~1500-2000 tokens to a model with 128-token limit. Model silently truncates to the first 600 characters. Fix: `text[:3000]` (~110-120 tokens). For 50-page contracts this currently means only the preamble is embedded.

---

## Implications for Roadmap

Based on dependency analysis in ARCHITECTURE.md and pitfall sequencing in PITFALLS.md, the following 4-phase structure is recommended.

### Phase 1: Cleanup (Снос)

**Rationale:** Delete dead code first. Removes the import chains that would break if done mid-sequence. Frees controller.py to be edited cleanly once in Phase 2. Also removes misleading test coverage that currently masks problems.

**Delivers:** Smaller codebase, no dead imports, no pandas/openpyxl dependency, clean controller.py, test suite reduced to only live code.

**Addresses:** Reporter removal (table stakes), validator removal (table stakes).

**Avoids:**
- Pitfall 2 (controller.py ImportError) — validator call sites removed before file deletion
- Pitfall 3 (stats dict KeyError) — report_path set to None before reporter deleted
- Pitfall 9 (dead test patches) — test_reporter.py and reporter patches in test_controller.py deleted in same commit

**Critical pre-step:** grep for all consumers of `report_path`, `generate_report`, `validate_metadata`, `validate_batch` before touching any file.

**Notes:** Preserve `_validate_inn` INN checksum logic and hallucination detection from validator — move to `postprocessor.py` before deleting the module (Pitfall 10). Keep `validation_status` column in SQLite, write `"ok"` unconditionally (Pitfall 11).

---

### Phase 2: GBNF + Logprobs

**Rationale:** Depends on Phase 1 (clean controller.py). Core architectural change — replaces invented confidence with real confidence. Must happen before any UI work on confidence display.

**Delivers:** Real logprobs-based confidence score from OllamaProvider. Removed `confidence` field from GBNF. Tighter grammar rules for dates and numbers. `contract_number` field in schema.

**Addresses:** "Confidence reflects actual model certainty" (table stakes), "Per-field confidence" (differentiator).

**Avoids:**
- Pitfall 1 (GBNF/logprobs incompatibility) — use grammar via per-request `grammar` field, not server `--grammar-file`; test with curl first
- Pitfall 8 (logprobs API shape in b5606) — standalone curl test against running server before any code; keep `temperature=0.05`, never 0.0

**Affected files:** `providers/base.py`, `providers/ollama.py`, `providers/zai.py`, `providers/openrouter.py`, `modules/ai_extractor.py`, `data/contract_v2.gbnf`

**Decision required at planning time:** Two-pass vs. single-pass logprobs (one grammar call for structure + one unconstrained call for confidence, or grammar via body parameter only). This is the most consequential technical decision in v0.9.

---

### Phase 3: Redline + Vector

**Rationale:** Independent of Phase 2 (can start in parallel for separate developers, but sequentially these come after cleanup). Groups the two service-layer improvements that share a migration (database v8).

**Delivers:** Word-level redline DOCX (usable by lawyers). Fixed embedding truncation (correct version matching). Cached template embeddings (performance). Fixed `mark_as_template` (full document text, not just subject).

**Addresses:** Word-level granularity (table stakes), version auto-linking accuracy, "Promote to template" (differentiator, backend half).

**Avoids:**
- Pitfall 4 (Word repair dialog) — validate XML structure; test in Word before marking phase done; add round-trip test (generate → parse → assert w:ins exists)
- Pitfall 5 (wrong similarity threshold) — add date-range guard alongside threshold; log all linking decisions for review
- Pitfall 6 (90MB model download mid-pipeline) — confirm model already pre-downloaded in setup flow; add offline fallback

**Affected files:** `services/version_service.py`, `services/review_service.py`, `modules/database.py` (migration v8)

---

### Phase 4: UI Wire-up

**Rationale:** Final phase; depends on all prior phases. Backend is complete — this phase connects implemented-but-unwired functions to the UI.

**Delivers:** "Download Redline" button from template review. "Mark as Template" button on document card. Bulk delete (with DB cascade). "Open in Finder/Word" native file open. Per-field amber confidence highlights.

**Addresses:** Template review exports DOCX redline (should have), vector template matching surfaced in UI (should have), per-field confidence highlights (should have).

**Avoids:**
- Pitfall 7 (provider import chain breaks if archiving) — keep ZAI/OpenRouter files in place, mark deprecated in comments only

**Affected files:** `app/pages/document.py`, `app/components/bulk_actions.py`, `modules/database.py` (`delete_contracts()` method)

---

### Phase Ordering Rationale

- Phase 1 before Phase 2: validator deletion and reporter deletion change controller.py — better to do this once cleanly than patch it multiple times
- Phase 2 before Phase 4: confidence UI requires logprobs implementation; rendering `null` confidence during Phase 4 would require a second UI pass
- Phase 3 parallel-capable with Phase 2: redline and vector changes touch different files than logprobs changes; can be developed concurrently by two developers
- Phase 4 last: all backend capabilities must exist before UI wire-up; avoids building UI for half-working features

### Research Flags

Phases needing deeper research or pre-implementation validation:

- **Phase 2:** Logprobs API behavior in llama-server b5606 must be validated with a standalone curl test before any code is written. The grammar-via-body-field approach must be verified against the server's `/v1/chat/completions` endpoint documentation. This is the highest-risk technical decision in v0.9.
- **Phase 3 (redline):** python-docx Word compatibility requires a manual test with an actual Word installation. The XML structure for `w:ins`/`w:del` with matching `rPr` is not well-documented; the existing code has a known structural issue (Pitfall 4) that requires hands-on verification.

Phases with standard patterns (no additional research needed):

- **Phase 1:** Deletion and cleanup — deterministic. Grep-first, delete-second approach is well-established.
- **Phase 3 (vector):** Text truncation fix and embedding caching are straightforward implementation tasks. Model card confirms 128-token limit; fix is a one-line change.
- **Phase 4:** UI wire-up tasks are small and well-scoped. No external API or library uncertainty.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new packages confirmed. All library alternatives surveyed and rejected with clear rationale. MiniLM model card verified. |
| Features | HIGH | Direct codebase analysis — all feature gaps identified against live code, not assumptions. Dependencies validated. |
| Architecture | HIGH | All file references, line numbers, and import chains verified against actual source files. Component boundaries are clear. |
| Pitfalls | MEDIUM | Critical pitfalls 1 and 4 (GBNF/logprobs, Word XML compatibility) are MEDIUM confidence — based on llama.cpp architectural documentation and OOXML schema behavior, not b5606-specific testing. Require validation before implementation. |

**Overall confidence:** HIGH, with two specific MEDIUM areas requiring pre-implementation curl/Word testing.

### Gaps to Address

- **GBNF/logprobs interaction in b5606 specifically:** The incompatibility is documented architecturally in llama.cpp, but must be confirmed against the exact running build before the Phase 2 implementation plan is finalized. Run the curl test from Pitfall 8 prevention steps as the first action of Phase 2 planning.
- **Word 365 compatibility of existing redline XML:** The current `generate_redline_docx()` may already produce valid output — or may not. Test before committing to the fix scope. If Word accepts the current output, Phase 3 redline work is narrower than estimated.
- **Logprobs confidence calculation method:** Two approaches documented (mean exp(logprob) vs. min exp(logprob) vs. first-N-tokens only). The right choice depends on empirical testing against the model. Defer this decision to Phase 2 implementation.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `controller.py`, `modules/validator.py`, `modules/reporter.py`, `services/version_service.py`, `providers/ollama.py`, `modules/ai_extractor.py`, `services/review_service.py`, `services/llama_server.py` — all files read directly
- MiniLM-L12-v2 model card (HuggingFace): confirms 128-token max sequence length
- llama.cpp server README: logprobs API parameters, `/v1/chat/completions` schema
- llama.cpp GBNF grammar documentation: field ordering constraints, supported syntax

### Secondary (MEDIUM confidence)
- llama.cpp GitHub issues and discussions: grammar + logprobs interaction behavior in b5606
- OOXML schema behavior: `w:ins`/`w:del` structure, `w:delText` vs `w:t` requirement, `rPr` inheritance
- python-docx GitHub issue #340: confirms no native track changes API

### Tertiary (LOW confidence / needs validation)
- Draftable Legal feature set as industry standard reference for redline granularity expectations
- OpenAI Cookbook on logprobs: applied to llama-server by analogy

---

*Research completed: 2026-03-26*
*Ready for roadmap: yes*
