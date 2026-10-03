import os
from pathlib import Path
from typing import Any, Dict
from app.core.config import settings
from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_BASE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        return self.base_path / key.lstrip("/\\")

    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int,
        expires_in: int = 3600,
    ) -> Dict[str, Any]:
        # For local development, generate path under local storage and point to local stream endpoint
        dest_path = self._get_full_path(key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Local upload endpoint simulated
        upload_url = f"/api/v1/videos/local-upload?storage_key={key}"
        return {
            "upload_url": upload_url,
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "fields": {},
            "expires_in": expires_in,
        }

    async def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
    ) -> str:
        return f"/api/v1/videos/local-download?storage_key={key}"

    async def object_exists(self, key: str) -> bool:
        path = self._get_full_path(key)
        return path.exists() and path.is_file() and path.stat().st_size > 0

    async def get_object_metadata(self, key: str) -> Dict[str, Any]:
        path = self._get_full_path(key)
        if not path.exists():
            return {}
        stat = path.stat()
        return {
            "content_length": stat.st_size,
            "last_modified": stat.st_mtime,
        }

    async def delete_object(self, key: str) -> bool:
        path = self._get_full_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    async def upload_file(
        self, local_path: str, remote_key: str, content_type: str = "application/octet-stream"
    ) -> str:
        dest_path = self._get_full_path(remote_key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copyfile(local_path, dest_path)
        return str(dest_path)

    async def download_file(self, remote_key: str, local_path: str) -> str:
        source_path = self._get_full_path(remote_key)
        if not source_path.exists():
            raise FileNotFoundError(f"Storage key {remote_key} not found")
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copyfile(source_path, local_path)
        return local_path

    async def list_objects(self, prefix: str) -> list:
        prefix_path = self._get_full_path(prefix)
        base = self.base_path
        results = []
        if prefix_path.is_dir():
            for p in prefix_path.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(base).as_posix()
                    results.append(rel)
        elif prefix_path.parent.exists():
            for p in prefix_path.parent.glob(f"{prefix_path.name}*"):
                if p.is_file():
                    rel = p.relative_to(base).as_posix()
                    results.append(rel)
        return results
