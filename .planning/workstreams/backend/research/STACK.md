# Technology Stack — v0.9 Backend Hardening

**Project:** ЮрТэг v0.9
**Researched:** 2026-03-26
**Scope:** New capabilities only — redline DOCX, vector search, logprobs confidence, GBNF hardening

---

## Summary of Additions

No new major dependencies needed. All four features are achievable with the existing stack
plus targeted fixes. Zero new runtime packages required for logprobs and GBNF. One library
optional for DOCX (not required — current approach works). Vector model is sufficient as-is.

---

## Feature 1: Redline DOCX with Track Changes

### Current State

`services/version_service.py:generate_redline_docx()` already implements w:ins/w:del via
raw OxmlElement calls on top of python-docx. The structure is valid OOXML. Word and LibreOffice
open it and show tracked changes correctly.

### Known Gap

Current implementation diffs at sentence level (splits on `.!?`). This produces coarse
granularity: the entire sentence is marked inserted/deleted even if only one word changed.
For legal contracts this matters — a lawyer reviewing a redline wants word-level precision.

### Recommendation: Improve Granularity, No New Library

Do NOT add python-redlines (text/markdown output only, no DOCX) or Python-Redlines (requires
.NET Core 8, x86-only binary, archived dependency chain). Both are unsuitable.

The fix is purely algorithmic: replace sentence-level SequenceMatcher with word-level diff
inside each changed sentence block. The OxmlElement approach is correct and robust for this
use case. Change is ~30 LOC in the existing function.

**Specific improvements:**
- Two-pass diff: sentence-level grouping → word-level diff within replace blocks
- Run character-normalize before diff (strip extra whitespace, normalize dashes)
- Split `w:r` properly so each word-level change gets its own run, not the whole sentence

**No new install required.** python-docx already in stack.

### Confidence: HIGH — verified against open issues, library survey complete

---

## Feature 2: Vector Search for Versioning and Template Matching

### Current State

`services/version_service.py` uses `paraphrase-multilingual-MiniLM-L12-v2` (384D, 50+ languages)
with cosine similarity. Thresholds: 0.85 for version linking, 0.60 for template matching.
Embeddings cached in SQLite `embeddings` table. Works offline, no external calls.

### Is the Model Sufficient?

Yes. For the specific task — detecting whether two Russian legal documents are versions of
the same contract — semantic similarity at sentence/paragraph level is the goal, not
fine-grained legal reasoning. MiniLM-L12-v2 handles Russian well (it was trained on 50+
languages including Russian).

Multilingual-E5 or RuBERT would give marginally better Russian recall but add ~450MB weight
vs ~120MB for MiniLM. For a desktop app bundled as DMG/EXE this is not worth the tradeoff.

### Known Gap

The model's max sequence length is 128 tokens. Current code truncates to first 8000 characters
(`text[:8000]`). This is wrong — 8000 characters is roughly 1500-2000 tokens, so the model
silently truncates to 128 tokens (~500-600 characters). For a 50-page contract this means
only the preamble is embedded.

**Fix:** Use `model.encode(text[:3000])` (3000 chars ≈ 110-120 tokens, fits in window) OR
use `encode_multi_process` with chunking + mean pooling. The 3000-char truncation is safe
and matches what the model actually sees.

**No new library needed.** sentence-transformers already in stack.

### Confidence: HIGH — model card confirmed 128 token limit on HuggingFace

---

## Feature 3: Logprobs Confidence Scoring

### Current State

`providers/ollama.py:complete()` requests a plain text response. Confidence field is still
in the GBNF grammar and in the model prompt, meaning the model generates a confidence
number — which is unreliable (known issue, documented in CONCERNS.md).

The plan: remove `confidence` from GBNF/prompt, compute it from logprobs instead.

### llama-server Logprobs API

llama-server (llama.cpp) exposes an OpenAI-compatible `/v1/chat/completions` endpoint.
Logprobs are requested via standard OpenAI parameters:

```python
response = client.chat.completions.create(
    model="local",
    messages=messages,
    logprobs=True,       # enable logprob collection
    top_logprobs=5,      # top-5 alternatives per token (optional)
    temperature=0.05,
    max_tokens=512,
)
```

Response structure (OpenAI-compatible):
```
response.choices[0].logprobs.content[i].logprob  # float, log-probability of token i
response.choices[0].logprobs.content[i].token    # the token string
```

**Confidence computation:** Mean of exp(logprob) across all generated tokens gives mean
token probability. For structured JSON output with GBNF-constrained decoding, token
probabilities are higher on well-structured outputs (grammar forces legal tokens). A mean
token probability < 0.5 → low confidence; > 0.85 → high confidence.

**Integration point:** `providers/ollama.py:complete()` needs to return logprobs alongside
text. Options:
1. Change return type from `str` to a small dataclass `(content: str, logprobs: list[float] | None)`
2. Pass logprobs via `**kwargs` out parameter

Option 1 is cleaner but requires updating `LLMProvider.complete()` signature and all callers.
Option 2 is a safe incremental change — add `complete_with_logprobs()` to OllamaProvider only,
keep base interface unchanged. Confidence computation happens in `modules/postprocessor.py`.

**Note:** Logprobs are only available from llama-server (local Ollama provider). ZAI/OpenRouter
providers do not reliably expose logprobs — for those, confidence stays null or uses a heuristic
(e.g., field completeness ratio).

**No new library needed.** openai SDK already handles logprobs in response object.

### Confidence: MEDIUM — llama.cpp logprobs confirmed supported; exact response field
names verified against server README and discussion threads; haven't confirmed b5606
specifically exposes `response.choices[0].logprobs` (may need to test).

---

## Feature 4: GBNF Grammar Improvements

### Current State

`data/contract.gbnf` is a hand-written GBNF that constrains model output to a fixed JSON
schema. It works. Known issues:
- `confidence` field is still present (must be removed)
- Fixed field order forces the model to emit fields in exact sequence — if the model
  naturally wants to emit `date_end` before `date_start`, the grammar rejects it mid-sequence
- No optional field support — all fields must appear even if null

### What GBNF Supports

GBNF (llama.cpp) supports:
- Alternation via `|` — for nullable types like `str-or-null`
- Optional via `?` — for optional elements
- Repetition via `*`, `+`, `{m,n}`
- Character classes `[a-z]`
- Enums as string alternatives `"monthly" | "quarterly" | ...`

### Known Limitation: Field Order Must Be Fixed

GBNF grammars for JSON **require fixed key order** because the grammar is a context-free
sequence. The model must emit fields in the exact order defined in the grammar. This is a
fundamental constraint of constrained decoding — the grammar cannot enforce "this set of
keys in any order."

This is not a bug to fix — it is how GBNF works. The grammar must list fields in a single
canonical order, and the system prompt must instruct the model to follow that order.

### Recommended Changes to contract.gbnf

1. **Remove `confidence` field** — computed from logprobs, not generated by model
2. **Tighten date rule** — current `[0-1][0-9]` allows month `09` but also `00` and `19`;
   use `("0" [1-9] | "1" [0-2])` for months and `("0" [1-9] | [1-2] [0-9] | "3" [0-1])` for days
3. **Fix `number-or-null` for payment_amount** — current rule allows `-0.` which is technically
   valid JSON number but semantically wrong; add `positive-number` variant
4. **Add `contract_number` field** — frequently extracted by model but not in schema, causes
   the model to hallucinate or skip it; adding it reduces field-stuffing

**No new library. Grammar is a text file, changes are 10-15 lines.**

### JSON Schema → GBNF Auto-generation

llama.cpp ships a Python converter at `llama.cpp/examples/json_schema_to_grammar.py`. This
takes a Pydantic model schema and outputs GBNF. Worth using if the schema grows in complexity —
avoids hand-maintaining the grammar file. Not required for v0.9.

### Confidence: HIGH — GBNF documentation reviewed, grammar structure confirmed

---

## What NOT to Add

| Library | Reason to Skip |
|---------|----------------|
| python-redlines (houfu/redlines) | Outputs markdown/HTML only, no DOCX. Wrong tool. |
| Python-Redlines (JSv4) | Requires .NET Core 8, x86-only, archived dependency. Not viable for macOS/Windows DMG. |
| Aspose.Words for Python | Commercial license, ~$600/year. Overkill for track changes generation. |
| multilingual-e5-large | 450MB vs 120MB for MiniLM. Marginal Russian improvement, not worth DMG size increase. |
| RuBERT | Russian-only, breaks multilingual flexibility, heavier. |
| llama-cpp-python | We use llama-server binary, not the Python binding. Adding this creates duplicate inference stack. |
| faiss / chromadb | Vector store overkill for SQLite-backed embeddings at <10K documents per client. |

---

## Final Stack Delta for v0.9

**Zero new runtime packages.** All changes are code-level:

| What Changes | Where | Type |
|---|---|---|
| Remove `confidence` from GBNF | `data/contract.gbnf` | Grammar fix |
| Tighten date/number rules in GBNF | `data/contract.gbnf` | Grammar fix |
| Add `complete_with_logprobs()` to OllamaProvider | `providers/ollama.py` | Code addition |
| Compute confidence from logprobs | `modules/postprocessor.py` | Code change |
| Fix 8000-char → 3000-char embedding truncation | `services/version_service.py` | Bug fix |
| Upgrade redline diff to word-level | `services/version_service.py` | Algorithm improvement |

---

## Sources

- llama.cpp server README (logprobs, grammar): https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- llama.cpp GBNF grammar docs: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
- python-docx track changes issue (confirms no native API): https://github.com/python-openxml/python-docx/issues/340
- Python-Redlines limitations (.NET dependency): https://github.com/JSv4/Python-Redlines
- redlines library (text-only output): https://pypi.org/project/redlines/
- MiniLM-L12-v2 model card (128 token limit): https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- GBNF grammar structured output deep-dive: https://deepwiki.com/ggml-org/llama.cpp/8.1-grammar-and-structured-output
