# app/services/kafka_producer.py
import json
from kafka import KafkaProducer
from app.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

TOPIC = KAFKA_TOPIC
