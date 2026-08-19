import os
import uuid
from pathlib import Path
from uuid import UUID
from app.services.storage.base import BaseStorageProvider

STORAGE_BASE_DIR = Path(os.getenv("STORAGE_BASE_DIR", "./storage_data")).resolve()


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage implementation with strict path traversal prevention."""

    def __init__(self, base_dir: Path = STORAGE_BASE_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(
        self,
        file_bytes: bytes,
        institution_id: UUID,
        course_id: UUID,
        original_filename: str
    ) -> str:
        # Extract extension safely
        ext = Path(original_filename).suffix.lower()
        # Generate safe UUID4 filename, preventing path traversal attacks
        safe_filename = f"{uuid.uuid4()}{ext}"
        
        rel_path = Path(str(institution_id)) / str(course_id) / safe_filename
        full_path = (self.base_dir / rel_path).resolve()
        
        # Verify resolved path remains inside base_dir
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attack detected in storage resolution")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(file_bytes)

        return str(rel_path).replace("\\", "/")

    async def get_file(self, storage_path: str) -> bytes:
        full_path = (self.base_dir / storage_path).resolve()
        if not str(full_path).startswith(str(self.base_dir)) or not full_path.exists():
            raise FileNotFoundError(f"File not found in storage: {storage_path}")
        
        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, storage_path: str) -> bool:
        full_path = (self.base_dir / storage_path).resolve()
        if str(full_path).startswith(str(self.base_dir)) and full_path.exists():
            full_path.unlink()
            return True
        return False
