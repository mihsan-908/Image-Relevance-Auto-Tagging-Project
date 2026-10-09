"""Service for validating image suggestions against blog posts (Mismatch Guard).

This module guards against false-positive suggestions by checking:
1. Vision Confidence: Images with low AI confidence or marked as low-confidence are rejected.
2. Semantic Similarity: Images below the acceptance threshold are rejected.
3. Category Compatibility: Obvious conflicts between post content and image category are rejected.
4. Conservative Subject Conflict: If the article clearly specifies a distinct subject and
   the image depicts an entirely different, conflicting subject, it is rejected.
"""

from app.models.post import Post
from app.models.image import Image
from app.schemas.guard_schema import GuardResult
from app.constants import VISION_CONFIDENCE_THRESHOLD, SEMANTIC_ACCEPT_THRESHOLD


def check_candidate(post: Post, image: Image, semantic_score: float) -> GuardResult:
    """Evaluate whether an image candidate is safe and trustworthy for a post.

    Args:
        post: The blog post being matched.
        image: The candidate image to inspect.
        semantic_score: Cosine similarity score between post and image embeddings.

    Returns:
        GuardResult indicating accepted (True/False) and the reason.
    """
    # 1. Vision Confidence Check
    # Ensure vision model had sufficient confidence and didn't flag low confidence
    if image.low_confidence:
        return GuardResult(
            accepted=False,
            reason="Image flagged with low vision confidence."
        )

    if image.confidence is not None and image.confidence < VISION_CONFIDENCE_THRESHOLD:
        return GuardResult(
            accepted=False,
            reason=f"Vision confidence ({image.confidence:.2f}) is below threshold ({VISION_CONFIDENCE_THRESHOLD:.2f})."
        )

    # 2. Semantic Similarity Threshold Check
    # Ensure baseline topical relevance is met
    if semantic_score < SEMANTIC_ACCEPT_THRESHOLD:
        return GuardResult(
            accepted=False,
            reason=f"Semantic similarity score ({semantic_score:.2f}) is below threshold ({SEMANTIC_ACCEPT_THRESHOLD:.2f})."
        )

    # Prepare combined post text for textual compatibility checks
    title_text = post.title or ""
    content_text = post.content or ""
    post_text = f"{title_text} {content_text}".lower()

    # 3. Category Compatibility Check
    if image.category:
        img_cat = image.category.lower().strip()
        
        # Conflict mappings: {image_category: [keywords indicating an incompatible domain]}
        incompatible_domains = {
            "food": ["automotive", "software programming", "cloud computing", "machine learning algorithm", "cybersecurity"],
            "technology": ["recipe", "baking ingredients", "culinary herbs"],
            "vehicle": ["baking cake", "knitting pattern", "gardening flowers"],
        }
        
        # If the article strongly targets an incompatible domain
        if img_cat in incompatible_domains:
            conflicts = incompatible_domains[img_cat]
            for conflict_term in conflicts:
                if conflict_term in post_text:
                    return GuardResult(
                        accepted=False,
                        reason=f"Category conflict: image category '{image.category}' is incompatible with post context '{conflict_term}'."
                    )

    # 4. Conservative Subject Conflict Check
    if image.subject:
        img_subject = image.subject.lower().strip()

        subject_groups = [
            {"fox", "red fox", "arctic fox"},
            {"wolf", "grey wolf", "timber wolf"},
            {"bear", "grizzly bear", "polar bear", "black bear"},
            {"lion"},
            {"tiger"},
            {"elephant"},
            {"cat", "kitten"},
            {"dog", "puppy"},
        ]

        # Determine which group the image subject belongs to, if any
        image_group = None
        for group in subject_groups:
            if any(term in img_subject for term in group):
                image_group = group
                break

        # If the image belongs to a known distinct subject group, check if post specifically focuses on a DIFFERENT group
        if image_group is not None:
            post_groups_found = []
            for group in subject_groups:
                if any(term in post_text for term in group):
                    post_groups_found.append(group)

            # If post clearly mentions subjects from known groups, but DOES NOT mention image's group
            if post_groups_found and (image_group not in post_groups_found):
                return GuardResult(
                    accepted=False,
                    reason=f"Clear subject conflict: article specifically targets other subjects but image depicts '{image.subject}'."
                )

    return GuardResult(
        accepted=True,
        reason="Passed all mismatch guard checks."
    )
