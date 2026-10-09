# Build Log

##  Project Scaffolding
- Initialized FastAPI application structure (`app/main.py`, `app/config.py`).
- Configured environment loading with `pydantic-settings` and `python-dotenv`.
- Created sanity check script (`scratch/sanity_check.py`).

## Design & Database Foundation
- Designed PostgreSQL database schema for 6 models (`Image`, `Tag`, `Post`, `Embedding`, `Suggestion`, `Review`).
- Initialized Alembic migrations and applied initial revision 
- Added database connection and model metadata tests (`tests/test_database.py`).
- Verified database setup and schema consistency.

##  Gemini Vision + One Image Classification
- Installed official `google-genai` SDK (`google-genai==2.27.0`) and updated `requirements.txt`.
- Created `app/services/gemini_client.py` to initialize `genai.Client` safely using `GEMINI_API_KEY` from `.env`.
- Created `ImageMetadataSchema` Pydantic model (`app/schemas/image_metadata.py`) enforcing required fields and confidence score validation (0.0 to 1.0).
- Created `app/services/vision_service.py` to call Gemini Vision (`gemini-2.0-flash`) using structured JSON output (`GenerateContentConfig`).
- Added unit tests (`tests/test_vision_schema.py`) to verify schema validation logic offline.
- Created sample test image `data/test_fox.png` and live demo script `scratch/test_gemini_vision.py`.
- **Result:** Live Gemini Vision classification and Pydantic validation succeeded.

##  Connect Vision to PostgreSQL
- Inspected Stage 1 database models and Alembic migrations.
- Updated `Image` model to include explicit metadata columns (`subject`, `category`, `caption`, `attributes`) mapping the `ImageMetadataSchema`.
- Created Alembic migration (`alembic revision --autogenerate -m "Add image vision metadata"`) and successfully upgraded the schema (`alembic upgrade head`).
- Implemented `app/services/image_metadata_service.py` to persist metadata, dynamically calculate `low_confidence` (threshold `0.70`), and safely create unique `Tag` entries via a single SQLAlchemy transaction.
- Added offline testing (`tests/test_image_metadata_service.py`) for DB persistence, confidence handling, and duplicate tag prevention via isolated in-memory SQLite.
- Verified live end-to-end processing (Image -> Gemini -> Database) via `scratch/test_vision_database.py` using a realistic local image (`data/fox.jpg`). Database read-back successfully retrieved generated metadata and tags.

##  Batch Image Ingestion
- Inspected existing models and Gemini vision services.
- Replaced the `"PROCESSED"` status with `"COMPLETED"` to explicitly match requested standard processing statuses (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). 
- Created `app/services/batch_processor.py` for sequential directory processing.
- Implemented robust error handling with a 2-retry mechanism (`MAX_RETRIES = 2`) to ensure isolated failures do not crash the batch job.
- Added idempotency check to automatically skip images with `COMPLETED` status.
- Implemented a `BatchSummary` to track totals, completions, failures, skips, and low confidence counts.
- Wrote extensive offline tests (`tests/test_batch_processor.py`) mocking the Gemini API to verify failure handling, retries, idempotency, and tracking metrics.
- Downloaded a 3-image dataset (`dog.jpg`, `bear.jpg`, `bird.jpg`) for live testing.
- Verified live functionality and idempotency via `scratch/live_batch_test.py`.

## Generate Embeddings
- Configured embedding generation utilizing `models/gemini-embedding-001` with `output_dimensionality` forced to 768 to guarantee fixed dimensions across different text inputs.
- Defined a straightforward validation schema `EmbeddingSchema`.
- Implemented `app/services/text_representation_service.py` mapping metadata to human-readable text representations (concatenating Subject, Category, Attributes, Caption for Images; Title and Content for Posts).
- Implemented `app/services/embedding_generation_service.py` to wrap the `google-genai` embedding API call and return the validated schema.
- Built `app/services/embedding_storage_service.py` to handle transactional saving of the `Embedding` records for both `Image` and `Post` entities, ensuring idempotent upserts using their respective IDs.
- Wrote extensive offline tests via `tests/test_embedding.py` to verify schema validation, text generation, and idempotent persistence via SQLite and mocked API calls.
- Ran live test `scratch/test_embedding_live.py` that successfully fetched an existing `COMPLETED` image, generated and persisted its embedding, generated a dummy post, and generated and persisted its embedding, verifying DB storage of 768-dimensional JSON vector output.
- Avoided schema migrations, natively utilizing the existing JSON `vector` column in the `embeddings` table.

##  Semantic Matching & Ranking
- Implemented mathematical semantic matching entirely in Python via standard library `math` avoiding heavy external dependencies like NumPy.
- Created `cosine_similarity(vector_a, vector_b)` to reliably compute mathematical similarity between embedded records, enforcing strict dimensionality matching and zero-vector crash prevention.
- Added simple Pydantic response schemas (`RankedCandidateSchema`, `RankedSuggestionsResponse`) for straightforward result formatting.
- Created `app/services/semantic_matching_service.py` to seamlessly execute vector comparisons between a `Post` and all embedded `Image` items, correctly generating descending rankings.
- Achieved ranking idempotency by checking `Suggestion` state and updating instead of aggressively creating multiple identical matches.
- Enforced complete missing-embedding exception handling to prevent application crashes when content is not yet processed through Gemini APIs.
- Built a thorough suite of in-memory offline testing inside `tests/test_semantic_matching.py` and `tests/test_similarity.py` using dummy orthogonal/aligned vectors to guarantee sorting accuracy.
- Ran end-to-end `scratch/test_ranking_live.py` returning expected ranking of Bear image (0.63 similarity) above Bird and Dog equivalents against a test blog post regarding bears.

## Mismatch Guard
- Created initial thresholds constants module (`app/constants.py`) with `VISION_CONFIDENCE_THRESHOLD = 0.70`, `SEMANTIC_ACCEPT_THRESHOLD = 0.60`, and `CATEGORY_MATCH_THRESHOLD = 0.0`. These thresholds are explicitly documented as INITIAL (not production-tuned).
- Created `GuardResult` Pydantic schema (`app/schemas/guard_schema.py`) holding `accepted: bool` and `reason: str`.
- Implemented mismatch guard service (`app/services/mismatch_guard_service.py`):
  - Vision confidence check: rejects images with confidence below `0.70` or marked with `low_confidence=True`.
  - Semantic similarity check: rejects candidates with cosine similarity below `0.60`.
  - Category compatibility check: checks for explicit domain mismatches (e.g., food category vs server infrastructure articles).
  - Conservative subject-matching check: does NOT require article text to contain the image subject as a universal acceptance rule. Only rejects when the article clearly identifies a specific subject from known groups and the image depicts a conflicting subject. Ambiguous articles (e.g., "Wildlife photography in winter") allow compatible images (e.g., "bear") through to let semantic similarity and vision confidence carry weight.
- Integrated mismatch guard into `rank_images_for_post` (`app/services/semantic_matching_service.py`):
  - Candidates passing the guard are preserved as `PENDING` for human review and returned in `RankedSuggestionsResponse`.
  - Candidates failing the guard are persisted in the `suggestions` table with `status="REJECTED"` and an explanatory `explanation` detailing the guard decision.
  - Ranking is idempotent, updating existing suggestions rather than creating duplicate rows.
- Created unit tests (`tests/test_mismatch_guard.py`) testing all 8 verification scenarios in-memory.
- Created live verification script (`scratch/test_mismatch_guard_live.py`) and verified end-to-end against PostgreSQL.

## [Stage 4] Production / Review API & Evaluation
- Inspected existing PostgreSQL database models (`Suggestion`, `Review`, `Image`, `Post`) and verified that existing schemas fully support human review actions without schema alterations.
- Created `app/database.py` providing session management (`SessionLocal`) and FastAPI dependency `get_db`.
- Created Review API schemas (`app/schemas/review_schema.py`):
  - `ReviewActionRequest`: payload for review decisions (`reason`).
  - `ReviewResponse`: details of human approval/rejection.
  - `SuggestionListItemResponse`: summary item with image metadata and `accepted_by_guard` indicator.
  - `SuggestionDetailResponse`: comprehensive suggestion view including post, image, and review history.
- Implemented `app/services/review_service.py` with review operations:
  - `get_suggestions_for_post`: lists suggestions ordered by score, distinguishing mismatch guard rejections from accepted candidates.
  - `get_suggestion_detail`: retrieves single suggestion with nested image/post metadata and review records.
  - `review_suggestion`: records human approval (`status="APPROVED"`) or rejection (`status="REJECTED"`), idempotently updating any existing `Review` entry to prevent duplicate review records.
- Implemented Review API routes in `app/routes/review_routes.py` and included in `app/main.py`:
  - `GET /posts/{post_id}/suggestions`
  - `GET /suggestions/{suggestion_id}`
  - `POST /suggestions/{suggestion_id}/approve`
  - `POST /suggestions/{suggestion_id}/reject`
- Created comprehensive Review API tests (`tests/test_review_api.py`) verifying listing, detail retrieval, 404 handling, approval, rejection, guard explanation preservation, and idempotency (9 tests passing).
- Created labeled evaluation dataset (`evals/dataset.json`) with 10 structured cases covering bear, dog, bird, jackal, and unrelated negative control articles (cloud computing, culinary recipe).
- Implemented Top-1 precision evaluation runner (`evals/run_eval.py`):
  - Ran evaluation using the existing semantic matching + mismatch guard pipeline.
  - Maintained initial thresholds (`VISION_CONFIDENCE_THRESHOLD = 0.70`, `SEMANTIC_ACCEPT_THRESHOLD = 0.60`).
  - Result: 10/10 cases correct (8 correct Top-1 matches, 2 correct mismatch guard rejections), achieving 100.0% Top-1 Precision.
- Created live verification script (`scratch/test_review_api_live.py`) and verified all Review API operations against live PostgreSQL.

---

## Final Capstone Completion & Requirements Gap Closure

### Key Achievements:
1. **Repository & Submission Assets:**
   - Created `.env.example` with safe placeholder variables.
   - Added standard MIT `LICENSE`.
   - Created `capstone.yaml` detailing project architecture, components, and evaluation metadata.
   - Authored comprehensive `EVIDENCE.md` verifying all 20 capstone acceptance requirements.

2. **Full Image Corpus (45 Real Photographs across 5 Categories):**
   - Curated and downloaded 45 authentic CC0 licensed photographs into `data/images/`.
   - Covered 5 distinct domains: `wildlife`, `domestic`, `food`, `technology`, and `nature`.
   - Created dataset manifest `data/manifest.json` detailing filename, category, subject, source, and file path.
   - Added unit test suite `tests/test_dataset_corpus.py` ensuring corpus size $\ge 40$ and categories $\ge 4$.

3. **Per-Call Cost & Token Usage Tracking:**
   - Designed and migrated `APICallCost` database table (`api_call_costs`) tracking operation type, model, prompt/candidate tokens, and estimated USD cost.
   - Implemented `app/services/cost_tracking_service.py` with pricing models for Gemini Vision and Gemini Embedding.
   - Integrated automatic cost recording into `vision_service.py` and `embedding_generation_service.py`.
   - Exposed API routes `GET /costs` and `GET /costs/summary` via `app/routes/cost_routes.py`.
   - Added automated tests in `tests/test_cost_tracking.py`.

4. **Background Job Processing:**
   - Implemented `BatchJob` model (`batch_jobs`) for tracking asynchronous background processing status, progress counters, and error messages.
   - Created `app/services/job_service.py` managing background job scheduling and execution with FastAPI `BackgroundTasks`.
   - Exposed REST API endpoints `POST /jobs/images/process`, `GET /jobs/{job_id}`, and `GET /jobs` via `app/routes/job_routes.py`.
   - Added automated tests in `tests/test_background_jobs.py`.

5. **Database & Migrations:**
   - Created and applied Alembic migration `64da3268db6b_add_cost_tracking_and_batch_jobs_tables.py`.
   - Verified `alembic check` passes with 0 pending operations.

6. **Final Verification & Test Suite:**
   - Pytest suite expanded to **68 passing tests** with 100% pass rate.
   - Evaluated Top-1 Precision benchmark: **100.00% (10/10)** (8/8 positive Top-1 matches, 2/2 negative controls correctly rejected).
   - Verified live PostgreSQL execution for batch jobs, cost tracking, mismatch guard, and review workflows.

---

