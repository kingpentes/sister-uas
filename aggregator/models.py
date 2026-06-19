from sqlalchemy import Column, String, JSON, DateTime, Integer, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String, nullable=False, index=True)
    event_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    source = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('topic', 'event_id', name='uq_topic_event_id'),
    )

class Stats(Base):
    __tablename__ = "stats"

    # We will just use a single row for global stats, id=1
    id = Column(Integer, primary_key=True, autoincrement=True)
    received = Column(Integer, default=0, nullable=False)
    unique_processed = Column(Integer, default=0, nullable=False)
    duplicate_dropped = Column(Integer, default=0, nullable=False)
