"""
Enhanced Session Manager - Support guest users
"""
import json
from datetime import datetime
from typing import Optional, Dict, List
import uuid
import redis

from app.config import settings


class SessionManager:
    """Manage sessions for both authenticated and guest users"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = settings.SESSION_TTL
    
    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    def _device_sessions_key(self, device_id: str) -> str:
        """Key to store list of sessions for a device"""
        return f"device_sessions:{device_id}"
    
    def _user_sessions_key(self, user_id: str) -> str:
        """Key to store list of sessions for a user"""
        return f"user_sessions:{user_id}"
    
    def create(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Create new session
        
        Args:
            user_id: User ID (if logged in)
            device_id: Device ID (if guest)
            session_id: Optional session ID
        """
        if not user_id and not device_id:
            raise ValueError("Either user_id or device_id required")
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "device_id": device_id,
            "is_authenticated": user_id is not None,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "messages": [],
            "context": {},
            "guest_info": None  # Will be filled when placing order
        }
        
        # Save session
        self.redis.setex(
            self._key(session_id),
            self.ttl,
            json.dumps(data)
        )
        
        # Add to device/user session list
        if device_id:
            self.redis.sadd(self._device_sessions_key(device_id), session_id)
            self.redis.expire(self._device_sessions_key(device_id), self.ttl)
        
        if user_id:
            self.redis.sadd(self._user_sessions_key(user_id), session_id)
            self.redis.expire(self._user_sessions_key(user_id), self.ttl)
        
        return data
    
    def get(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        data = self.redis.get(self._key(session_id))
        return json.loads(data) if data else None
    
    def get_by_device(self, device_id: str) -> List[Dict]:
        """Get all sessions for a device"""
        session_ids = self.redis.smembers(self._device_sessions_key(device_id))
        sessions = []
        
        for session_id in session_ids:
            session = self.get(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    def get_latest_by_device(self, device_id: str) -> Optional[Dict]:
        """Get most recent session for a device"""
        sessions = self.get_by_device(device_id)
        if not sessions:
            return None
        
        # Sort by last_activity
        sessions.sort(key=lambda s: s["last_activity"], reverse=True)
        return sessions[0]
    
    def update(self, session_id: str, data: Dict):
        """Update session"""
        data["last_activity"] = datetime.utcnow().isoformat()
        self.redis.setex(
            self._key(session_id),
            self.ttl,
            json.dumps(data)
        )

    def extend_ttl(self, session_id: str):
        """Extend session TTL without updating data"""
        key = self._key(session_id)
        if self.redis.exists(key):
            self.redis.expire(key, self.ttl)
            return True
        return False
    
    def upgrade_to_authenticated(
        self,
        session_id: str,
        user_id: str
    ) -> Dict:
        """
        Upgrade guest session to authenticated session
        Called after user logs in or registers
        """
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Update session
        session["user_id"] = user_id
        session["is_authenticated"] = True
        session["upgraded_at"] = datetime.utcnow().isoformat()
        
        # Add to user session list
        self.redis.sadd(self._user_sessions_key(user_id), session_id)
        self.redis.expire(self._user_sessions_key(user_id), self.ttl)
        
        self.update(session_id, session)
        
        return session
    
    def migrate_device_sessions(self, device_id: str, user_id: str):
        """
        Migrate all device sessions to user account
        Called when guest user creates account
        """
        sessions = self.get_by_device(device_id)
        
        for session in sessions:
            self.upgrade_to_authenticated(session["session_id"], user_id)
        
        return len(sessions)
    
    def add_message(self, session_id: str, role: str, content: str, **kwargs):
        """Add message atomically using Lua script"""
        
        lua_script = """
        local key = KEYS[1]
        local message = ARGV[1]
        local ttl = ARGV[2]
        
        local session = redis.call('GET', key)
        if not session then
            return nil
        end
        
        local data = cjson.decode(session)
        table.insert(data.messages, cjson.decode(message))
        
        -- Keep last 50
        if #data.messages > 50 then
            local start = #data.messages - 49
            local new_messages = {}
            for i = start, #data.messages do
                table.insert(new_messages, data.messages[i])
            end
            data.messages = new_messages
        end
        
        data.last_activity = ARGV[3]
        redis.call('SETEX', key, ttl, cjson.encode(data))
        return 1
        """
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        result = self.redis.eval(
            lua_script,
            1,
            self._key(session_id),
            json.dumps(message),
            str(self.ttl),
            datetime.utcnow().isoformat()
        )
        
        if not result:
            raise ValueError(f"Session not found: {session_id}")
    
    def set_guest_info(self, session_id: str, guest_info: Dict):
        """Save guest info to session (for orders)"""
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session["guest_info"] = guest_info
        self.update(session_id, session)

    def cleanup_device_sessions(self, device_id: str, keep_latest: int = 5):
        """
        Cleanup old sessions for device, keep only N latest
        
        Args:
            device_id: Device ID
            keep_latest: Number of recent sessions to keep
        """
        sessions = self.get_by_device(device_id)
        
        if len(sessions) <= keep_latest:
            return 0
        
        # Sort by last_activity (oldest first)
        sessions.sort(key=lambda s: s["last_activity"])
        
        # Delete old sessions
        deleted = 0
        for session in sessions[:-keep_latest]:
            self.redis.delete(self._key(session["session_id"]))
            deleted += 1
        
        return deleted

# Call this periodically or when creating new session
if not request.user_id:
    # Guest user - cleanup old sessions
    session_manager.cleanup_device_sessions(request.device_id, keep_latest=5)

    # session_manager.extend_ttl(session_id)
