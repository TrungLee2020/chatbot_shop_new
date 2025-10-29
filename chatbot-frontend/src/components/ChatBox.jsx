// src/components/ChatBox.jsx
import { useState, useEffect, useRef } from 'react';
import { sendMessage } from '../api/chat';
import { isAuthenticated, logout, getUserInfo, getDeviceId, getSessionId } from '../utils/storage';
import ProductCard from './ProductCard';
import LoginModal from './LoginModal';
import './ChatBox.css';

const ChatBox = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = () => {
      const authenticated = isAuthenticated();
      setIsLoggedIn(authenticated);
      
      if (authenticated) {
        const info = getUserInfo();
        setUserInfo(info);
      }
    };
    
    checkAuth();
    
    // Add welcome message
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: '👋 Xin chào! Tôi là trợ lý mua sắm AI.\n\nTôi có thể giúp bạn:\n• Tìm sản phẩm phù hợp\n• So sánh giá từ nhiều shop\n• Tư vấn mua hàng\n\nBạn đang tìm sản phẩm gì?',
        timestamp: new Date().toISOString()
      }]);
    }
  }, []);
  
  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // Add user message to UI immediately
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, newUserMessage]);
    setLoading(true);
    
    // Focus back to input
    inputRef.current?.focus();
    
    try {
      // Call API
      const response = await sendMessage(userMessage);
      
      // Add AI response to UI
      const aiMessage = {
        role: 'assistant',
        content: response.ai_response,
        products: response.products || [],
        intent: response.intent,
        timestamp: response.timestamp
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
    } catch (error) {
      console.error('Error:', error);
      
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: `❌ ${error.message}\n\nVui lòng kiểm tra:\n• Backend có đang chạy không?\n• Mock AI Service có chạy không?`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleLogin = () => {
    setShowLoginModal(true);
  };
  
  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
    const info = getUserInfo();
    setUserInfo(info);
    
    // Add success message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: `🎉 Chào mừng trở lại, ${info?.username}!\n\nTài khoản của bạn đã được liên kết với phiên chat này.`,
      timestamp: new Date().toISOString()
    }]);
  };
  
  const handleLogout = () => {
    logout();
    setIsLoggedIn(false);
    setUserInfo(null);
    
    // Add logout message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '👋 Bạn đã đăng xuất. Chat của bạn vẫn được lưu trên thiết bị này.',
      timestamp: new Date().toISOString()
    }]);
  };
  
  const handleNewChat = () => {
    if (window.confirm('Bạn có chắc muốn bắt đầu chat mới? Lịch sử chat hiện tại sẽ bị xóa.')) {
      setMessages([{
        role: 'assistant',
        content: '✨ Chat mới đã được tạo! Tôi có thể giúp gì cho bạn?',
        timestamp: new Date().toISOString()
      }]);
      
      // Clear session from localStorage
      localStorage.removeItem('session_id');
    }
  };
  
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('vi-VN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  const getQuickActions = () => {
    return [
      { label: '📱 Tìm điện thoại', message: 'Tìm điện thoại iPhone' },
      { label: '💻 Tìm laptop', message: 'Tìm laptop gaming' },
      { label: '🎧 Tai nghe', message: 'Tìm tai nghe bluetooth' },
      { label: '⌚ Đồng hồ', message: 'Tìm đồng hồ thông minh' },
    ];
  };
  
  const handleQuickAction = (message) => {
    setInput(message);
    inputRef.current?.focus();
  };
  
  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <h2>🤖 AI Shopping Assistant</h2>
          <span className="status-indicator">
            <span className="status-dot"></span>
            Online
          </span>
        </div>
        
        <div className="header-right">
          {isLoggedIn ? (
            <>
              <span className="user-badge">
                👤 {userInfo?.username}
              </span>
              <button className="btn-logout" onClick={handleLogout}>
                Đăng xuất
              </button>
            </>
          ) : (
            <button className="btn-login-header" onClick={handleLogin}>
              🔐 Đăng nhập
            </button>
          )}
          
          <button className="btn-new-chat" onClick={handleNewChat} title="Chat mới">
            ✨
          </button>
        </div>
      </div>
      
      {/* Info Bar */}
      <div className="info-bar">
        <div className="info-item">
          <span className="info-label">Device ID:</span>
          <span className="info-value">{getDeviceId().slice(0, 8)}...</span>
        </div>
        
        {getSessionId() && (
          <div className="info-item">
            <span className="info-label">Session:</span>
            <span className="info-value">{getSessionId().slice(0, 8)}...</span>
          </div>
        )}
        
        <div className="info-item">
          <span className="info-label">Messages:</span>
          <span className="info-value">{messages.length}</span>
        </div>
      </div>
      
      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.role}`}>
            <div className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}>
              {/* Avatar */}
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              
              {/* Content */}
              <div className="message-body">
                <div className="message-content">
                  {msg.content}
                </div>
                
                {/* Products */}
                {msg.products && msg.products.length > 0 && (
                  <div className="products-grid">
                    {msg.products.map((product, idx) => (
                      <ProductCard key={idx} product={product} />
                    ))}
                  </div>
                )}
                
                {/* Timestamp */}
                <div className="message-time">
                  {formatTime(msg.timestamp)}
                  {msg.intent && (
                    <span className="message-intent">• {msg.intent}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {loading && (
          <div className="message-wrapper assistant">
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-body">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Quick Actions */}
      {messages.length <= 2 && (
        <div className="quick-actions">
          <p className="quick-actions-title">💡 Gợi ý:</p>
          <div className="quick-actions-buttons">
            {getQuickActions().map((action, index) => (
              <button
                key={index}
                className="quick-action-btn"
                onClick={() => handleQuickAction(action.message)}
                disabled={loading}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Input */}
      <div className="chat-input">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Nhập tin nhắn... (Enter để gửi, Shift+Enter để xuống dòng)"
          disabled={loading}
          rows={1}
          onInput={(e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
          }}
        />
        
        <button 
          className="btn-send" 
          onClick={handleSend} 
          disabled={loading || !input.trim()}
          title="Gửi tin nhắn"
        >
          {loading ? '⏳' : '📤'}
        </button>
      </div>
      
      {/* Footer */}
      <div className="chat-footer">
        <span className="footer-text">
          Powered by AI • Backend: {isLoggedIn ? '🟢 Authenticated' : '🟡 Guest'}
        </span>
      </div>
      
      {/* Login Modal */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </div>
  );
};

export default ChatBox;