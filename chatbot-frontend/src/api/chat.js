// src/api/chat.js
import axios from 'axios';
import { 
  getDeviceId, 
  getSessionId, 
  setSessionId, 
  getAuthToken,
  setAuthToken,
  setUserInfo
} from '../utils/storage';

const API_BASE = 'http://localhost:8000';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 seconds
});

// Request interceptor - Add auth token if available
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Send chat message
 */
export const sendMessage = async (message) => {
  const deviceId = getDeviceId();
  const sessionId = getSessionId();
  
  const payload = {
    device_id: deviceId,
    session_id: sessionId,
    message: message.trim()
  };
  
  console.log('📤 Sending message:', payload);
  
  try {
    const response = await api.post('/chat/message', payload);
    const data = response.data;
    
    console.log('📥 Response:', data);
    
    // Save session_id for next message
    if (data.session_id) {
      setSessionId(data.session_id);
    }
    
    return data;
    
  } catch (error) {
    console.error('❌ Send message error:', error);
    
    if (error.response) {
      // Server responded with error
      throw new Error(error.response.data.detail || 'Server error');
    } else if (error.request) {
      // No response from server
      throw new Error('Cannot connect to server. Please check if backend is running.');
    } else {
      throw new Error('Failed to send message');
    }
  }
};

/**
 * Get session info
 */
export const getSessionInfo = async (sessionId) => {
  try {
    const response = await api.get(`/chat/session/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('❌ Get session error:', error);
    throw error;
  }
};

/**
 * Login
 */
export const login = async (username, password) => {
  try {
    const response = await api.post('/auth/login', {
      username,
      password
    });
    
    const { access_token } = response.data;
    
    // Save token
    setAuthToken(access_token);
    
    // Save user info (mock - in real app, fetch from API)
    setUserInfo({
      username: username,
      user_id: 'user_123' // Should come from token payload
    });
    
    // Upgrade current session if exists
    const sessionId = getSessionId();
    if (sessionId) {
      await upgradeSession(sessionId);
    }
    
    console.log('✅ Login successful');
    
    return { success: true, access_token };
    
  } catch (error) {
    console.error('❌ Login error:', error);
    
    if (error.response?.status === 401) {
      throw new Error('Incorrect username or password');
    }
    
    throw new Error('Login failed. Please try again.');
  }
};

/**
 * Upgrade guest session to authenticated
 */
export const upgradeSession = async (sessionId) => {
  try {
    await api.post(`/chat/session/upgrade?session_id=${sessionId}`);
    console.log('✅ Session upgraded to authenticated');
  } catch (error) {
    console.error('⚠️ Session upgrade failed:', error);
    // Don't throw - this is not critical
  }
};

/**
 * Health check
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('❌ Health check failed:', error);
    return { status: 'unhealthy' };
  }
};