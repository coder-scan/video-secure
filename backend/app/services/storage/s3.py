from typing import Any, Dict
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.services.storage.base import StorageProvider


class S3CompatibleStorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint_url: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        region_name: str = None,
        bucket_name: str = None,
    ):
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL or None
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.S3_REGION_NAME or "auto"
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4"),
        )

    async def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int,
        expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Generates a presigned PUT URL for direct client streaming."""
        params = {
            "Bucket": self.bucket_name,
            "Key": key,
            "ContentType": content_type,
        }
        url = self.client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expires_in,
        )
        return {
            "upload_url": url,
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
        url = self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def get_object_metadata(self, key: str) -> Dict[str, Any]:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                "content_length": response.get("ContentLength", 0),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError:
            return {}

    async def delete_object(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def upload_file(
        self, local_path: str, remote_key: str, content_type: str = "application/octet-stream"
    ) -> str:
        self.client.upload_file(
            Filename=local_path,
            Bucket=self.bucket_name,
            Key=remote_key,
            ExtraArgs={"ContentType": content_type},
        )
        return remote_key

    async def download_file(self, remote_key: str, local_path: str) -> str:
        from pathlib import Path
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(
            Bucket=self.bucket_name,
            Key=remote_key,
            Filename=local_path,
        )
        return local_path

    async def list_objects(self, prefix: str) -> list:
        paginator = self.client.get_paginator("list_objects_v2")
        results = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                results.append(obj["Key"])
        return results
