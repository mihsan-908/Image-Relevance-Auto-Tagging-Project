"""Utility functions for vector math and semantic similarity."""

import math
from typing import List

def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """Calculate the cosine similarity between two vectors.
    
    The formula is: (A · B) / (|A| * |B|)

    """
    if not vector_a or not vector_b:
        raise ValueError("Vectors must not be empty.")
        
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same dimensionality.")
        
    dot_product = 0.0
    magnitude_a_sq = 0.0
    magnitude_b_sq = 0.0
    
    for a, b in zip(vector_a, vector_b):
        # Enforce numeric types just in case JSON parsing yielded something else
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("Vector elements must be numeric.")
            
        dot_product += a * b
        magnitude_a_sq += a * a
        magnitude_b_sq += b * b
        
    if magnitude_a_sq == 0.0 or magnitude_b_sq == 0.0:
        raise ValueError("Cannot calculate cosine similarity with a zero vector.")
        
    magnitude_a = math.sqrt(magnitude_a_sq)
    magnitude_b = math.sqrt(magnitude_b_sq)
    
    return dot_product / (magnitude_a * magnitude_b)
