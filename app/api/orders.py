"""
Order API - Support guest checkout
"""
from fastapi import APIRouter, Depends, HTTPException
import uuid
from datetime import datetime

from models.chat import OrderRequest, GuestInfo
from models.auth import User
from api.auth import get_current_user_optional
from services.session_manager import SessionManager
from core.redis_client import get_redis

redis_client = get_redis()
session_manager = SessionManager(redis_client)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/create")
async def create_order(
    request: OrderRequest,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Create order - works for both guest and logged-in users
    
    Guest users must provide:
    - device_id
    - guest_info (name, phone, address)
    
    Logged-in users:
    - Auto-fetch info from profile
    """
    # Validate
    request.validate_identity()
    session_manager = SessionManager(redis_client)
    session = session_manager.get(request.session_id)

    if not session:
        raise HTTPException(404, "Session not found")
    
    # Determine user type
    if current_user:
        # Authenticated user
        if session["user_id"] != current_user.user_id:
            raise HTTPException(403, "Session does not belong to you")
        user_id = current_user.user_id
        is_guest = False
    else:
        # Guest user
        if not request.device_id:
            raise HTTPException(400, "device_id required for guest users")
        
        if session["device_id"] != request.device_id:
            raise HTTPException(403, "Session does not belong to this device")
        
        if not request.guest_info:
            raise HTTPException(400, "guest_info required for guest checkout")
        
        user_id = None
        is_guest = True
        
        customer_info = {
            "device_id": request.device_id,
            "name": request.guest_info.name,
            "phone": request.guest_info.phone,
            "email": request.guest_info.email,
            "address": request.guest_info.address,
            "city": request.guest_info.city
        }
        
        # Save guest info to session
        redis_client = get_redis()
        session_manager = SessionManager(redis_client)
        session_manager.set_guest_info(
            request.session_id,
            customer_info
        )
    
    # Create order
    order_id = str(uuid.uuid4())
    
    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "device_id": request.device_id,
        "session_id": request.session_id,
        "is_guest": is_guest,
        "customer_info": customer_info,
        "products": request.products,
        "delivery_address": request.delivery_address or customer_info.get("address"),
        "delivery_notes": request.delivery_notes,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # TODO: Save to PostgreSQL orders table
    # - Include device_id for guest orders
    # - Can link to user_id later if they register
    
    return {
        "order_id": order_id,
        "status": "success",
        "message": "Đặt hàng thành công!",
        "is_guest": is_guest,
        "order_data": order_data
    }


@router.get("/track/{order_id}")
async def track_order(order_id: str):
    """
    Track order by ID
    No authentication required - anyone with order_id can track
    """
    # TODO: Fetch from database
    return {
        "order_id": order_id,
        "status": "processing",
        "tracking_info": "Order is being prepared"
    }


@router.post("/claim")
async def claim_guest_orders(
    device_id: str,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Claim guest orders after login/register
    Links all orders from device_id to user account
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Must be logged in to claim orders"
        )
    
    # TODO: Update orders in database
    # UPDATE orders SET user_id = ? WHERE device_id = ? AND user_id IS NULL
    
    return {
        "message": "Orders claimed successfully",
        "user_id": current_user.user_id
    }