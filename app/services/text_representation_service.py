"""Service to convert database models into text representations for embedding."""

from app.models.image import Image
from app.models.post import Post

def build_image_embedding_text(image: Image) -> str:
    """Build a human-readable text description of an image for embedding.
    
    Args:
        image: The processed Image model containing metadata.
        
    Returns:
        str: The combined text representation.
    """
    lines = []
    if image.subject:
        lines.append(f"Subject: {image.subject}")
    if image.category:
        lines.append(f"Category: {image.category}")
    if image.attributes:
        # Attributes are stored as a JSON array (list of strings)
        attr_str = ", ".join(image.attributes)
        lines.append(f"Attributes: {attr_str}")
    if image.caption:
        lines.append(f"Caption: {image.caption}")
        
    return "\n".join(lines)


def build_post_embedding_text(post: Post) -> str:
    """Build a human-readable text description of a post for embedding.
    
    Args:
        post: The Post model containing title and content.
        
    Returns:
        str: The combined text representation.
    """
    lines = []
    if post.title:
        lines.append(f"Title: {post.title}")
    if post.content:
        lines.append(f"Content: {post.content}")
        
    return "\n".join(lines)
