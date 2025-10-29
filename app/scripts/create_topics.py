"""
Create Kafka topics
"""
import sys
import os

# ✅ ADD THIS: Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from app.config import settings

def create_topics():
    """Create required Kafka topics"""
    admin_client = KafkaAdminClient(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
    )
    
    topics = [
        NewTopic(
            name=settings.KAFKA_TOPIC_CHAT_REQUESTS,
            num_partitions=3,
            replication_factor=1
        ),
        NewTopic(
            name=settings.KAFKA_TOPIC_CHAT_RESPONSES,
            num_partitions=3,
            replication_factor=1
        )
    ]
    
    try:
        admin_client.create_topics(new_topics=topics, validate_only=False)
        print("✅ Topics created successfully")
        print(f"  - {settings.KAFKA_TOPIC_CHAT_REQUESTS}")
        print(f"  - {settings.KAFKA_TOPIC_CHAT_RESPONSES}")
    except TopicAlreadyExistsError:
        print("⚠️  Topics already exist")
    except Exception as e:
        print(f"❌ Error creating topics: {e}")
    finally:
        admin_client.close()

if __name__ == "__main__":
    create_topics()