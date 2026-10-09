"""Evaluation script for measuring matching quality and Top-1 precision.

Evaluates the existing semantic matching + mismatch guard pipeline against
the labeled evaluation set in `evals/dataset.json`.

Outputs:
- Case-by-case report (expected vs predicted, similarity score, guard outcome)
- Total cases evaluated
- Correct Top-1 matches
- Incorrect Top-1 matches
- No-match / correctly rejected cases
- Top-1 Precision metric
"""

import json
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.post import Post
from app.models.embedding import Embedding
from app.services.embedding_storage_service import store_post_embedding
from app.services.semantic_matching_service import rank_images_for_post

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_evaluation():
    settings = get_settings()
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    eval_file = os.path.join(os.path.dirname(__file__), "dataset.json")
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_cases = json.load(f)

    print("==================================================")
    print("      EVALUATION & TOP-1 PRECISION       ")
    print("==================================================")
    print(f"Loaded {len(eval_cases)} evaluation cases from evals/dataset.json\n")

    total_cases = len(eval_cases)
    correct_matches = 0
    incorrect_matches = 0
    correct_no_matches = 0
    incorrect_no_matches = 0

    results_summary = []

    try:
        for idx, case in enumerate(eval_cases, start=1):
            case_id = case["id"]
            title = case["title"]
            content = case["content"]
            expected_filename = case.get("expected_filename")
            expected_subject = case.get("expected_subject")
            desc = case.get("description", "")

            # 1. Create or retrieve Post in database for evaluation
            # Using unique evaluation title prefix
            eval_title = f"EVAL_POST_{case_id}: {title}"
            post = db.query(Post).filter(Post.title == eval_title).first()
            if not post:
                post = Post(title=eval_title, content=content)
                db.add(post)
                db.commit()
                db.refresh(post)

            # 2. Ensure post has an embedding using the existing service
            post_emb = db.query(Embedding).filter(Embedding.post_id == post.id).first()
            if not post_emb:
                store_post_embedding(db, post)

            # 3. Run existing ranking pipeline with mismatch guard
            ranking_response = rank_images_for_post(db, post.id, limit=3)
            candidates = ranking_response.candidates

            # 4. Determine Top-1 predicted candidate
            top_candidate = candidates[0] if candidates else None

            # 5. Evaluate correctness
            is_correct = False
            predicted_filename = top_candidate.filename if top_candidate else None
            predicted_subject = top_candidate.subject if top_candidate else None
            score = top_candidate.similarity_score if top_candidate else None

            if expected_filename is None:
                # Unrelated / mismatch case: expectation is NO candidate accepted by guard
                if top_candidate is None:
                    is_correct = True
                    correct_no_matches += 1
                    status_str = "PASS (Correctly Rejected by Guard)"
                else:
                    is_correct = False
                    incorrect_matches += 1
                    status_str = f"FAIL (Expected No Match, got {predicted_filename})"
            else:
                # Relevant case: expectation is top_candidate matches expected_filename or expected_subject
                if top_candidate is None:
                    is_correct = False
                    incorrect_no_matches += 1
                    status_str = "FAIL (No Candidate Accepted by Guard)"
                elif top_candidate.filename == expected_filename or (
                    expected_subject and top_candidate.subject and expected_subject.lower() in top_candidate.subject.lower()
                ):
                    is_correct = True
                    correct_matches += 1
                    status_str = "PASS (Correct Top-1 Match)"
                else:
                    is_correct = False
                    incorrect_matches += 1
                    status_str = f"FAIL (Predicted {predicted_filename}, expected {expected_filename})"

            case_result = {
                "case_id": case_id,
                "title": title,
                "expected": expected_filename or "None (Should Reject)",
                "predicted": predicted_filename or "None (Rejected)",
                "predicted_subject": predicted_subject or "None",
                "similarity_score": f"{score:.4f}" if score is not None else "N/A",
                "is_correct": is_correct,
                "status_str": status_str,
                "description": desc,
            }
            results_summary.append(case_result)

            # Print case details
            print(f"Case {idx:02d} [{case_id}]: {title}")
            print(f"  Description : {desc}")
            print(f"  Expected    : {case_result['expected']}")
            print(f"  Predicted   : {case_result['predicted']} (Subject: '{case_result['predicted_subject']}')")
            print(f"  Score       : {case_result['similarity_score']}")
            print(f"  Outcome     : {status_str}\n")

        # 6. Overall Metrics
        # Total positive and negative cases handled correctly
        total_correct = correct_matches + correct_no_matches
        precision = (total_correct / total_cases) * 100.0 if total_cases > 0 else 0.0

        print("--------------------------------------------------")
        print("             EVALUATION REPORT SUMMARY            ")
        print("--------------------------------------------------")
        print(f"Total evaluated cases        : {total_cases}")
        print(f"Correct Top-1 matches        : {correct_matches}")
        print(f"Correctly rejected cases     : {correct_no_matches}")
        print(f"Incorrect Top-1 matches      : {incorrect_matches}")
        print(f"Incorrectly rejected cases   : {incorrect_no_matches}")
        print(f"Overall Accuracy / Precision : {precision:.2f}% ({total_correct}/{total_cases})")
        print("--------------------------------------------------")

        if precision >= 80.0:
            print("Status: EVALUATION SUCCEEDED (Meets capstone requirements)")
        else:
            print("Status: EVALUATION NEEDS REVIEW")

    finally:
        # Clean up evaluation posts created during test
        eval_posts = db.query(Post).filter(Post.title.like("EVAL_POST_%")).all()
        for p in eval_posts:
            db.delete(p)
        db.commit()
        db.close()


if __name__ == "__main__":
    run_evaluation()
