# Image Relevance & Auto-Tagging Engine

An AI-powered backend that classifies images, matches them with relevant blog posts, rejects mismatched suggestions, and supports human review. Built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and Google Gemini.

## Overview

The system automates image tagging and matching through the following pipeline:
* **Image Classification:** Extracts structured metadata, tags, captions, and confidence scores using Gemini Vision.
* **Batch Processing:** Processes image directories with retries, failure isolation, and idempotency.
* **Semantic Matching:** Generates 768-dimensional embeddings and ranks images against blog post content using cosine similarity.
* **Mismatch Guard:** Checks model confidence, semantic similarity, category compatibility, and subject conflicts.
* **Review API:** Allows users to inspect, approve, or reject image suggestions.
* **Cost Tracking:** Records AI API usage and estimated costs.
* **Evaluation:** Tests matching and rejection behavior against a labeled dataset.

## Architecture

```mermaid
flowchart TD
    A[Image Corpus] --> B[Background Batch Processing]
    B --> C[Gemini Vision]
    C --> D[Pydantic Validation]
    D --> E[(PostgreSQL)]
    E --> F[Generate Embeddings]
    G[Blog Posts] --> F
    F --> H[Cosine Similarity Ranking]
    H --> I[Mismatch Guard]
    I --> J[Ranked Suggestions]
    I --> K[Rejected Suggestions with Reasons]
    J --> L[Review API]
    K --> L
    L --> M[Approve or Reject]
```

## Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend API** | FastAPI |
| **Database** | PostgreSQL |
| **ORM & Migrations** | SQLAlchemy, Alembic |
| **Validation** | Pydantic |
| **Vision Model** | Gemini Flash |
| **Embedding Model** | gemini-embedding-001 |
| **Testing** | pytest |

## Key Features

* Schema-validated image metadata.
* Low-confidence detection.
* Batch processing with retries and idempotency.
* Persistent image, post, tag, and embedding data.
* Semantic ranking with a mismatch guard.
* Human-readable rejection explanations.
* Suggestion approval and rejection endpoints.
* Background job status and progress tracking.
* Per-call API usage and estimated cost tracking.

## Setup

### Prerequisites

* Python 3.11+
* PostgreSQL
* Google Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Installation

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root using `.env.example` as a template:

```env
DATABASE_URL=postgresql+psycopg2://USERNAME:PASSWORD@localhost:5432/image_relevance_auto_tagging
GEMINI_API_KEY=your_gemini_api_key_here
```

Make sure the PostgreSQL database exists, then run:

```bash
alembic upgrade head
```

## Run the API

```bash
uvicorn app.main:app --reload
```

* **API:** http://127.0.0.1:8000
* **Swagger documentation:** http://127.0.0.1:8000/docs

## Main API Endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Check API health |
| `POST` | `/jobs/images/process` | Start background image processing |
| `GET` | `/jobs` | List processing jobs |
| `GET` | `/jobs/{job_id}` | Check job progress |
| `GET` | `/posts/{post_id}/suggestions` | Retrieve image suggestions for a post |
| `GET` | `/suggestions/{suggestion_id}` | Inspect a suggestion |
| `POST` | `/suggestions/{suggestion_id}/approve` | Approve a suggestion |
| `POST` | `/suggestions/{suggestion_id}/reject` | Reject a suggestion |
| `GET` | `/costs` | Inspect API usage records |
| `GET` | `/costs/summary` | View aggregated usage and estimated costs |

## Image Dataset

The project includes 45 images across five categories:
* Wildlife
* Domestic animals
* Food
* Technology
* Nature

The image manifest is available at `data/manifest.json`. Dataset naming and source information are documented in the manifest.

## Mismatch Guard

The guard evaluates four conditions before accepting a suggested match:
1. Vision confidence meets the configured threshold.
2. Semantic similarity meets the configured threshold.
3. Image category is compatible with the article.
4. The image subject does not conflict with the article's intended subject.

The initial thresholds are defined in `app/constants.py` and have not been production-tuned.

## Evaluation

Run the labeled evaluation dataset:

```bash
python evals/run_eval.py
```

**Evaluation results:**
* Total cases: 10
* Correct positive Top-1 matches: 8/8
* Correctly rejected negative controls: 2/2
* Incorrect results: 0

All 10 evaluation cases were handled correctly. This is a small evaluation dataset, so the result should not be interpreted as a guarantee of production performance.

## Tests

Run the automated test suite:

```bash
pytest -q
```

*Latest recorded result:* 68 passed.

## Project Documentation

* `BUILDLOG.md` — development stages and implementation notes.
* `EVIDENCE.md` — capstone requirement verification.
* `capstone.yaml` — project metadata and component status.
* `data/manifest.json` — image dataset details.

