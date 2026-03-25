# Domain Pitfalls: v0.9 Backend Hardening

**Domain:** Adding redline DOCX, vector versioning, logprobs confidence to existing Python legal doc app
**Researched:** 2026-03-26
**Stack:** Python 3.10+, NiceGUI, SQLite, llama-server b5606, python-docx, sentence-transformers

---

## Critical Pitfalls

### Pitfall 1: GBNF Grammar Breaks logprobs

**What goes wrong:** llama-server grammar-constrained generation (--grammar-file) and logprobs are incompatible in llama.cpp b5606. When `--grammar-file` is active server-side, token probabilities are computed *before* grammar filtering is applied. The logprobs values reflect raw model distribution over *all* tokens, not the distribution over grammar-valid tokens. Result: a token forced by grammar to be the only valid choice can have logprob of -12.0 (very "uncertain"), while a forbidden token gets -0.1 ("certain").

**Why it happens:** Grammar is a post-sampling filter in llama.cpp. The model predicts, grammar rejects invalid tokens and forces resampling, but logprobs are reported from the unconstrained distribution. This is a known architectural choice, not a bug — there is no fix at the llama-server level in b5606.

**Consequences:** `metadata.confidence` computed from logprobs while grammar is active will be systematically wrong — often the opposite of actual model certainty. JSON fields like date formats get forced to correct shape by grammar but report near-zero confidence because the raw model was uncertain about them. UI shows "low confidence" on correctly-extracted dates and "high confidence" on hallucinated free-text fields.

**Prevention:**
- Make logprobs a separate API call *without* grammar, on the same input
- Or: run two requests — first with grammar (for output), second without grammar and `max_tokens=1` just to sample confidence
- Or (simpler): abandon logprobs-as-confidence entirely; compute field-level confidence heuristically from postprocessor signals already in `sanitize_metadata()`
- Do not pass `--grammar-file` to the llama-server process if logprobs are needed from that session; use two separate server instances or grammar via the API body (`grammar` field in JSON body) which can be toggled per-request without restarting the server

**Detection:** Confidence scores are bimodal — either very high or very low with nothing in between. Dates extracted perfectly all score < 0.3.

**Phase:** Address in the GBNF + logprobs phase before touching the validator.

---

### Pitfall 2: Removing Validator Leaves Broken Contract in controller.py

**What goes wrong:** `validate_metadata` and `validate_batch` are imported at the top of `controller.py` (lines 26, 334) and called in the pipeline. If you delete `modules/validator.py` or remove the functions without updating the controller, the app crashes on import — *before any document is processed*. The 268 tests include `test_controller.py` which patches `controller.validate_metadata` and `controller.validate_batch` — those patches become `AttributeError` after removal.

**Why it happens:** Python resolves import-level names eagerly. The `from modules.validator import validate_batch, validate_metadata` at the top of controller.py will raise `ImportError` the moment the module is loaded, breaking startup.

**Consequences:** Total app failure. Not a graceful degradation.

**Prevention:**
- Before deleting validator: replace all call sites in controller.py with pass-through stubs or remove them
- Audit call sites: `grep -n "validate_metadata\|validate_batch\|from modules.validator" controller.py` — there are exactly 3 references
- Update `test_controller.py`: remove the two `patch("controller.validate_metadata", ...)` and `patch("controller.validate_batch", ...)` lines; replace with correct assertions
- The `validation_status` column in SQLite is still needed by the UI (status badges) — keep writing it even without L1-L5 logic; just default to `"ok"` or derive from logprobs confidence

**Detection:** `ImportError` on app start after validator deletion.

**Phase:** Do not delete validator until controller.py and test_controller.py are both updated in the same commit.

---

### Pitfall 3: Reporter Removal Breaks stats dict and test_reporter.py

**What goes wrong:** `controller.py` line 342 calls `generate_report()` and stores result in `stats["report_path"]`. The pipeline service, UI pages, and tests all read `stats["report_path"]`. Removing reporter without updating all consumers causes `KeyError` in pipeline callbacks and broken UI state.

**Why it happens:** `report_path` is part of the documented return contract of `process_archive()`. It propagates to `on_progress` notifications and the UI shows "отчёт создан" toast on completion.

**Consequences:**
- `test_reporter.py` (entire file) becomes dead test code — not a crash, but misleading green
- `test_controller.py` patches `controller.generate_report` — becomes `AttributeError` after removal
- UI pages that display report_path will either crash or show `None`
- `services/pipeline_service.py` likely reads `report_path` from stats — needs auditing

**Prevention:**
- Keep `stats["report_path"]` in the return dict, just set it to `None` always
- Or replace with a different export signal (e.g., `stats["export_path"]`) and update all consumers
- Delete `test_reporter.py` in the same PR as reporter removal
- Search: `grep -rn "report_path\|generate_report" app/ services/` before removing

**Detection:** `KeyError: 'report_path'` in pipeline callbacks; or silent `None` that breaks UI toast.

**Phase:** Reporter removal must be done with a full search for all consumers before the commit.

---

### Pitfall 4: python-docx Track Changes Not Rendered by Word/LibreOffice

**What goes wrong:** The current `generate_redline_docx()` in `version_service.py` (lines 231-306) constructs `w:ins` and `w:del` XML elements manually. This approach has a compatibility trap: the run element appended inside `w:ins` must have its `rPr` (run properties) element as a child of `w:ins`, not of `w:r`, to satisfy the OOXML schema. LibreOffice accepts malformed track-changes XML silently; Word (365/2019) will show "repaired document" dialog and strip the changes entirely.

**Specific bug in existing code:** Lines 271-276 — `_add_inserted_run` creates a run via `para.add_run(text)`, removes it from its parent, then appends `run._r` inside `ins_el`. This works for the raw bytes but loses the run's `rPr` (formatting). More critically: if the paragraph already has `rPr` at the paragraph level, Word requires the run inside `w:ins` to also have a matching `rPr`. Without it, Word considers the insertion malformed.

**Consequences:** The redline DOCX opens in Word with "We found a problem... we'll try to repair it" — track changes are silently stripped. Looks like a normal document with no markings.

**Prevention:**
- After generating the DOCX bytes, validate the XML: unzip the bytes (it's a ZIP), parse `word/document.xml`, check that every `w:ins`/`w:del` element has a valid `w:id` attribute (unique across the document) and that child runs use `w:delText` inside `w:del` (not `w:t`)
- Use `w:rPr` with `w:rStyle val="Insertion"` or `w:rStyle val="Deletion"` — Word uses these built-in character styles to color tracked changes
- The revision ID counter (`_rev_counter`) must be globally unique per document — the current implementation resets per `generate_redline_docx()` call, which is correct, but IDs must be integers (not strings that look like integers) — the current `str(next(_rev_counter))` produces strings; the `w:id` attribute in OOXML schema accepts `xsd:int`, so this is technically correct but verify Word does not reject it

**Detection:** Open generated DOCX in Word — if it shows a repair dialog, the XML is invalid. Use `python -c "import zipfile, sys; z=zipfile.ZipFile(sys.argv[1]); print(z.read('word/document.xml')[:2000].decode())"` to inspect raw XML.

**Phase:** After implementing redline, test with actual Word (not just LibreOffice). Add a round-trip test: generate → parse XML → assert `w:ins` elements exist and have `w:id`.

---

## Moderate Pitfalls

### Pitfall 5: Vector Similarity Threshold 0.85 Causes Both False Positives and False Negatives

**What goes wrong:** `VERSION_LINK_THRESHOLD = 0.85` in `version_service.py` was set without empirical validation on actual legal documents. The `paraphrase-multilingual-MiniLM-L12-v2` model (384-dim) trained on paraphrase pairs has a different similarity distribution than Russian contract text. Two contracts of the same type (e.g., two different NDA templates) can score 0.87+ — causing unrelated documents to be merged into one version group. Meanwhile, a genuine v1→v2 revision where only one clause changed may score 0.82 — falling below threshold and creating a spurious new group.

**Why it happens:** The model's similarity scores are not calibrated for the "same contract, different version" task. The current candidate pre-filter (same `contract_type` AND same `counterparty`) partially helps but does not prevent false positives when counterparty names slightly differ (e.g., "ООО Альфа" vs "ООО «Альфа»").

**Prevention:**
- Add a second guard: only consider two documents as versions if `date_signed` difference is < 3 years (configurable)
- The pre-filter already uses exact string match on `counterparty` — this is good but fragile (normalization issues); ensure counterparty is normalized before comparison (strip quotes, lowercase, strip "ООО/АО" variants)
- Log all linking decisions with similarity score to a debug log; review after a real 50-document test
- Consider raising threshold to 0.90 with the date-range guard — reduces false positives at acceptable false-negative cost

**Detection:** Multiple unrelated documents appearing in the same version group in the UI.

**Phase:** Vector versioning phase. Add a `--dry-run` mode that prints proposed links without committing them.

---

### Pitfall 6: sentence-transformers Downloads 90MB Model on First Run Without User Awareness

**What goes wrong:** `get_embedding_model()` lazily loads `paraphrase-multilingual-MiniLM-L12-v2` via `SentenceTransformer(EMBEDDING_MODEL)`. This triggers a ~90MB download from HuggingFace on first call — during document pipeline processing, while the user is watching a progress bar. The download is synchronous (blocks the thread), takes 15-60 seconds on slow connections, and has no progress indication.

**Consequences:** Pipeline appears frozen mid-way through processing. No timeout — if HuggingFace is unreachable (e.g., corporate firewall), the call hangs indefinitely. This is especially problematic on the offline-first desktop app where users expect fully local operation.

**Prevention:**
- Download the embedding model during the same "model setup" flow as llama-server — in `LlamaServerManager.ensure_model()` or a parallel `ensure_embedding_model()` call
- Add `on_progress` callback to the embedding model download; show it in the onboarding wizard
- Cache path: `~/.yurteg/sentence-transformers/` — check for existence before calling `SentenceTransformer()`
- Fallback: if model not available (offline), skip vector versioning entirely with a warning rather than hanging

**Detection:** Pipeline progress bar freezes at "AI-анализ договоров..." for 30+ seconds on first run.

**Phase:** Address in the setup/onboarding phase, before vector versioning goes live.

---

### Pitfall 7: Archiving Cloud Provider Code While Keeping Imports Active

**What goes wrong:** The plan is to "archive" cloud provider code (ZAI, OpenRouter) while keeping it available. The risk is that `providers/__init__.py` still imports from `providers/zai.py` and `providers/openrouter.py`. If those files are moved to `providers/archive/` or renamed without updating `__init__.py`, every file that does `from providers import get_provider` breaks with `ImportError`.

**Why it happens:** Python package imports are path-based. Moving a file is not a refactor — it is a breaking change to all importers unless `__init__.py` re-exports the moved symbols.

**Specific dependency chain:**
- `controller.py` → `from providers import get_provider, get_fallback_provider`
- `modules/ai_extractor.py` → `from providers import get_provider` (inside verify_metadata)
- `modules/ai_extractor.py` → `from providers.openrouter import _merge_system_into_user` (line 23, direct import)
- `services/review_service.py` — likely imports provider

**Consequences:** App fails to start. All 268 tests fail on import.

**Prevention:**
- Keep provider files in-place; add a `# DEPRECATED: cloud-only` comment at the top
- Do not move files; mark them as archived in comments only
- If physical archiving is required, update `providers/__init__.py` to re-export from new locations, and fix `_merge_system_into_user` import in `ai_extractor.py`
- Run full test suite after any provider file move before marking phase done

**Detection:** `ImportError` at startup, all tests red.

**Phase:** Cloud cleanup phase. Run `pytest -x` immediately after any import restructuring.

---

### Pitfall 8: logprobs API Availability in llama-server b5606

**What goes wrong:** The llama.cpp `/v1/chat/completions` endpoint supports logprobs via `logprobs: true` and `top_logprobs: N` in the request body (OpenAI-compatible). However, in b5606, `logprobs` are only returned if the server was *not* started with `--grammar-file` (see Pitfall 1) and only when sampling temperature > 0. The `OllamaProvider.complete()` currently hardcodes `temperature=0.05` which is fine, but if temperature is ever set to 0.0, llama-server returns deterministic output and the logprob for the chosen token is always 0.0 (log(1.0)), making all confidence scores 1.0 regardless of actual certainty.

**Additional issue:** The `logprobs` field in the response is at `response.choices[0].logprobs.content[i].logprob` — not `response.choices[0].message.logprobs`. The OpenAI Python SDK (which is used here) maps this correctly for OpenAI's API but the llama-server response shape may differ slightly. Need to validate the actual JSON shape from b5606 before writing parsing code.

**Prevention:**
- Test logprobs with a minimal script against the running llama-server *before* integrating into the pipeline: `curl http://localhost:8080/v1/chat/completions -d '{"model":"local","messages":[...],"logprobs":true,"top_logprobs":1,"temperature":0.05,"max_tokens":5}'`
- Keep temperature at 0.05 (never 0.0) when logprobs are needed
- Handle the case where `choices[0].logprobs` is `None` gracefully (returns when grammar is active or server version doesn't support it)

**Detection:** `AttributeError: 'NoneType' object has no attribute 'content'` when accessing logprobs on the response object.

**Phase:** GBNF + logprobs phase. Validate with a standalone script before wiring into the provider.

---

## Minor Pitfalls

### Pitfall 9: Test Suite Has 19 Tests Tied to Reporter

**What goes wrong:** `tests/test_reporter.py` tests `generate_report()`. After removing reporter, these tests pass vacuously (if reporter is mocked elsewhere) or fail. `test_controller.py` patches `controller.generate_report` in multiple test functions — these will raise `AttributeError` after the import is removed from controller.py.

**Prevention:** Delete `test_reporter.py` and remove reporter patches from `test_controller.py` in the same commit as reporter removal.

**Phase:** Reporter removal phase.

---

### Pitfall 10: Validator L3 Used INN Checksum Logic That Has Real Value

**What goes wrong:** `_validate_l3` in validator.py contains hallucination detection and `_validate_inn` contains actual INN checksum logic. These are not "cloud-era" artifacts — they detect real model errors. Deleting the entire validator module removes these checks along with the L4 duplicate detection.

**Prevention:** Before deleting: extract `_validate_inn` and the hallucination name list into `modules/postprocessor.py` as part of `sanitize_metadata()`. The postprocessor already runs on all ollama responses. This preserves the guards without keeping the validator scaffolding.

**Phase:** Validator removal phase. Do not bulk-delete; extract valuable logic first.

---

### Pitfall 11: SQLite `validation_status` Column Cannot Be Dropped Without Migration

**What goes wrong:** `validation_status` is a column in the `contracts` table, referenced by the UI (status badges in AG Grid) and by `database.py` read queries. Removing the validator does not mean removing this column — the column must stay and be populated (even if just with `"ok"` as default).

**Prevention:** Keep `validation_status` in the DB schema. After validator removal, write `"ok"` unconditionally or derive it from logprobs confidence. Add a migration only if renaming the column.

**Phase:** Validator removal phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| GBNF + logprobs | Grammar mode makes logprobs meaningless (Pitfall 1) | Use grammar via per-request body, not server flag; test logprobs with curl first (Pitfall 8) |
| Validator removal | controller.py import crash (Pitfall 2) | Audit and update controller.py + tests in same commit |
| Reporter removal | stats dict KeyError, dead test patches (Pitfall 3) | Search all consumers before removing; keep `report_path: None` in stats |
| Redline DOCX | Word repair dialog, silent strip of track changes (Pitfall 4) | Validate XML structure; test in Word not just LibreOffice |
| Vector versioning | Wrong threshold, false version groups (Pitfall 5) | Add date-range guard; log all linking decisions |
| Cloud provider archiving | Import chain breaks (Pitfall 7) | Keep files in place, mark deprecated in comments only |
| Sentence-transformers | Silent 90MB download mid-pipeline (Pitfall 6) | Pre-download in setup flow alongside llama-server |
| INN/hallucination logic | Lost when validator deleted (Pitfall 10) | Move to postprocessor before deleting validator |

---

## Sources

- Code inspection: `controller.py`, `modules/validator.py`, `modules/reporter.py`, `services/version_service.py`, `providers/ollama.py`, `modules/ai_extractor.py`, `services/llama_server.py` (direct read, HIGH confidence)
- llama.cpp logprobs + grammar interaction: known architectural limitation documented in llama.cpp issues; confidence MEDIUM (training knowledge, not verified against b5606 release notes directly)
- python-docx track changes: based on OOXML schema behavior and reported Word compatibility issues; confidence MEDIUM
- sentence-transformers download behavior: HIGH confidence (deterministic library behavior)
- SQLite migration impact: HIGH confidence (direct schema inspection)
