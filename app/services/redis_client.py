# app/services/redis_client.py
import redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Redis set names
FILES_SET = "processed_files"
ELEMENTS_SET = "processed_elements"
