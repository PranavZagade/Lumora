"""
Semantic Mappings API Router.

Handles storing and retrieving semantic concept → column mappings.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from services.mapping_storage import (
    get_mappings,
    save_mapping,
    save_mappings,
    delete_mapping
)
from services.storage import storage

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


class MappingRequest(BaseModel):
    """Request to save a mapping."""
    concept: str
    column_name: str


class MappingsRequest(BaseModel):
    """Request to save multiple mappings."""
    mappings: Dict[str, str]


@router.get("/{dataset_id}")
async def get_dataset_mappings(dataset_id: str) -> Dict[str, Any]:
    """Get all semantic mappings for a dataset."""
    # Verify dataset exists
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    mappings = get_mappings(dataset_id)
    
    return {
        "dataset_id": dataset_id,
        "mappings": mappings,
    }


@router.post("/{dataset_id}")
async def save_dataset_mapping(
    dataset_id: str,
    request: MappingRequest
) -> Dict[str, Any]:
    """Save a single semantic mapping."""
    # Verify dataset exists
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Verify column exists
    columns = profile_data.get("columns", [])
    column_names = [col.get("name", "") for col in columns]
    
    if request.column_name not in column_names:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{request.column_name}' not found in dataset"
        )
    
    # Save mapping
    save_mapping(dataset_id, request.concept, request.column_name)
    
    return {
        "dataset_id": dataset_id,
        "concept": request.concept,
        "column_name": request.column_name,
        "success": True,
    }


@router.post("/{dataset_id}/bulk")
async def save_dataset_mappings(
    dataset_id: str,
    request: MappingsRequest
) -> Dict[str, Any]:
    """Save multiple semantic mappings at once."""
    # Verify dataset exists
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Verify all columns exist
    columns = profile_data.get("columns", [])
    column_names = [col.get("name", "") for col in columns]
    
    invalid_columns = [
        col for col in request.mappings.values()
        if col not in column_names
    ]
    
    if invalid_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Columns not found in dataset: {invalid_columns}"
        )
    
    # Save mappings
    save_mappings(dataset_id, request.mappings)
    
    return {
        "dataset_id": dataset_id,
        "mappings": request.mappings,
        "success": True,
    }


@router.delete("/{dataset_id}/{concept}")
async def delete_dataset_mapping(
    dataset_id: str,
    concept: str
) -> Dict[str, Any]:
    """Delete a semantic mapping."""
    # Verify dataset exists
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Delete mapping
    delete_mapping(dataset_id, concept)
    
    return {
        "dataset_id": dataset_id,
        "concept": concept,
        "success": True,
    }

