"""
Chat models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class ChatMessage(BaseModel):
    """
    Chat message - support both authenticated and guest users
    """
    # Identity: Either user_id OR device_id required
    user_id: Optional[str] = None  # For logged-in users
    device_id: Optional[str] = None  # For guest users
    
    # Session (optional - will be created if not provided)
    session_id: Optional[str] = None
    
    # Message
    message: str
    
    def get_identity(self) -> str:
        """Get user identity (user_id or device_id)"""
        if self.user_id:
            return f"user:{self.user_id}"
        elif self.device_id:
            return f"device:{self.device_id}"
        else:
            raise ValueError("Either user_id or device_id required")
    
    def is_authenticated(self) -> bool:
        """Check if user is logged in"""
        return self.user_id is not None


class ChatResponse(BaseModel):
    message_id: str
    session_id: str  # ← Frontend MUST save this!
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    user_message: str
    ai_response: str
    products: List[Dict] = []
    intent: Optional[str] = None
    timestamp: str
    is_authenticated: bool = False
    session_created: bool = False  # ← NEW: True if new session was created


class GuestInfo(BaseModel):
    """Guest information for orders"""
    name: str
    phone: str
    email: Optional[str] = None
    address: str
    city: str
    district: Optional[str] = None


class OrderRequest(BaseModel):
    """Order request - support both guest and logged-in"""
    # Identity
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    
    # Session
    session_id: str
    
    # Products
    products: List[Dict]  # [{"product_id": "...", "quantity": 1}]
    
    # Guest info (required if not logged in)
    guest_info: Optional[GuestInfo] = None
    
    # Delivery
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    
    def validate_identity(self):
        """Validate that we have identity and required info"""
        if not self.user_id and not self.device_id:
            raise ValueError("Either user_id or device_id required")
        
        # Guest users must provide contact info
        if not self.user_id and not self.guest_info:
            raise ValueError("Guest users must provide guest_info")