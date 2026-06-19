import asyncio
import logging
import time
from typing import List, Union
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, text

from database import engine, Base, get_db, AsyncSessionLocal
from models import Stats, ProcessedEvent
from schemas import EventSchema, StatsResponse
from broker import publish_event_to_queue, publish_batch_to_queue
from worker import consumer_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pub-Sub Log Aggregator")

START_TIME = time.time()
consumer_tasks = []

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        # Auto-create tables
        await conn.run_sync(Base.metadata.create_all)
        
    # Initialize Stats row if not exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stats).where(Stats.id == 1))
        stat_row = result.scalar_one_or_none()
        if not stat_row:
            session.add(Stats(id=1, received=0, unique_processed=0, duplicate_dropped=0))
            await session.commit()
            
    # Start consumer workers (multiple threads/coroutines for concurrency demonstration)
    global consumer_tasks
    NUM_WORKERS = 3
    for _ in range(NUM_WORKERS):
        task = asyncio.create_task(consumer_loop())
        consumer_tasks.append(task)

@app.on_event("shutdown")
async def shutdown_event():
    for task in consumer_tasks:
        task.cancel()
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    await engine.dispose()

@app.get("/")
async def read_root():
    return {"message": "Aggregator API is running"}

@app.post("/publish")
async def publish_events(events: Union[EventSchema, List[EventSchema]], db: AsyncSession = Depends(get_db)):
    if not isinstance(events, list):
        events = [events]
        
    # Increment received atomically
    await db.execute(update(Stats).where(Stats.id == 1).values(received=Stats.received + len(events)))
    await db.commit()
    
    # Push to queue
    await publish_batch_to_queue(events)
    
    return {"status": "accepted", "count": len(events)}

@app.get("/events", response_model=List[EventSchema])
async def get_events(topic: str = None, db: AsyncSession = Depends(get_db)):
    query = select(ProcessedEvent)
    if topic:
        query = query.where(ProcessedEvent.topic == topic)
    query = query.order_by(ProcessedEvent.timestamp.desc()).limit(100)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [EventSchema.model_validate(e, from_attributes=True) for e in events]

@app.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Get stats
    result = await db.execute(select(Stats).where(Stats.id == 1))
    stat_row = result.scalar_one_or_none()
    
    # Get distinct topics count
    topic_result = await db.execute(select(func.count(func.distinct(ProcessedEvent.topic))))
    topics_count = topic_result.scalar() or 0
    
    uptime = time.time() - START_TIME
    
    return StatsResponse(
        received=stat_row.received if stat_row else 0,
        unique_processed=stat_row.unique_processed if stat_row else 0,
        duplicate_dropped=stat_row.duplicate_dropped if stat_row else 0,
        topics=topics_count,
        uptime_seconds=uptime
    )
