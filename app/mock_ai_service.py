"""
MOCK AI API - For Testing
Simple FastAPI server that mimics AI service behavior
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import redis
import json

app = FastAPI(title="Mock AI API")

# Connect to Redis (same as Chat API)
redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)


class ChatRequest(BaseModel):
    message: str
    session_id: str


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Mock AI endpoint
    
    Receives: message + session_id
    Returns: response + products + intent
    """
    message = request.message.lower()
    session_id = request.session_id
    
    # Get session from Redis to see history
    try:
        session_data = redis_client.get(f"session:{session_id}")
        if session_data:
            session = json.loads(session_data)
            history_count = len(session.get("messages", []))
        else:
            history_count = 0
    except:
        history_count = 0
    
    # Simple intent detection
    if any(keyword in message for keyword in ["tìm", "find", "search", "có", "mua"]):
        intent = "product_search"
        
        # Mock products
        products = [
            {
                "product_id": "prod_001",
                "product_name": "iPhone 15 Pro Max 256GB",
                "shop_name": "TechZone Vietnam",
                "original_price": 32000000,
                "discount_price": 29500000,
                "images": ["https://via.placeholder.com/300"],
                "status": "available"
            },
            {
                "product_id": "prod_002",
                "product_name": "iPhone 15 Pro 128GB",
                "shop_name": "Mobile World",
                "original_price": 28000000,
                "discount_price": 25500000,
                "images": ["https://via.placeholder.com/300"],
                "status": "available"
            },
            {
                "product_id": "prod_003",
                "product_name": "iPhone 15 Plus 128GB",
                "shop_name": "FPT Shop",
                "original_price": 24000000,
                "discount_price": 22000000,
                "images": ["https://via.placeholder.com/300"],
                "status": "available"
            }
        ]
        
        response_text = f"""Tôi tìm thấy {len(products)} sản phẩm phù hợp với yêu cầu của bạn:

1. **iPhone 15 Pro Max 256GB** - 29.5 triệu đồng (giảm từ 32 triệu)
   Shop: TechZone Vietnam

2. **iPhone 15 Pro 128GB** - 25.5 triệu đồng (giảm từ 28 triệu)
   Shop: Mobile World

3. **iPhone 15 Plus 128GB** - 22 triệu đồng (giảm từ 24 triệu)
   Shop: FPT Shop

Bạn muốn xem chi tiết sản phẩm nào? 📱"""
        
    elif any(keyword in message for keyword in ["giá", "price", "cost", "bao nhiêu"]):
        intent = "price_inquiry"
        products = []
        response_text = "Để tôi kiểm tra giá cho bạn. Bạn đang quan tâm sản phẩm nào nhỉ?"
        
    elif any(keyword in message for keyword in ["đặt", "mua", "order", "buy"]):
        intent = "order_intent"
        products = []
        response_text = "Để đặt hàng, bạn vui lòng chọn sản phẩm từ danh sách tôi gợi ý. Sau đó tôi sẽ hướng dẫn bạn hoàn tất đơn hàng."
        
    elif any(keyword in message for keyword in ["hi", "hello", "xin chào", "chào"]):
        intent = "greeting"
        products = []
        response_text = f"""Xin chào! 👋 Tôi là trợ lý mua sắm AI.

Tôi có thể giúp bạn:
• Tìm sản phẩm phù hợp
• So sánh giá từ nhiều shop
• Đặt hàng nhanh chóng

Bạn đang tìm sản phẩm gì?"""
        
    else:
        intent = "general_chat"
        products = []
        response_text = "Tôi có thể giúp bạn tìm kiếm sản phẩm. Bạn muốn tìm gì?"
    
    # Add context about history
    if history_count > 0:
        response_text += f"\n\n_({history_count} tin nhắn trong session này)_"
    
    return {
        "content": response_text,
        "products": products or [],
        "intent": intent or [],
        "confidence": 0.0
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mock-ai-api"}


if __name__ == "__main__":
    print("🤖 Starting Mock AI API on http://localhost:5000")
    print("📡 Endpoint: POST /api/chat")
    print("📋 Payload: {message, session_id}")
    uvicorn.run(app, host="0.0.0.0", port=5000)