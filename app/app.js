// Initialize
const CHAT_API = 'http://localhost:8000';
let deviceId = localStorage.getItem('device_id') || generateUUID();
let sessionId = localStorage.getItem('session_id') || null;
let authToken = localStorage.getItem('auth_token') || null;

localStorage.setItem('device_id', deviceId);

// Send message (guest)
async function sendMessageGuest(message) {
  const response = await fetch(`${CHAT_API}/chat/message`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      device_id: deviceId,
      session_id: sessionId,
      message: message
    })
  });
  
  const data = await response.json();
  
  // Save session for next message
  sessionId = data.session_id;
  localStorage.setItem('session_id', sessionId);
  
  return data;
}

// Send message (authenticated)
async function sendMessageAuth(message) {
  const response = await fetch(`${CHAT_API}/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      message: message
    })
  });
  
  return await response.json();
}

// Login and upgrade session
async function login(username, password) {
  // 1. Login
  const loginRes = await fetch(`${CHAT_API}/auth/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password})
  });
  
  const {access_token} = await loginRes.json();
  authToken = access_token;
  localStorage.setItem('auth_token', authToken);
  
  // 2. Upgrade existing session
  if (sessionId) {
    await fetch(`${CHAT_API}/chat/session/upgrade?session_id=${sessionId}`, {
      method: 'POST',
      headers: {'Authorization': `Bearer ${authToken}`}
    });
  }
}

// Helper
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}