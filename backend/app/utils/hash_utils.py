"""Hash utilities for change detection in incremental updates."""
import hashlib
import json
from typing import Dict, Any


def compute_row_hash(row_dict: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of CSV row for change detection.

    Args:
        row_dict: CSV row as dictionary

    Returns:
        str: SHA256 hash (hex string)

    Excludes from hash:
    - created_at, updated_at (metadata)
    - embedding (always regenerate)
    - row_hash (circular dependency)

    Purpose:
    - Skip update if hash unchanged (no data changes)
    - Save embedding generation cost for unchanged rows
    """
    # Exclude metadata fields
    excluded_fields = {"created_at", "updated_at", "embedding", "row_hash",
                      "embedding_model_version", "embedding_generated_at"}

    # Create sorted dict for consistent hashing
    hashable_data = {
        k: v for k, v in sorted(row_dict.items())
        if k not in excluded_fields
    }

    # Serialize to JSON (deterministic order)
    json_str = json.dumps(hashable_data, sort_keys=True, ensure_ascii=False)

    # Compute SHA256 hash
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    return hash_obj.hexdigest()


def has_row_changed(new_row: Dict[str, Any], existing_hash: str) -> bool:
    """
    Check if CSV row has changed since last ingestion.

    Args:
        new_row: New CSV row data
        existing_hash: Hash from existing Neo4j node

    Returns:
        bool: True if row changed, False if unchanged
    """
    new_hash = compute_row_hash(new_row)
    return new_hash != existing_hash
