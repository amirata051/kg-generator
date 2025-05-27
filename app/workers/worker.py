# app/workers/worker.py
import io
import json
import logging
from kafka import KafkaConsumer
from app.services.minio_client import minio_client, BUCKET_NAME
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

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_message(task: dict):
    file_id = task["file_id"]
    object_name = task["object_name"]

    logger.info(f"Processing file_id={file_id}, object={object_name}")

    # 1) Download PDF from MinIO storage
    response = minio_client.get_object(BUCKET_NAME, object_name)
    pdf_bytes = response.read()

    local_path = f"/tmp/{object_name}"
    with open(local_path, "wb") as f:
        f.write(pdf_bytes)

    # 2) Extract elements from PDF using unstructured-io
    elements = partition(filename=local_path)
    logger.info(f"Extracted {len(elements)} elements from PDF")

    # 3) Concatenate all text elements for ontology creation
    full_text = " ".join([element.text for element in elements if hasattr(element, "text")])

    # 4) Create a Source object from raw text (required by Ontology.from_sources)
    source = Source_FromRawText(full_text)

    # 5) Initialize the LLM model (using Gemini model)
    model = LiteModel(model_name="gemini/gemini-2.0-flash")

    # 6) Create Ontology from the source text and model
    ontology = Ontology.from_sources(sources=[source], model=model)
    logger.info("Ontology created from extracted text")

    # Optional: save ontology JSON to disk for debugging
    with open("/tmp/ontology.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(ontology.to_json(), indent=2))

    # 7) Setup KnowledgeGraphModelConfig with the initialized model
    model_config = KnowledgeGraphModelConfig.with_model(model)

    # 8) Initialize KnowledgeGraph instance with ontology and FalkorDB connection details
    kg = KnowledgeGraph(
        name=KG_NAME,
        model_config=model_config,
        ontology=ontology,
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        # username and password optional, add if needed
    )

    # 9) Ingest extracted elements into the KnowledgeGraph (stores in FalkorDB)
    # kg.ingest(elements)
    kg.process_sources(sources=[source])

    logger.info(f"Graph updated for file_id={file_id}")

def main():
    # Initialize Kafka consumer with necessary configurations
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="pdf_worker_group"
    )

    logger.info(f"Worker started, listening on topic='{KAFKA_TOPIC}'")

    # Consume messages continuously from Kafka topic and process them
    for message in consumer:
        try:
            process_message(message.value)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

if __name__ == "__main__":
    main()
