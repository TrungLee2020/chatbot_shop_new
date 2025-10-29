"""
Configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "AI Shopping Chatbot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # JWT - ✅ Added default value
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    SESSION_TTL: int = 1800
    
    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://default:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_CHAT_REQUESTS: str = "chat-requests"
    KAFKA_TOPIC_CHAT_RESPONSES: str = "chat-responses"
    KAFKA_CONSUMER_GROUP: str = "chat-service-group"
    
    # External AI API - ✅ Added default values
    AI_API_URL: str = "http://10.141.32.222:8000/sessions/" #"http://localhost:5000/api/chat"
    AI_API_KEY: str = "mock-api-key-for-development"
    AI_API_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()