"""Private S3 storage and presigned URL adapter."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from pacific_bioarchive.domain.storage import ObjectInfo, PresignedPut


class S3ObjectStorage:
    def __init__(self, client: Any, *, bucket_name: str) -> None:
        if not bucket_name.strip():
            raise ValueError("bucket_name is required")
        self._client = client
        self.bucket_name = bucket_name

    def create_presigned_put(
        self,
        *,
        key: str,
        content_type: str,
        checksum_hex: str,
        file_id: str,
        expires_in: int = 900,
    ) -> PresignedPut:
        checksum_base64 = base64.b64encode(bytes.fromhex(checksum_hex)).decode("ascii")
        params = {
            "Bucket": self.bucket_name,
            "Key": key,
            "ContentType": content_type,
            "ChecksumSHA256": checksum_base64,
            "Metadata": {"file-id": file_id, "checksum-sha256": checksum_hex},
        }
        url = self._client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=expires_in, HttpMethod="PUT"
        )
        return PresignedPut(
            url=url,
            headers={
                "Content-Type": content_type,
                "x-amz-checksum-sha256": checksum_base64,
                "x-amz-meta-file-id": file_id,
                "x-amz-meta-checksum-sha256": checksum_hex,
            },
            expires_in=expires_in,
        )

    def create_presigned_get(self, key: str, *, expires_in: int = 900) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )

    def head(self, key: str) -> ObjectInfo:
        response = self._client.head_object(
            Bucket=self.bucket_name, Key=key, ChecksumMode="ENABLED"
        )
        return ObjectInfo(
            size_bytes=int(response["ContentLength"]),
            content_type=response.get("ContentType", "application/octet-stream"),
            checksum_sha256_base64=response.get("ChecksumSHA256"),
            metadata={str(k): str(v) for k, v in response.get("Metadata", {}).items()},
        )

    def download_file(self, key: str, destination: str | Path) -> None:
        self._client.download_file(self.bucket_name, key, str(destination))

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket_name, Key=key)
