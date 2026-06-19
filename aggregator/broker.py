import os
import redis.asyncio as redis
from schemas import EventSchema

BROKER_URL = os.getenv("BROKER_URL", "redis://localhost:6379/0")
QUEUE_NAME = "events_queue"

redis_client = redis.from_url(BROKER_URL, decode_responses=True)

async def publish_event_to_queue(event: EventSchema):
    await redis_client.rpush(QUEUE_NAME, event.model_dump_json())

async def publish_batch_to_queue(events: list[EventSchema]):
    if not events:
        return
    pipe = redis_client.pipeline()
    for ev in events:
        pipe.rpush(QUEUE_NAME, ev.model_dump_json())
    await pipe.execute()
