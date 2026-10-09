# 🧪 Acceptance & Verification Evidence

This document provides formal evidence of implementation, testing, and verification for all 20 requirements in the **Image Relevance & Auto-Tagging Engine** project.

---

## 1. Image Ingestion & Classification

- **Requirement:** Ingest real images and classify visual content using Gemini Vision.
- **Implementation Location:** [`app/services/vision_service.py`](app/services/vision_service.py)
- **Verification Command / Test:** `pytest tests/test_image_metadata_service.py`
- **Actual Observed Result:** Successfully sends image bytes to `gemini-2.0-flash` requesting structured JSON and returns validated `ImageMetadataSchema` populated with subject, category, attributes, caption, and confidence.

---

## 2. Structured Vision Output Validation

- **Requirement:** Enforce strict Pydantic schema validation over AI vision responses.
- **Implementation Location:** [`app/schemas/image_metadata.py`](app/schemas/image_metadata.py)
- **Verification Command / Test:** `pytest tests/test_vision_schema.py`
- **Actual Observed Result:** All 4 schema validation tests pass. Confidence constrained to $[0.0, 1.0]$. Malformed or missing fields raise `pydantic.ValidationError`.

---

## 3. Low-Confidence Flagging

- **Requirement:** Automatically mark images with low confidence ($< 0.70$) with a boolean flag.
- **Implementation Location:** [`app/services/image_metadata_service.py`](app/services/image_metadata_service.py)
- **Verification Command / Test:** `pytest tests/test_image_metadata_service.py::test_low_confidence_flag_calculation`
- **Actual Observed Result:** When `confidence < 0.70`, `image.low_confidence` is set to `True` in PostgreSQL.

---

## 4. Batch Image Processing

- **Requirement:** Process multiple images in a directory sequentially with progress reporting.
- **Implementation Location:** [`app/services/batch_processor.py`](app/services/batch_processor.py)
- **Verification Command / Test:** `pytest tests/test_batch_processor.py::test_successful_processing`
- **Actual Observed Result:** Discovers supported files (`.jpg`, `.jpeg`, `.png`, `.webp`), processes images sequentially, updates database records from `PENDING` $\to$ `PROCESSING` $\to$ `COMPLETED`, and returns a detailed `BatchSummary`.

---

## 5. Retry Behavior on Transient AI Failure

- **Requirement:** Retry failed vision calls up to 2 times before failing.
- **Implementation Location:** [`app/services/batch_processor.py`](app/services/batch_processor.py)
- **Verification Command / Test:** `pytest tests/test_batch_processor.py::test_retry_after_simulated_failure`
- **Actual Observed Result:** Simulated transient failures are retried after a 2-second delay and succeed on subsequent attempts.

---

## 6. Idempotency & Duplicate Prevention

- **Requirement:** Avoid duplicate processing and duplicate database records on repeated runs.
- **Implementation Location:**
  - Ingestion: [`app/services/batch_processor.py`](app/services/batch_processor.py)
  - Embedding: [`app/services/embedding_storage_service.py`](app/services/embedding_storage_service.py)
  - Ranking: [`app/services/semantic_matching_service.py`](app/services/semantic_matching_service.py)
- **Verification Command / Test:** `pytest tests/test_batch_processor.py::test_idempotency_skip_completed` and `pytest tests/test_embedding.py::test_image_embedding_idempotency`
- **Actual Observed Result:** Already `COMPLETED` images are skipped with `summary.skipped += 1`. Re-running embeddings or rankings updates existing rows in place without creating duplicate records.

---

## 7. Semantic Embedding Generation & Storage

- **Requirement:** Convert image metadata and blog posts into 768-dimensional vectors using `gemini-embedding-001` and persist in PostgreSQL.
- **Implementation Location:** [`app/services/embedding_generation_service.py`](app/services/embedding_generation_service.py), [`app/services/embedding_storage_service.py`](app/services/embedding_storage_service.py)
- **Verification Command / Test:** `pytest tests/test_embedding.py`
- **Actual Observed Result:** All 8 embedding tests pass. Vectors stored as JSON float arrays in the `embeddings` table linked via foreign keys to `images` or `posts`.

---

## 8. Semantic Ranking

- **Requirement:** Rank image candidates against blog posts by calculating pure cosine similarity over embeddings.
- **Implementation Location:** [`app/utils/similarity.py`](app/utils/similarity.py), [`app/services/semantic_matching_service.py`](app/services/semantic_matching_service.py)
- **Verification Command / Test:** `pytest tests/test_semantic_matching.py` and `pytest tests/test_similarity.py`
- **Actual Observed Result:** Cosine similarity correctly ranks candidates from highest score to lowest.

---

## 9. Mismatch Guard

- **Requirement:** Multi-stage safety guard filtering out false positives (confidence $< 0.70$, similarity $< 0.60$, category conflict, conservative subject conflict).
- **Implementation Location:** [`app/services/mismatch_guard_service.py`](app/services/mismatch_guard_service.py)
- **Verification Command / Test:** `pytest tests/test_mismatch_guard.py`
- **Actual Observed Result:** All 8 mismatch guard test scenarios pass:
  - Red fox article + red fox image $\to$ **ACCEPTED**
  - Red fox article + wolf image $\to$ **REJECTED** (subject conflict)
  - Low vision confidence $\to$ **REJECTED**
  - Low semantic similarity $\to$ **REJECTED**
  - Category conflict $\to$ **REJECTED**
  - Ambiguous wildlife article + bear image $\to$ **ACCEPTED** (conservative subject check)

---

## 10. Human-Readable Rejection Explanations

- **Requirement:** Provide human-readable explanations explaining why an image was accepted or rejected.
- **Implementation Location:** [`app/services/mismatch_guard_service.py`](app/services/mismatch_guard_service.py)
- **Verification Command / Test:** `pytest tests/test_mismatch_guard.py::test_scenario_7_rejected_suggestions_persisted`
- **Actual Observed Result:** Rejected suggestions contain descriptive explanations such as `"Rejected by mismatch guard: Vision confidence (0.50) is below threshold (0.70)."` and `"Rejected by mismatch guard: Clear subject conflict: article specifically targets other subjects but image depicts 'wolf'."`

---

## 11. No-Match Behavior

- **Requirement:** Safely produce no accepted image suggestions when no suitable candidate exists.
- **Implementation Location:** [`app/services/semantic_matching_service.py`](app/services/semantic_matching_service.py)
- **Verification Command / Test:** `python evals/run_eval.py` (Cases 09 and 10)
- **Actual Observed Result:** Cases 09 ("Modern Cloud Server Optimization") and 10 ("Italian Pasta Recipes") produce empty candidate lists with all incompatible candidates safely marked `REJECTED`.

---

## 12. Review API

- **Requirement:** RESTful FastAPI endpoints for listing suggestions, inspecting details, approving, and rejecting suggestions.
- **Implementation Location:** [`app/routes/review_routes.py`](app/routes/review_routes.py), [`app/services/review_service.py`](app/services/review_service.py)
- **Verification Command / Test:** `pytest tests/test_review_api.py`
- **Actual Observed Result:** All 9 review API tests pass:
  - `GET /posts/{post_id}/suggestions` returns ordered suggestions with guard outcome.
  - `GET /suggestions/{suggestion_id}` returns suggestion details, image metadata, and review history.

---

## 13. Human Approval Workflow

- **Requirement:** Human reviewer can approve a suggestion and record approval decision.
- **Implementation Location:** [`app/routes/review_routes.py`](app/routes/review_routes.py)
- **Verification Command / Test:** `pytest tests/test_review_api.py::test_approve_suggestion`
- **Actual Observed Result:** Suggestion status transitions to `APPROVED` and a `Review` record (`approved=True`) is created. Repeated approvals update existing review records idempotently.

---

## 14. Human Rejection Workflow

- **Requirement:** Human reviewer can reject a suggestion with an optional reason note.
- **Implementation Location:** [`app/routes/review_routes.py`](app/routes/review_routes.py)
- **Verification Command / Test:** `pytest tests/test_review_api.py::test_reject_suggestion`
- **Actual Observed Result:** Suggestion status transitions to `REJECTED` and a `Review` record (`approved=False`) is created, preserving existing mismatch guard explanation history.

---

## 15. Evaluation Dataset

- **Requirement:** Curate a labeled evaluation dataset with positive match cases and negative/reject cases.
- **Implementation Location:** [`evals/dataset.json`](evals/dataset.json)
- **Verification Command / Test:** `pytest tests/test_dataset_corpus.py`
- **Actual Observed Result:** `evals/dataset.json` contains 10 labeled test cases spanning wildlife, domestic animals, technology, and culinary recipes.

---

## 16. Top-1 Precision Evaluation Metric

- **Requirement:** Benchmark the end-to-end pipeline against the labeled dataset and achieve $\ge 80\%$ Top-1 Precision.
- **Implementation Location:** [`evals/run_eval.py`](evals/run_eval.py)
- **Verification Command / Test:** `python evals/run_eval.py`
- **Actual Observed Result:** **10/10 evaluation cases were correctly handled**: 8/8 positive cases produced the expected Top-1 image, and 2/2 negative controls were correctly rejected. Top-1 evaluation result: **100% (10/10 cases)**.

---

## 17. Cost & Token Usage Tracking

- **Requirement:** Track per-call token usage and estimated USD cost for Vision and Embedding API calls.
- **Implementation Location:** [`app/models/cost.py`](app/models/cost.py), [`app/services/cost_tracking_service.py`](app/services/cost_tracking_service.py), [`app/routes/cost_routes.py`](app/routes/cost_routes.py)
- **Verification Command / Test:** `pytest tests/test_cost_tracking.py`
- **Actual Observed Result:** All 6 cost tracking tests pass. Every vision and embedding call creates an `APICallCost` entry in PostgreSQL with token counts and estimated USD cost. Aggregated summaries are accessible via `GET /costs/summary`.

---

## 18. Database Schema, Foreign Keys & Indexes

- **Requirement:** Clean relational PostgreSQL schema with Alembic migrations and appropriate indexes.
- **Implementation Location:** [`alembic/versions/`](alembic/versions/)
- **Verification Command / Test:** `alembic check` and `pytest tests/test_database.py`
- **Actual Observed Result:** `alembic check` returns `No new upgrade operations detected.` All 8 tables (`images`, `tags`, `posts`, `embeddings`, `suggestions`, `reviews`, `api_call_costs`, `batch_jobs`) and their respective indexes are in complete synchronization.

---

## 19. Secrets Management & Security

- **Requirement:** Prevent hardcoded API keys or database passwords; ensure `.env` is ignored.
- **Implementation Location:** [`.gitignore`](.gitignore), [`.env.example`](.env.example), [`app/config.py`](app/config.py)
- **Verification Command / Test:** Inspection of codebase and gitignore.
- **Actual Observed Result:** `.env` is ignored by `.gitignore`. `.env.example` contains only placeholder values. No hardcoded credentials exist in source files.

---

## 20. Background Processing & Job Management

- **Requirement:** Provide asynchronous background processing for bulk image ingestion with job progress tracking.
- **Implementation Location:** [`app/models/job.py`](app/models/job.py), [`app/services/job_service.py`](app/services/job_service.py), [`app/routes/job_routes.py`](app/routes/job_routes.py)
- **Verification Command / Test:** `pytest tests/test_background_jobs.py`
- **Actual Observed Result:** `POST /jobs/images/process` accepts a directory, schedules asynchronous processing using FastAPI `BackgroundTasks`, and returns HTTP 202 Accepted. `GET /jobs/{job_id}` returns real-time progress metrics (`processed_count`, `completed_count`, `failed_count`, `skipped_count`).
