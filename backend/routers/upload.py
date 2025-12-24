"""File upload router."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from models.schemas import UploadResponse, DatasetProfile, ErrorResponse
from services.storage import storage
from services.analyzer import analyze_dataframe, get_dataframe_from_bytes, generate_id

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Max file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def validate_file(file: UploadFile) -> None:
    """Validate the uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check extension
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("/", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel dataset.
    
    Returns dataset metadata and profile information.
    """
    # Validate file
    validate_file(file)
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate session ID
    session_id = generate_id()
    
    try:
        # Parse the file into a DataFrame
        df = get_dataframe_from_bytes(content, file.filename or "data.csv")
        
        # Analyze the DataFrame
        profile = analyze_dataframe(df, file.filename or "data.csv")
        
        # Update the dataset ID to match session
        profile["dataset"]["id"] = session_id
        
        # Save the raw file temporarily
        storage.save_file(session_id, file.filename or "data.csv", content)
        
        # Save the profile as JSON (this is what we'll use, not raw data)
        storage.save_json(session_id, "profile", profile)
        
        return UploadResponse(
            success=True,
            dataset_id=session_id,
            dataset=profile["dataset"],
            message=f"Successfully uploaded {file.filename}"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(dataset_id: str):
    """Get the profile of an uploaded dataset."""
    profile = storage.get_json(dataset_id, "profile")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return DatasetProfile(**profile)


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset and all associated data."""
    if storage.delete_session(dataset_id):
        return {"success": True, "message": "Dataset deleted"}
    else:
        raise HTTPException(status_code=404, detail="Dataset not found")


