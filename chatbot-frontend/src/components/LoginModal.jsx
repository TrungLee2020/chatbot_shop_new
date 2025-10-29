// src/components/LoginModal.jsx
import { useState } from 'react';
import { login } from '../api/chat';
import './LoginModal.css';

const LoginModal = ({ isOpen, onClose, onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!username || !password) {
      setError('Please enter username and password');
      return;
    }
    
    setLoading(true);
    
    try {
      await login(username, password);
      
      // Success
      onLoginSuccess();
      onClose();
      
      // Reset form
      setUsername('');
      setPassword('');
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <h2>🔐 Đăng nhập</h2>
        <p className="modal-subtitle">
          Đăng nhập để lưu lịch sử chat và đặt hàng
        </p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
            />
          </div>
          
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
          
          <button 
            type="submit" 
            className="btn-login"
            disabled={loading}
          >
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>
        
        <div className="demo-credentials">
          <p><strong>Demo credentials:</strong></p>
          <p>Username: <code>testuser</code></p>
          <p>Password: <code>testpass</code></p>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;