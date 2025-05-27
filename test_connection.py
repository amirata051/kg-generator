from kafka import KafkaProducer

try:
    producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
    print("Kafka connection successful!")
except Exception as e:
    print(f"Kafka connection failed: {e}")
