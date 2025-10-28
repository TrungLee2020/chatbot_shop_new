"""
AI Client - Call external AI API
"""
import httpx
import logging
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Client to call external AI API"""
    
    def __init__(self):
        self.api_url = settings.AI_API_URL
        self.api_key = settings.AI_API_KEY
        self.timeout = settings.AI_API_TIMEOUT
    
    async def send_message(
        self,
        message: str,
        session_id: str,
        user_id: str,
        chat_history: list = None
    ) -> Dict:
        """
        Send message to AI API
        
        Args:
            message: User message
            session_id: Session ID
            user_id: User ID
            chat_history: Previous messages
            
        Returns:
            AI response dict
        """
        payload = {
            "message": message,
            "session_id": session_id,
            "user_id": user_id,
            "chat_history": chat_history or []
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                
                logger.info(f"✅ AI API response received for session {session_id}")
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"❌ AI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error calling AI API: {e}")
            raise


# Global instance
ai_client = AIClient()