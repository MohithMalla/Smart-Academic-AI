from abc import ABC, abstractmethod
from uuid import UUID


class BaseStorageProvider(ABC):
    """Abstract storage provider interface for managing document files."""

    @abstractmethod
    async def save_file(
        self,
        file_bytes: bytes,
        institution_id: UUID,
        course_id: UUID,
        original_filename: str
    ) -> str:
        """Save file bytes securely and return relative storage path."""
        pass

    @abstractmethod
    async def get_file(self, storage_path: str) -> bytes:
        """Retrieve stored file bytes by storage path."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete stored file by storage path."""
        pass
