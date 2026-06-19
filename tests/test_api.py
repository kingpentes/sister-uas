import pytest
import requests
import uuid
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8080"

def wait_for_service():
    """Wait for aggregator service to be available."""
    max_retries = 30
    for _ in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/")
            if resp.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_service_is_up():
    assert wait_for_service(), "Aggregator API did not start in time."

def generate_event(topic="test_topic"):
    return {
        "topic": topic,
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "pytest",
        "payload": {"data": "test"}
    }

def test_root_endpoint():
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Aggregator API is running"

def test_publish_single_event():
    event = generate_event("topic1")
    resp = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["count"] == 1

def test_publish_batch_events():
    events = [generate_event("topic_batch") for _ in range(3)]
    resp = requests.post(f"{BASE_URL}/publish", json=events)
    assert resp.status_code == 200
    assert resp.json()["count"] == 3

def test_publish_invalid_schema_missing_topic():
    event = generate_event()
    del event["topic"]
    resp = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp.status_code == 422 # Validation Error

def test_publish_invalid_schema_missing_timestamp():
    event = generate_event()
    del event["timestamp"]
    resp = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp.status_code == 422

def test_publish_invalid_schema_bad_payload():
    event = generate_event()
    event["payload"] = "Not a dict"
    resp = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp.status_code == 422

def test_deduplication_exact_event():
    event = generate_event("dedup_test")
    # Send first time
    resp1 = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp1.status_code == 200
    
    # Give worker time to process
    time.sleep(1.5)
    
    stats_before = requests.get(f"{BASE_URL}/stats").json()
    
    # Send exactly the same event
    resp2 = requests.post(f"{BASE_URL}/publish", json=event)
    assert resp2.status_code == 200
    
    # Wait for processing
    time.sleep(1.5)
    
    stats_after = requests.get(f"{BASE_URL}/stats").json()
    
    # unique_processed should NOT have incremented for this event, 
    # but duplicate_dropped should have incremented.
    assert stats_after["duplicate_dropped"] > stats_before["duplicate_dropped"]

def test_get_events_list():
    resp = requests.get(f"{BASE_URL}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)

def test_get_events_filter_by_topic():
    unique_topic = str(uuid.uuid4())
    event = generate_event(unique_topic)
    requests.post(f"{BASE_URL}/publish", json=event)
    
    time.sleep(1) # wait for worker
    
    resp = requests.get(f"{BASE_URL}/events", params={"topic": unique_topic})
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["topic"] == unique_topic

def test_stats_consistency():
    resp = requests.get(f"{BASE_URL}/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "received" in stats
    assert "unique_processed" in stats
    assert "duplicate_dropped" in stats
    assert "uptime_seconds" in stats
    assert stats["received"] >= stats["unique_processed"] + stats["duplicate_dropped"]

def test_concurrency_same_event_multiple_times():
    # Send same event 10 times concurrently to test race conditions
    event = generate_event("concurrent_test")
    import concurrent.futures
    import asyncio
    
    async def send_req():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: requests.post(f"{BASE_URL}/publish", json=event))

    async def run_concurrent():
        tasks = [send_req() for _ in range(10)]
        return await asyncio.gather(*tasks)

    loop = asyncio.get_event_loop()
    responses = loop.run_until_complete(run_concurrent())
    
    for r in responses:
        assert r.status_code == 200
        
    time.sleep(2) # Wait for all to be processed
    
    resp = requests.get(f"{BASE_URL}/events", params={"topic": "concurrent_test"})
    assert resp.status_code == 200
    events = resp.json()
    
    # Should only be processed EXACTLY once
    assert len(events) == 1

def test_batch_stress_small():
    events = [generate_event("stress") for _ in range(50)]
    # Intentionally add duplicates
    events.extend(events[:10]) 
    
    resp = requests.post(f"{BASE_URL}/publish", json=events)
    assert resp.status_code == 200
    
    time.sleep(3)
    
    resp_events = requests.get(f"{BASE_URL}/events", params={"topic": "stress"})
    assert resp_events.status_code == 200
    # Even though we sent 60 (50 unique + 10 dupes), only 50 should be stored
    assert len(resp_events.json()) == 50
