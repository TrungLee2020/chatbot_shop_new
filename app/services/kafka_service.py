"""
Kafka Producer and Consumer
"""
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import logging
from typing import Callable
import time

from config import settings

logger = logging.getLogger(__name__)


class KafkaService:
    """Kafka Producer and Consumer wrapper"""
    
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(',')
        self.producer = None
        self.consumer = None
    
    def get_producer(self) -> KafkaProducer:
        """Get Kafka producer with retry logic"""
        if not self.producer:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.producer = KafkaProducer(
                        bootstrap_servers=self.bootstrap_servers,
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        key_serializer=lambda k: k.encode('utf-8') if k else None,
                        acks='all',
                        retries=3,
                        max_block_ms=5000  # ✅ Timeout để không block forever
                    )
                    logger.info("✅ Kafka producer initialized")
                    break
                except Exception as e:
                    logger.error(f"❌ Kafka connection attempt {attempt+1} failed: {e}")
                    if attempt == max_retries - 1:
                        logger.warning("⚠️ Kafka not available - running without Kafka")
                        raise
                    time.sleep(2)
        
        return self.producer
    
    def send_message(self, topic: str, message: dict, key: str = None):
        """
        Send message to Kafka topic
        
        Args:
            topic: Kafka topic name
            message: Message data (dict)
            key: Optional partition key
        """
        producer = self.get_producer()
        
        try:
            future = producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"✅ Message sent to {record_metadata.topic} "
                f"partition {record_metadata.partition} "
                f"offset {record_metadata.offset}"
            )
            
        except KafkaError as e:
            logger.error(f"❌ Failed to send message: {e}")
            raise
    
    def send_chat_request(self, data: dict):
        """Send to chat-requests topic"""
        self.send_message(
            topic=settings.KAFKA_TOPIC_CHAT_REQUESTS,
            message=data,
            key=data.get("session_id")
        )
    
    def send_chat_response(self, data: dict):
        """Send to chat-responses topic"""
        self.send_message(
            topic=settings.KAFKA_TOPIC_CHAT_RESPONSES,
            message=data,
            key=data.get("session_id")
        )
    
    def create_consumer(
        self,
        topics: list,
        group_id: str = None
    ) -> KafkaConsumer:
        """
        Create Kafka consumer
        
        Args:
            topics: List of topics to subscribe
            group_id: Consumer group ID
            
        Returns:
            KafkaConsumer instance
        """
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id or settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
    
    def consume_messages(
        self,
        topics: list,
        callback: Callable,
        group_id: str = None
    ):
        """
        Consume messages from topics
        
        Args:
            topics: List of topics
            callback: Function to process each message
            group_id: Consumer group ID
        """
        consumer = self.create_consumer(topics, group_id)
        
        logger.info(f"🔄 Listening to topics: {topics}")
        
        try:
            for message in consumer:
                data = message.value
                logger.info(
                    f"📨 Received message from {message.topic} "
                    f"partition {message.partition} offset {message.offset}"
                )
                
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("⏹️  Stopping consumer...")
        finally:
            consumer.close()


# Global instance
kafka_service = KafkaService()