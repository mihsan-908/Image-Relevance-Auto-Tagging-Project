"""Pydantic schema for mismatch guard results."""

from pydantic import BaseModel


class GuardResult(BaseModel):
    """Result returned by the mismatch guard for an image-post candidate pair.

    Attributes:
        accepted: True if the candidate passes all guard checks, False otherwise.
        reason: Explanation of the decision (e.g. why it was accepted or rejected).
    """
    accepted: bool
    reason: str
