# app/api/upload.py
import io
import uuid
import logging
from fastapi import APIRouter, UploadFile, HTTPException, status
from minio.error import S3Error
from app.services.minio_client import minio_client, BUCKET_NAME
from app.services.kafka_producer import producer, KAFKA_TOPIC

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile):
    logger.info(f"KAFKA_BOOTSTRAP_SERVERS: {producer.config['bootstrap_servers']}")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_id = str(uuid.uuid4())
    object_name = f"{file_id}.pdf"
    data = await file.read()

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

    message = {
        "file_id": file_id,
        "bucket": BUCKET_NAME,
        "object_name": object_name
    }

    logger.info(f"Sending message to Kafka: {message}")

    try:
        future = producer.send(KAFKA_TOPIC, message)
        record_metadata = future.get(timeout=10)  # wait synchronously for confirmation
        logger.info(f"Message delivered to {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
    except Exception as e:
        logger.error(f"Failed to deliver message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Kafka produce error: {e}")

    return {
        "file_id": file_id,
        "detail": "File uploaded successfully. Processing started."
    }
