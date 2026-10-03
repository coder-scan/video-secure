from abc import ABC, abstractmethod
from typing import Any, Dict


class StorageProvider(ABC):
    @abstractmethod
    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int,
        expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Generates direct client upload URL or signed post parameters."""
        pass

    @abstractmethod
    async def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
    ) -> str:
        """Generates short-lived download URL for secure ingestion."""
        pass

    @abstractmethod
    async def object_exists(self, key: str) -> bool:
        """Checks if key exists in storage."""
        pass

    @abstractmethod
    async def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """Retrieves size, content headers, etc."""
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Deletes raw or processed object."""
        pass

    @abstractmethod
    async def upload_file(
        self, local_path: str, remote_key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """Uploads a local file to storage at remote_key."""
        pass

    @abstractmethod
    async def download_file(self, remote_key: str, local_path: str) -> str:
        """Downloads a remote object to a local file."""
        pass

    @abstractmethod
    async def list_objects(self, prefix: str) -> list:
        """Lists object keys starting with prefix."""
        pass
