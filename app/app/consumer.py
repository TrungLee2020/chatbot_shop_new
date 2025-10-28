"""
Kafka Consumer - Background worker to process messages
Run separately from main API
"""
import logging
from app.services.kafka_service import kafka_service
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_chat_request(data: dict):
    """
    Process chat request from Kafka
    
    This is where you can add additional processing:
    - Analytics
    - Logging to MongoDB
    - Trigger notifications
    - etc.
    """
    logger.info(f"Processing chat request: {data['message_id']}")
    logger.info(f"  Session: {data['session_id']}")
    logger.info(f"  User: {data['user_id']}")
    logger.info(f"  Message: {data['message']}")
    
    # TODO: Add your processing logic here
    # - Save to MongoDB
    # - Send to analytics
    # - etc.


def process_chat_response(data: dict):
    """
    Process chat response from Kafka
    """
    logger.info(f"Processing chat response: {data['message_id']}")
    logger.info(f"  Response: {data['response'][:50]}...")
    
    # TODO: Add your processing logic here


def main():
    """Main consumer loop"""
    logger.info("🔄 Starting Kafka consumer...")
    
    # Consume chat requests
    kafka_service.consume_messages(
        topics=[
            settings.KAFKA_TOPIC_CHAT_REQUESTS,
            settings.KAFKA_TOPIC_CHAT_RESPONSES
        ],
        callback=lambda data: (
            process_chat_request(data) 
            if 'message' in data 
            else process_chat_response(data)
        )
    )


if __name__ == "__main__":
    main()