# app/workers/worker.py
import os
import io
import json
import logging
from kafka import KafkaConsumer
from app.services.minio_client import minio_client, BUCKET_NAME
from unstructured.partition.auto import partition
from graphrag_sdk import KnowledgeGraph, KnowledgeGraphModelConfig
from falkordb import FalkorDB
from app.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    FALKORDB_HOST,
    FALKORDB_PORT,
    KG_NAME,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_message(task: dict):
    file_id = task["file_id"]
    object_name = task["object_name"]

    logger.info(f"Processing file_id={file_id}, object={object_name}")

    # 1) Download PDF from MinIO
    response = minio_client.get_object(BUCKET_NAME, object_name)
    pdf_bytes = response.read()
    local_path = f"/tmp/{object_name}"
    with open(local_path, "wb") as f:
        f.write(pdf_bytes)

    # 2) Extract elements via Unstructured-IO
    elements = partition(filename=local_path)
    logger.info(f"Extracted {len(elements)} elements from PDF")

    # 3) Initialize FalkorDB client
    fdb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)

    # 4) Initialize KnowledgeGraph
    kg = KnowledgeGraph(
        name=KG_NAME,
        model_config=KnowledgeGraphModelConfig(),
        falkordb_client=fdb
    )

    # 5) Ingest extracted elements into KG
    kg.ingest(elements)

    logger.info(f"Graph updated for file_id={file_id}")

def main():
    # 6) Start Kafka consumer
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="pdf_worker_group"
    )

    logger.info(f"Worker started, listening on topic='{KAFKA_TOPIC}'")
    for message in consumer:
        try:
            process_message(message.value)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

if __name__ == "__main__":
    main()
