# Feature Landscape: Backend Hardening

**Domain:** Legal document processing desktop app — backend subsystems
**Researched:** 2026-03-26
**Scope:** Redline DOCX, vector versioning, confidence scoring, GBNF, cleanup

---

## Context: What Already Exists

Before categorising features, it matters what's already partially built:

| Subsystem | Current State | Gap |
|-----------|--------------|-----|
| `generate_redline_docx()` | Sentence-level difflib → w:ins/w:del DOCX | Works for plain text; does not handle DOCX-to-DOCX (only string-to-string); no word-level granularity |
| `version_service.find_version_match()` | MiniLM-L12-v2 embeddings, cos-sim ≥ 0.85, caches in SQLite | Only searches by type+counterparty pre-filter; template matching uses same vectors but different threshold (0.60) |
| `review_service.review_against_template()` | difflib sentence diff → color-coded dict list | UI renders HTML colors; no DOCX export from template review path |
| `OllamaProvider.complete()` | Returns raw string; `logprobs=False` — confidence comes from model output only | Model-generated confidence is unreliable; real logprobs not requested |
| GBNF `contract_05b.gbnf` | Constrains all fields including `confidence` as `0.[0-9]+` float | `confidence` in grammar is the model's self-reported score — not actual logprobs |
| Validation L1-L5 | Structural + logical + AI-confidence + cross-archive checks | L3 specifically relies on model-reported `confidence` field — invalid once we switch to logprobs |

---

## Table Stakes

Features users (lawyers) expect in this category of tool. Absence makes the product feel broken or untrustworthy.

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| **Redline DOCX word-level granularity** | Industry standard: Draftable, Litera Compare, Word Compare all operate word-by-word, not sentence-by-sentence. Sentence-level diffs produce giant red/green blocks that are unusable in practice. | Medium | Replace difflib sentence split with word/token-level SequenceMatcher |
| **Redline from DOCX source files** | Lawyers compare actual DOCX files, not extracted strings. Current code takes `text_old: str` — you lose formatting context, headers, clause numbering. Comparison should extract text per-paragraph, then diff per-paragraph. | Medium | `python-docx` paragraph extraction + per-paragraph word diff |
| **Redline covers full document text** | Current `generate_redline_docx()` is called only for subject field in some paths. A real redline covers the full document body. | Low (wiring) | Existing function signature is correct; caller must pass full text |
| **Template review also exports DOCX redline** | `review_against_template()` produces a dict for UI display. Lawyers need to save/send the redline. Export to DOCX should be available from the template review flow too. | Low | Wire existing `generate_redline_docx()` into `review_service` |
| **Version auto-linking works across re-imports** | If a lawyer re-processes a folder after adding a v2 of a contract, the system must link them automatically. Currently works, but threshold 0.85 may be too strict for heavily negotiated contracts where text changed significantly. | Low (tuning) | Threshold calibration — consider 0.75 for same-counterparty+type candidates |
| **Confidence score reflects actual model certainty** | Displaying model-reported `confidence: 0.87` from GBNF output is meaningless — the model was forced to output a float, it's just inventing a number. Real confidence = logprobs of key extracted tokens. | High | llama-server `/v1/chat/completions` with `logprobs: true, top_logprobs: 5` |
| **Confidence shown per-field, not per-document** | Different fields have different extraction difficulty. `counterparty` is usually reliable; `date_end` often hallucinated. Per-field confidence lets the UI highlight exactly what to check. | High | Logprobs aggregation per output segment |
| **Dead code removed (L1-L5, Excel reporter)** | Unmaintained validation that depends on model self-reported confidence is actively misleading. Excel reporter is cloud-era artifact. Removal reduces cognitive overhead and test surface. | Low | Dependency audit before deletion |

---

## Differentiators

Features beyond table stakes that would make ЮрТэг meaningfully better than the competition for its specific use case (solo lawyer, local-first, Russian contracts).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **"Promote to template" from version history** | Any document in a version group can be promoted as the new canonical template for that contract type. Litera/Draftable don't have this — they're file-comparison tools, not document registries. | Medium | Needs UI affordance; backend is `mark_contract_as_template()` already exists |
| **Semantic template search (vector)** | When adding a new document, suggest the most relevant template automatically based on embedding similarity — not just `contract_type` string match. Already partially built (threshold 0.60), but not surfaced in UI. | Low (already built) | `match_template()` in `review_service` — just needs UI wiring |
| **Confidence ring / field-level amber highlighting** | UI shows which extracted fields are low-confidence (logprob-derived). Lawyer knows exactly where to manually verify. This directly addresses the CustDev finding: "недоверие к AI". | Medium | Requires logprobs implementation first |
| **Side-by-side version timeline** | For a contract group, show v1→v2→v3 as a timeline with a one-click diff between any two versions. This is the core document lifecycle view that generic redline tools don't offer. | Medium | `get_version_group()` exists; UI needs to call `generate_redline_docx(text_v1, text_vN)` |
| **Paragraph-anchored redline** | Diff is computed per paragraph (not whole document), so structural changes (new clauses, reordered sections) are identified separately from text changes within clauses. | High | Requires paragraph-level extraction from both source DOCXs |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Word-compatible comment annotations in redline** | `w:comment` XML is a separate complex subsystem. Not needed for v0.9 — lawyers just need to see what changed. | Use `w:ins`/`w:del` only; comments are v1.0+ |
| **Diffing PDF documents directly** | PDF has no semantic structure — you'd be diffing raw text blobs. Error-prone, unmaintainable. | Convert to text via pdfplumber first, then diff |
| **Custom embedding model fine-tuned on legal Russian** | Would require training data, GPU, months. MiniLM-L12-v2 multilingual is good enough for version matching at 0.85 threshold. | Stay on `paraphrase-multilingual-MiniLM-L12-v2`; consider `multilingual-e5-small` as an alternative if speed is a concern |
| **Real-time collaboration / shared redline review** | Requires server, auth, websockets. This is a local desktop app. | Single-user DOCX export is the collaboration primitive |
| **Logprobs for cloud providers (ZAI, OpenRouter)** | OpenRouter does not expose logprobs on all models. ZAI API may not support it. Implementing per-provider logprob parsing adds fragility. | Logprobs confidence only for `OllamaProvider` (llama-server); cloud providers fall back to model-reported confidence or fixed default |
| **Replacing GBNF with JSON mode / function calling** | llama-server supports both, but GBNF gives more control over enum values and date formats. Do not migrate to JSON mode — it loses enum constraints. | Improve GBNF by removing `confidence` field (move to logprobs) and adding `contract_number` field if needed |

---

## Feature Dependencies

```
logprobs in OllamaProvider
    → per-field confidence computation
        → remove `confidence` from GBNF output schema
            → remove L3 validation (depends on model-reported confidence)
                → simplify/remove L1-L5 validator

generate_redline_docx() word-level upgrade
    → wire into review_service template review path
        → UI "Download Redline" button in document card

paragraph-level extraction for DOCX-to-DOCX redline
    → version comparison uses real extracted text, not subject-only
        → side-by-side version timeline in UI

vector template matching (already exists)
    → promote-to-template from version group
        → semantic template suggestions on document processing
```

---

## MVP for v0.9 Recommendation

**Must ship (table stakes, blocks trust):**
1. Word-level granularity in `generate_redline_docx()` — current sentence-level is not usable
2. Wire full document text through redline (not just subject field)
3. Logprobs confidence via llama-server — remove model's self-reported confidence field from GBNF
4. Remove L1-L5 validator and Excel reporter — dead weight

**Should ship (differentiators, already 80% built):**
5. Template review path also exports DOCX redline
6. Surface vector template matching in UI (backend already complete)
7. Per-field confidence as amber highlights in document card UI

**Defer (too complex for v0.9):**
- Paragraph-anchored redline (High complexity, not blocking)
- Side-by-side version timeline (UI milestone, not backend)
- Promote-to-template from version group (nice to have, not MVP)

---

## Sources

- [Python-Redlines (JSv4) — GitHub](https://github.com/JSv4/Python-Redlines)
- [docx-revisions — GitHub](https://github.com/balalofernandez/docx-revisions) — read/write w:ins/w:del in python-docx
- [redlines — PyPI](https://pypi.org/project/redlines/) — simpler redline library
- [llama.cpp server README — logprobs API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [OpenAI Cookbook: Using logprobs](https://cookbook.openai.com/examples/using_logprobs)
- [Estimating LLM classification confidence with logprobs (2025)](https://ericjinks.com/blog/2025/logprobs/)
- [Draftable Legal — departures table as standard feature](https://www.draftable.com/draftable-legal)
- [Legal document similarity — sentence-transformers](https://github.com/malteos/legal-document-similarity)
- [GBNF grammar constrained decoding guide](https://www.aidancooper.co.uk/constrained-decoding/)
