"""Service for semantically matching and ranking images against posts."""

from sqlalchemy.orm import Session
from app.models.post import Post
from app.models.image import Image
from app.models.embedding import Embedding
from app.models.suggestion import Suggestion
from app.utils.similarity import cosine_similarity
from app.schemas.suggestion_schema import RankedCandidateSchema, RankedSuggestionsResponse
from app.services.mismatch_guard_service import check_candidate

def rank_images_for_post(db: Session, post_id: int, limit: int = 5) -> RankedSuggestionsResponse:
    """Calculate semantic similarities and return ranked image suggestions for a post.
    
    Images are filtered through the mismatch guard:
    - Accepted candidates are kept as PENDING for human review.
    - Rejected candidates are persisted with status REJECTED and their rejection reason.

    """
    # 1. Find the requested Post
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise ValueError(f"Post with ID {post_id} does not exist.")
        
    # 2. Find the Post embedding
    post_embedding = db.query(Embedding).filter(Embedding.post_id == post_id).first()
    if not post_embedding or not post_embedding.vector:
        raise ValueError(f"Post with ID {post_id} has no valid embedding.")
        
    post_vector = post_embedding.vector
    
    # 3. Load all valid image embeddings
    image_embeddings = db.query(Embedding).filter(Embedding.image_id.isnot(None)).all()
    
    if not image_embeddings:
        # Return empty early if no images exist
        return RankedSuggestionsResponse(post_id=post_id, candidates=[])
        
    accepted_candidates = []
    
    # 4. Compare post vector with each image vector and run mismatch guard
    for img_emb in image_embeddings:
        # Skip if missing vector or incompatible dimension
        if not img_emb.vector or len(img_emb.vector) != len(post_vector):
            continue
            
        try:
            score = cosine_similarity(post_vector, img_emb.vector)
            image = img_emb.image

            # Run through mismatch guard
            guard_result = check_candidate(post=post, image=image, semantic_score=score)

            if not guard_result.accepted:
                # Persist or update rejected suggestion in database
                existing_rejected = db.query(Suggestion).filter(
                    Suggestion.post_id == post_id,
                    Suggestion.image_id == image.id
                ).first()

                rejection_explanation = f"Rejected by mismatch guard: {guard_result.reason}"

                if existing_rejected:
                    existing_rejected.score = score
                    existing_rejected.status = "REJECTED"
                    existing_rejected.explanation = rejection_explanation
                else:
                    rejected_suggestion = Suggestion(
                        post_id=post_id,
                        image_id=image.id,
                        score=score,
                        status="REJECTED",
                        explanation=rejection_explanation
                    )
                    db.add(rejected_suggestion)
                continue

            # Candidate passed guard checks
            accepted_candidates.append({
                "image": image,
                "score": score
            })
        except ValueError:
            continue
            
    # 5. Sort accepted candidates from highest similarity to lowest
    accepted_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # 6. Apply limit
    top_candidates = accepted_candidates[:limit]
    
    ranked_results = []
    
    # 7. Create/Update Accepted Suggestions in Database
    for rank_idx, candidate in enumerate(top_candidates, start=1):
        image = candidate["image"]
        score = candidate["score"]
        
        # Check for existing suggestion
        existing_suggestion = db.query(Suggestion).filter(
            Suggestion.post_id == post_id,
            Suggestion.image_id == image.id
        ).first()
        
        explanation_text = "Passed mismatch guard. Ranked by semantic similarity for human review."
        
        if existing_suggestion:
            existing_suggestion.score = score
            existing_suggestion.explanation = explanation_text
            existing_suggestion.status = "PENDING"
        else:
            new_suggestion = Suggestion(
                post_id=post_id,
                image_id=image.id,
                score=score,
                status="PENDING",
                explanation=explanation_text
            )
            db.add(new_suggestion)
            
        ranked_results.append(
            RankedCandidateSchema(
                image_id=image.id,
                filename=image.filename,
                subject=image.subject,
                similarity_score=score,
                rank=rank_idx
            )
        )
        
    db.commit()
    
    return RankedSuggestionsResponse(
        post_id=post_id,
        candidates=ranked_results
    )

