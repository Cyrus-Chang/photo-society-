# Works Retrieval Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a measurable, explainable hybrid work retriever over the existing CLIP ViT-B/32 index without adding dependencies.

**Architecture:** Persist CLIP/color vectors and manifest metadata in a base NPZ plus append-only NPZ shards while keeping the original artifact contract. `WorkIndex` reads ids/tags lazily at startup, loads vectors on first search, computes three normalized components (CLIP, tags, color), applies configurable weights, and returns component-level explanations. Evaluation and single-item upsert are standalone scripts.

**Tech Stack:** Python 3.11, FastAPI, NumPy, Pillow, SQLite stdlib, existing torch/transformers CLIP ViT-B/32.

**Spec:** `docs/superpowers/specs/2026-11-15-works-retrieval-quality-design.md`

## Global Constraints

- Do not add dependencies.
- Keep `openai/clip-vit-base-patch32`.
- Chinese queries map to English prompts and unknown terms remain visible.
- Do not modify `DiscoverPage.vue`, `MarketPage.vue`, `MarketPostCard.vue`, or `styles.css`.

## Review Focus

- Missing/unknown Chinese terms remain in the response and do not disappear during prompt mapping.
- Legacy NPZ without color/metadata still loads through the fallback path.
- Duplicate manifest entries (`works` + `spiralWorks`) index once by id.
- A zero or partial weight vector is normalized safely and does not produce NaN scores.
- Missing/invalid human annotation files never produce fabricated metrics.

---

### Task 1: Localize six external work images and build source ledger

**Files:**
- Create: `public/works/unsplash/w-001.jpg` … `w-006.jpg`
- Modify: `ai-classifier/models/works.manifest.json` (six `imageUrl` fields only)
- Create: `ai-classifier/docs/WORKS-SOURCES.md`
- Modify: `ai-classifier/tools/build_works_index.py`

**Interfaces:**
- `resolve_local(url: str) -> Path | None` resolves `/works/...` paths.
- The ledger records source URL, retrieval date, SHA256 and Unsplash License link.

- [ ] Download each source image and verify it opens with Pillow.
- [ ] Update only the six image URLs to local `/works/unsplash/...` paths and record license/hash metadata.
- [ ] Extend the builder to include local `/works/` entries and report `remote=0` after localization.
- [ ] Run the builder smoke check once the retrieval implementation is present; expect 50 unique ids.

### Task 2: Implement hybrid WorkIndex and persistence

**Files:**
- Modify: `ai-classifier/pipeline/retrieval.py`
- Modify: `ai-classifier/tools/build_works_index.py`
- Create: `ai-classifier/tools/update_work_index.py`
- Create/modify: `ai-classifier/models/works.index.sqlite`, `works.embed.npz`, `works.index.json`

**Interfaces:**
- `WorkIndex(path: Path, manifest_path: Path | None = None)`.
- `search_text(text: str, state: dict, k: int = 8, weights: dict | None = None, tags: list[str] | None = None, city: str = "") -> dict`.
- `upsert_work(entry: dict, image_path: Path, state: dict, db_path: Path) -> dict`.

- [ ] Add tests for component score calculation, weight normalization, and explanation fields using fake vectors/state.
- [ ] Implement lazy base/shard NPZ loading and legacy NPZ fallback; startup must not load all vector arrays.
- [ ] Implement Chinese→English mapping metadata with `mappedTerms`, `unknownTerms`, and `translatedText`.
- [ ] Implement tag overlap and color24 prototype scoring; return raw CLIP score plus all components.
- [ ] Make the builder write the base NPZ (including color/tags) and index metadata in one run, clearing stale shards.
- [ ] Implement the single-item upsert script and print extraction/write timings.
- [ ] Run focused unit tests and a 50-item build.

### Task 3: Wire both search routes and agent explanations

**Files:**
- Modify: `ai-classifier/pipeline/serve.py`
- Modify: `ai-classifier/pipeline/agent.py`
- Modify: `ai-classifier/mcp_server.py` only if request/response schema needs a pass-through

**Interfaces:**
- `TextRequest` adds optional `weights`, `tags`, and `city` without breaking `{text,k}`.
- `/v1/search` and `/api/v1/ai/search` return the same hybrid response shape.

- [ ] Add endpoint tests with a fake runtime index and assert both routes expose `query`, `weights`, and `hits[].explain`.
- [ ] Pass parsed style tags/city from `run_agent` to `WorkIndex` and remove its fixed CLIP+0.06 tag ranking adjustment.
- [ ] Preserve photographer aggregation and explicit cross-city warnings.
- [ ] Run a live HTTP smoke test against port 8100 when the service is available.

### Task 4: Human-labelled retrieval evaluation

**Files:**
- Create: `ai-classifier/data/retrieval_labels.json`
- Create: `ai-classifier/tools/eval_retrieval.py`
- Create: `ai-classifier/reports/retrieval_quality.md`

**Interfaces:**
- Label row: `{query, expected_id, annotator, source: "human", notes}`.
- Output: `.review-tmp/retrieval-eval.json` with `evaluated`, per-weight metrics, and limitations.

- [ ] Add strict validation for ≥40 rows, `source=human`, and known ids; fail without metrics when invalid.
- [ ] Implement recall@1, recall@5 and reciprocal rank for each weight set.
- [ ] Run all three weight sets through the local search function or HTTP endpoint and persist raw rows.
- [ ] Write a report that states the absolute CLIP-score limitation and the chosen trade-off.

### Task 5: End-to-end verification

**Files:**
- Create: `ai-classifier/tools/test_retrieval_contract.py`

- [ ] Verify index count, id uniqueness, and NPZ/SQLite id-set equality.
- [ ] Verify both HTTP aliases return 200 and identical hit ids for the same request.
- [ ] Verify unknown query words are present in the response metadata.
- [ ] Verify incremental upsert changes only one row and reports elapsed milliseconds.
- [ ] Run `python -m compileall pipeline tools` and the focused test suite.
