# app/api/upload.py
import io
import uuid
import hashlib
import logging

from fastapi import APIRouter, UploadFile, HTTPException, status
from minio.error import S3Error
from app.services.minio_client import minio_client, BUCKET_NAME
from app.services.kafka_producer import producer, KAFKA_TOPIC
from app.services.redis_client import redis_client, FILES_SET

router = APIRouter()
logger = logging.getLogger(__name__)

def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest for given bytes."""
    return hashlib.sha256(data).hexdigest()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile):
    # Only accept PDF files
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Read the entire file into memory
    data = await file.read()
    file_hash = sha256_hex(data)

    # Check if this file hash has been seen before
    if redis_client.sismember(FILES_SET, file_hash):
        logger.info(f"Duplicate upload skipped: hash={file_hash}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This file has already been uploaded."
        )

    # Generate a unique object name for MinIO
    file_id = str(uuid.uuid4())
    object_name = f"{file_id}.pdf"

    # Upload to MinIO
    try:
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type="application/pdf"
        )
    except S3Error as e:
        logger.error(f"MinIO upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"MinIO upload error: {e}")

    # Enqueue processing task in Kafka
    message = {
        "file_id": file_id,
        "bucket": BUCKET_NAME,
        "object_name": object_name
    }
    logger.info(f"Sending message to Kafka: {message}")
    try:
        future = producer.send(KAFKA_TOPIC, message)
        record_metadata = future.get(timeout=10)
        logger.info(
            f"Message delivered to {record_metadata.topic} "
            f"partition {record_metadata.partition} offset {record_metadata.offset}"
        )
    except Exception as e:
        logger.error(f"Failed to deliver message: {e}", exc_info=True)
        # Optional: roll back MinIO upload if desired
        raise HTTPException(status_code=500, detail=f"Kafka produce error: {e}")

    # Mark this file hash as seen
    redis_client.sadd(FILES_SET, file_hash)

    return {
        "file_id": file_id,
        "detail": "File uploaded successfully. Processing started."
    }
