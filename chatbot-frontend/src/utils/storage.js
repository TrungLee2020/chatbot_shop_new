// src/utils/storage.js
import { v4 as uuidv4 } from 'uuid';

/**
 * Device ID - Unique identifier for guest users
 */
export const getDeviceId = () => {
  let deviceId = localStorage.getItem('device_id');
  if (!deviceId) {
    deviceId = uuidv4();
    localStorage.setItem('device_id', deviceId);
    console.log('🆔 New device_id created:', deviceId);
  }
  return deviceId;
};

/**
 * Session ID - Current chat session
 */
export const getSessionId = () => {
  return localStorage.getItem('session_id') || null;
};

export const setSessionId = (sessionId) => {
  localStorage.setItem('session_id', sessionId);
  console.log('💾 Session ID saved:', sessionId);
};

export const clearSessionId = () => {
  localStorage.removeItem('session_id');
  console.log('🗑️ Session cleared');
};

/**
 * Auth Token - For logged-in users
 */
export const getAuthToken = () => {
  return localStorage.getItem('auth_token') || null;
};

export const setAuthToken = (token) => {
  localStorage.setItem('auth_token', token);
  console.log('🔐 Auth token saved');
};

export const clearAuthToken = () => {
  localStorage.removeItem('auth_token');
  console.log('🔓 Logged out');
};

/**
 * User Info
 */
export const getUserInfo = () => {
  const info = localStorage.getItem('user_info');
  return info ? JSON.parse(info) : null;
};

export const setUserInfo = (userInfo) => {
  localStorage.setItem('user_info', JSON.stringify(userInfo));
};

export const clearUserInfo = () => {
  localStorage.removeItem('user_info');
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => {
  return !!getAuthToken();
};

/**
 * Logout - Clear all auth data
 */
export const logout = () => {
  clearAuthToken();
  clearUserInfo();
  // Keep device_id and session_id for continuity
  console.log('👋 Logged out successfully');
};