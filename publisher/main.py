import os
import time
import uuid
import random
import requests
from datetime import datetime, timezone

TARGET_URL = os.getenv("TARGET_URL", "http://localhost:8080/publish")

# Cache to store sent events to intentionally create duplicates
sent_events = []

def generate_events(batch_size=10):
    global sent_events
    events = []
    topics = ["auth", "payment", "user_activity", "system"]
    
    for _ in range(batch_size):
        # 30% chance to duplicate an existing event to test idempotency
        if sent_events and random.random() < 0.3:
            events.append(random.choice(sent_events))
        else:
            event = {
                "topic": random.choice(topics),
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "simulator_publisher",
                "payload": {"random_val": random.randint(1, 100)}
            }
            events.append(event)
            sent_events.append(event)
            
            # Keep cache size manageable
            if len(sent_events) > 1000:
                sent_events = sent_events[-1000:]
                
    return events

def main():
    print(f"Publisher started. Target URL: {TARGET_URL}")
    
    # Give aggregator time to start
    time.sleep(5)
    
    while True:
        try:
            events = generate_events(batch_size=random.randint(10, 50))
            response = requests.post(TARGET_URL, json=events, timeout=5)
            print(f"Sent {len(events)} events, Status: {response.status_code}")
            time.sleep(0.5) # Fast publish rate
        except Exception as e:
            print(f"Error publishing: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
