"""Tests for vector math utilities."""

import pytest
from app.utils.similarity import cosine_similarity

def test_identical_vectors():
    """Identical vectors should have a similarity of 1.0."""
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    assert cosine_similarity([0.5, 0.5], [0.5, 0.5]) == pytest.approx(1.0)

def test_orthogonal_vectors():
    """Orthogonal vectors should have a similarity of 0.0."""
    assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

def test_opposite_vectors():
    """Opposite vectors should have a similarity of -1.0."""
    assert cosine_similarity([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)

def test_different_vector_dimensions():
    """Vectors of different lengths should raise ValueError."""
    with pytest.raises(ValueError, match="same dimensionality"):
        cosine_similarity([1, 0], [1, 0, 0])

def test_empty_vectors():
    """Empty vectors should raise ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        cosine_similarity([], [])

def test_zero_vector():
    """Zero vectors should raise ValueError since magnitude is 0."""
    with pytest.raises(ValueError, match="zero vector"):
        cosine_similarity([0, 0], [1, 1])

def test_non_numeric_values():
    """Vectors with non-numeric values should raise ValueError."""
    with pytest.raises(ValueError, match="numeric"):
        cosine_similarity([1, "a"], [1, 2])
