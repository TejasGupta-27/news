import io
import os
import tempfile

from minio import Minio

from app.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def upload_directory(local_dir: str, bucket: str, prefix: str):
    client = get_minio_client()
    for root, _, files in os.walk(local_dir):
        for f in files:
            local_path = os.path.join(root, f)
            object_name = os.path.join(prefix, os.path.relpath(local_path, local_dir))
            client.fput_object(bucket, object_name, local_path)


def download_directory(bucket: str, prefix: str, local_dir: str):
    client = get_minio_client()
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    for obj in objects:
        rel_path = obj.object_name[len(prefix):].lstrip("/")
        local_path = os.path.join(local_dir, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client.fget_object(bucket, obj.object_name, local_path)


def upload_bytes(data: bytes, bucket: str, object_name: str):
    client = get_minio_client()
    client.put_object(bucket, object_name, io.BytesIO(data), len(data))


def download_to_tempdir(bucket: str, prefix: str) -> str:
    tmp = tempfile.mkdtemp()
    download_directory(bucket, prefix, tmp)
    return tmp
