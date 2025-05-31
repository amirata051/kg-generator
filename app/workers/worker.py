# app/workers/worker.py
import io
import json
import logging
import hashlib

from kafka import KafkaConsumer
from app.services.minio_client import minio_client, BUCKET_NAME
from app.services.redis_client import redis_client, ELEMENTS_SET
from unstructured.partition.auto import partition
from graphrag_sdk import KnowledgeGraph, KnowledgeGraphModelConfig, Ontology
from graphrag_sdk.models.litellm import LiteModel
from graphrag_sdk.source import Source_FromRawText
from app.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    FALKORDB_HOST,
    FALKORDB_PORT,
    KG_NAME,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest for given bytes."""
    return hashlib.sha256(data).hexdigest()

def process_message(task: dict):
    file_id = task["file_id"]
    object_name = task["object_name"]
    logger.info(f"Processing file_id={file_id}, object={object_name}")

    # 1) Download PDF from MinIO
    response = minio_client.get_object(BUCKET_NAME, object_name)
    pdf_bytes = response.read()

    # 2) Save to local temp file for partitioning
    local_path = f"/tmp/{object_name}"
    with open(local_path, "wb") as f:
        f.write(pdf_bytes)

    # 3) Extract elements from PDF
    elements = partition(filename=local_path)
    logger.info(f"Extracted {len(elements)} elements")

    # 4) Filter elements by text-hash only
    new_texts = []
    for el in elements:
        if not hasattr(el, "text"):
            continue
        text_bytes = el.text.encode("utf-8")
        elem_hash = sha256_hex(text_bytes)
        # if this text hasn't been processed before, keep it
        if not redis_client.sismember(ELEMENTS_SET, elem_hash):
            redis_client.sadd(ELEMENTS_SET, elem_hash)
            new_texts.append(el.text)

    # 5) If no new text found, skip further processing
    if not new_texts:
        logger.info("No new content found; skipping incremental update.")
        return

    # 6) Build ontology from only the new texts
    full_text = " ".join(new_texts)
    source = Source_FromRawText(full_text)
    model = LiteModel(model_name="gemini/gemini-2.0-flash")
    ontology = Ontology.from_sources(sources=[source], model=model)
    logger.info("Ontology created for new content")

    # 7) Ingest incrementally via process_sources
    model_config = KnowledgeGraphModelConfig.with_model(model)
    kg = KnowledgeGraph(
        name=KG_NAME,
        model_config=model_config,
        ontology=ontology,
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
    )
    kg.process_sources(sources=[source])
    logger.info("Graph updated with incremental content")

def main():
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
