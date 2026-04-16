from qdrant_client import QdrantClient
import os

DB_IP = "192.168.45.80"
QDRANT_PORT = 6333
COLLECTION_NAME = "osint_news"

client = QdrantClient(host=DB_IP, port=QDRANT_PORT)

try:
    count = client.count(collection_name=COLLECTION_NAME).count
    print(f"Total points in {COLLECTION_NAME}: {count}")
    
    # Get latest point
    points, _ = client.scroll(collection_name=COLLECTION_NAME, limit=1, with_payload=True)
    if points:
        print(f"Latest point payload: {points[0].payload}")
    else:
        print("No points found.")
except Exception as e:
    print(f"Error: {e}")
