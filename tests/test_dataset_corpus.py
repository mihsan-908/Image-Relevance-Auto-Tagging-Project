"""Unit tests verifying image corpus requirements (40+ images, 4+ categories)."""

import os
import json
import pytest

IMAGE_DIR = "data/images"
MANIFEST_PATH = "data/manifest.json"


def test_manifest_file_exists():
    """Verify data/manifest.json exists and is valid JSON."""
    assert os.path.exists(MANIFEST_PATH), f"Missing manifest at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert isinstance(manifest, list)
    assert len(manifest) >= 40, f"Expected at least 40 manifest entries, got {len(manifest)}"


def test_corpus_image_count():
    """Verify data/images contains at least 40 supported image files."""
    assert os.path.isdir(IMAGE_DIR), f"Missing image directory at {IMAGE_DIR}"
    supported = {".jpg", ".jpeg", ".png", ".webp"}
    images = [
        f for f in os.listdir(IMAGE_DIR)
        if os.path.splitext(f)[1].lower() in supported
    ]
    assert len(images) >= 40, f"Expected at least 40 images in {IMAGE_DIR}, found {len(images)}"


def test_corpus_category_count():
    """Verify image corpus spans at least 4 distinct categories."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    categories = {entry["category"] for entry in manifest if "category" in entry}
    assert len(categories) >= 4, f"Expected at least 4 categories, found {categories}"


def test_all_manifest_images_exist_and_non_empty():
    """Verify that every image referenced in manifest exists on disk and is non-empty."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for entry in manifest:
        filename = entry["filename"]
        path = os.path.join(IMAGE_DIR, filename)
        assert os.path.exists(path), f"Image file {filename} does not exist at {path}"
        assert os.path.getsize(path) > 100, f"Image file {filename} is too small or empty ({os.path.getsize(path)} bytes)"
