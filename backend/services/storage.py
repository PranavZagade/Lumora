"""
Temporary storage service.

For Phase 1, we use local temp storage.
Cloudflare R2 integration will be added when deploying.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import json


# Local temp directory for development
TEMP_DIR = Path(__file__).parent.parent / "temp_data"
TEMP_DIR.mkdir(exist_ok=True)

# Session TTL in hours
SESSION_TTL_HOURS = 24


class TempStorage:
    """Temporary storage manager for datasets."""
    
    def __init__(self, base_dir: Path = TEMP_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get the directory for a session."""
        return self.base_dir / session_id
    
    def create_session(self, session_id: str) -> Path:
        """Create a new session directory."""
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(exist_ok=True)
        
        # Store metadata
        metadata = {
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).isoformat(),
        }
        with open(session_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        return session_dir
    
    def save_file(self, session_id: str, filename: str, content: bytes) -> Path:
        """Save a file to the session directory."""
        session_dir = self._get_session_dir(session_id)
        if not session_dir.exists():
            self.create_session(session_id)
        
        file_path = session_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path
    
    def get_file(self, session_id: str, filename: str) -> Optional[bytes]:
        """Retrieve a file from the session directory."""
        file_path = self._get_session_dir(session_id) / filename
        if file_path.exists():
            with open(file_path, "rb") as f:
                return f.read()
        return None
    
    def save_json(self, session_id: str, name: str, data: dict) -> Path:
        """Save JSON data to the session directory."""
        session_dir = self._get_session_dir(session_id)
        if not session_dir.exists():
            self.create_session(session_id)
        
        file_path = session_dir / f"{name}.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        return file_path
    
    def get_json(self, session_id: str, name: str) -> Optional[dict]:
        """Retrieve JSON data from the session directory."""
        file_path = self._get_session_dir(session_id) / f"{name}.json"
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data."""
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        removed = 0
        now = datetime.utcnow()
        
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if now > expires_at:
                        shutil.rmtree(session_dir)
                        removed += 1
                except Exception:
                    # If metadata is corrupt, remove the session
                    shutil.rmtree(session_dir)
                    removed += 1
        
        return removed


# Global storage instance
storage = TempStorage()



