import asyncio
import logging
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from database import AsyncSessionLocal
from models import ProcessedEvent, Stats
from schemas import EventSchema
from broker import redis_client, QUEUE_NAME

logger = logging.getLogger(__name__)

async def process_event(event: EventSchema):
    async with AsyncSessionLocal() as session:
        # Atomic Idempotent Insert using PostgreSQL ON CONFLICT DO NOTHING
        stmt = insert(ProcessedEvent).values(
            topic=event.topic,
            event_id=event.event_id,
            timestamp=event.timestamp,
            source=event.source,
            payload=event.payload
        ).on_conflict_do_nothing(
            index_elements=['topic', 'event_id']
        )
        
        result = await session.execute(stmt)
        inserted = result.rowcount > 0
        
        # Update stats
        if inserted:
            await session.execute(update(Stats).where(Stats.id == 1).values(unique_processed=Stats.unique_processed + 1))
        else:
            await session.execute(update(Stats).where(Stats.id == 1).values(duplicate_dropped=Stats.duplicate_dropped + 1))
            
        await session.commit()

async def consumer_loop():
    logger.info("Starting background consumer loop...")
    while True:
        try:
            # BLPOP blocks until an item is available
            result = await redis_client.blpop(QUEUE_NAME, timeout=1)
            if result:
                _, event_json = result
                event = EventSchema.model_validate_json(event_json)
                await process_event(event)
        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            await asyncio.sleep(1)
