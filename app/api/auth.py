"""
Authentication - Optional for chat, required for some features
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.models.auth import Token, LoginRequest, User
from app.core.security import create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)  # auto_error=False for optional auth


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user from JWT token (OPTIONAL)
    Returns None if no token provided
    Use for endpoints that work for both guest and logged-in users
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        # In production: fetch from database
        return User(user_id=user_id, username=f"user_{user_id}")
    except:
        return None


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current user from JWT token (REQUIRED)
    Raises 401 if no valid token
    Use for endpoints that require authentication
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    return User(user_id=user_id, username=f"user_{user_id}")


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """Login and get JWT token"""
    # Mock authentication
    # In production: verify against database
    
    if request.username == "testuser" and request.password == "testpass":
        access_token = create_access_token(
            data={"sub": "user_123"}
        )
        return Token(access_token=access_token)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )


@router.post("/register")
async def register(
    username: str,
    password: str,
    email: str,
    device_id: Optional[str] = None
):
    """
    Register new account
    Optionally migrate guest sessions if device_id provided
    """
    # TODO: Create user in database
    user_id = str(uuid.uuid4())
    
    # Migrate device sessions if provided
    if device_id:
        from app.core.redis_client import get_redis
        from app.services.session_manager import SessionManager
        
        redis_client = get_redis()
        session_manager = SessionManager(redis_client)
        
        migrated_count = session_manager.migrate_device_sessions(
            device_id=device_id,
            user_id=user_id
        )
        
        return {
            "user_id": user_id,
            "message": "Account created successfully",
            "migrated_sessions": migrated_count
        }
    
    return {
        "user_id": user_id,
        "message": "Account created successfully"
    }