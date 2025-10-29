import httpx
import logging
from typing import Dict, List, Any

# Giả lập settings để code chạy được
class Settings:
    AI_API_URL = "http://your-api-url.com/endpoint"
    AI_API_KEY = "your-api-key"
    AI_API_TIMEOUT = 30.0

settings = Settings()
# ---

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
        
        Args:
            message: User message
            session_id: Session ID
            
        Returns:
            Một dictionary chứa câu trả lời cuối cùng của AI, ví dụ:
            {
                "response": "Xin lỗi, không tìm thấy thông tin cho mã sản phẩm...",
                "products": [],
                "intent": "ai_generated" 
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
                    # headers=headers # Bỏ comment nếu cần xác thực
                )
                
                response.raise_for_status()
                
                # API trả về một LIST các message, không phải một DICT
                data: List[Dict[str, Any]] = response.json()
                
                # 1. Kiểm tra xem data có phải là list và có phần tử không
                if not isinstance(data, list) or not data:
                    logger.error("❌ AI API returned an empty or invalid response.")
                    return self._fallback_response(message)

                # 2. Lấy message cuối cùng trong danh sách
                final_response = data[-1]

                # 3. Lấy nội dung trả lời từ message cuối cùng
                #    Nên tìm message cuối cùng có role là 'assistant' và có content
                assistant_responses = [
                    msg for msg in reversed(data) 
                    if msg.get("role") == "assistant" and msg.get("content")
                ]
                
                if not assistant_responses:
                    logger.error("❌ No valid assistant message found in AI API response.")
                    return self._fallback_response(message)
                
                final_content = assistant_responses[0].get("content")

                logger.info(
                    f"✅ AI API response extracted: "
                    f"content='{final_content[:70]}...'"
                )
                
                # Trả về theo một định dạng nhất quán, tương tự fallback
                return {
                    "response": final_content,
                    "products": [],  # Bạn có thể trích xuất thông tin này nếu cần
                    "intent": "ai_generated" # Đặt một intent mặc định
                }
                
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
            "response": "Xin lỗi, hệ thống AI đang bận. Vui lòng thử lại sau ít phút.",
            "products": [],
            "intent": "system_error",
        }


# Global instance
ai_client = AIClient()