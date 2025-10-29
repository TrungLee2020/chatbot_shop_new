"""
AI Client - SIMPLIFIED VERSION
Only send message + session_id to AI API
"""
import httpx
import logging
from typing import Dict

from config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Client to call external AI API - Simplified"""
    
    def __init__(self):
        self.api_url = settings.AI_API_URL
        self.api_key = settings.AI_API_KEY
        self.timeout = settings.AI_API_TIMEOUT
    
    async def send_message(
        self,
        message: str,
        session_id: str
    ) -> Dict:
        """
        Send message to AI API - SIMPLIFIED
        
        AI API sẽ tự:
        - Load session history từ Redis
        - Query database
        - Generate response
        
        Args:
            message: User message
            session_id: Session ID (AI API dùng để load context)
            
        Returns:
            {
                "response": "AI generated text",
                "products": [...],
                "intent": "product_search",
                "confidence": 0.95
            }
        """
        payload = {
            "message": message,
            "session_id": session_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.info(f"🤖 Calling AI API: session={session_id}, message='{message[:50]}...'")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    # headers=headers
                )
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(
                    f"✅ AI API response: "
                    f"intent={data.get('intent')}, "
                    f"products={len(data.get('products', []))}"
                )
                
                return data
                
        except httpx.TimeoutException:
            logger.error(f"⏱️ AI API timeout after {self.timeout}s")
            return self._fallback_response(message)
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AI API HTTP error: {e.response.status_code}")
            return self._fallback_response(message)
        
        except httpx.HTTPError as e:
            logger.error(f"❌ AI API connection error: {e}")
            return self._fallback_response(message)
        
        except Exception as e:
            logger.error(f"❌ AI API unexpected error: {e}")
            return self._fallback_response(message)
    
    def _fallback_response(self, message: str) -> Dict:
        """
        Fallback response when AI API fails
        Return friendly error message
        """
        return {
            "response": "Xin lỗi, hệ thống AI đang bận. Vui lòng thử lại sau ít phút. 🙏",
            "products": [],
            "intent": "system_error",
            "confidence": 0.0
        }


# Global instance
ai_client = AIClient()