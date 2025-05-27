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
    # Only PDF files are allowed
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Generate a unique file identifier
    file_id = str(uuid.uuid4())
    object_name = f"{file_id}.pdf"

    # Read file bytes
    data = await file.read()

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

    # Prepare message for Kafka
    message = {
        "file_id": file_id,
        "bucket": BUCKET_NAME,
        "object_name": object_name
    }

    # Send message to Kafka
    try:
        producer.send(KAFKA_TOPIC, message)
        producer.flush()
        logger.info(f"Message sent to Kafka topic {KAFKA_TOPIC}: {message}")
    except Exception as e:
        logger.error(f"Kafka produce failed: {e}")
        raise HTTPException(status_code=500, detail=f"Kafka produce error: {e}")

    # Return response to client
    return {
        "file_id": file_id,
        "detail": "File uploaded successfully. Processing started."
    }
