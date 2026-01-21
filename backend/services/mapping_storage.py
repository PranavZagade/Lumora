"""
Mapping Storage Service.

Stores semantic concept → column name mappings per dataset.
CORE PRINCIPLE: Only metadata (concept → column), no data values.
"""

from typing import Dict, Optional
import logging
from services.storage import storage

logger = logging.getLogger(__name__)


def get_mappings(dataset_id: str) -> Dict[str, str]:
    """
    Get all semantic mappings for a dataset.
    
    Returns: {concept: column_name}
    """
    mappings_data = storage.get_json(dataset_id, "semantic_mappings")
    if not mappings_data:
        return {}
    
    return mappings_data.get("mappings", {})


def save_mapping(
    dataset_id: str,
    concept: str,
    column_name: str
) -> None:
    """
    Save a semantic mapping for a dataset.
    
    Args:
        dataset_id: Dataset identifier
        concept: Semantic concept (e.g., "rating", "country")
        column_name: Column name that represents this concept
    """
    mappings_data = storage.get_json(dataset_id, "semantic_mappings") or {}
    mappings = mappings_data.get("mappings", {})
    
    mappings[concept] = column_name
    
    mappings_data["mappings"] = mappings
    
    storage.save_json(dataset_id, "semantic_mappings", mappings_data)
    
    logger.info(f"Saved mapping for dataset {dataset_id}: {concept} → {column_name}")


def save_mappings(
    dataset_id: str,
    mappings: Dict[str, str]
) -> None:
    """
    Save multiple semantic mappings at once.
    
    Args:
        dataset_id: Dataset identifier
        mappings: {concept: column_name}
    """
    mappings_data = storage.get_json(dataset_id, "semantic_mappings") or {}
    existing_mappings = mappings_data.get("mappings", {})
    
    # Merge with existing mappings
    existing_mappings.update(mappings)
    
    mappings_data["mappings"] = existing_mappings
    
    storage.save_json(dataset_id, "semantic_mappings", mappings_data)
    
    logger.info(f"Saved {len(mappings)} mappings for dataset {dataset_id}")


def delete_mapping(
    dataset_id: str,
    concept: str
) -> None:
    """
    Delete a semantic mapping.
    """
    mappings_data = storage.get_json(dataset_id, "semantic_mappings")
    if not mappings_data:
        return
    
    mappings = mappings_data.get("mappings", {})
    if concept in mappings:
        del mappings[concept]
        mappings_data["mappings"] = mappings
        storage.save_json(dataset_id, "semantic_mappings", mappings_data)
        logger.info(f"Deleted mapping for dataset {dataset_id}: {concept}")


