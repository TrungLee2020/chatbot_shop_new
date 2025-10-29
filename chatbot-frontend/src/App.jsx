// src/App.jsx
import { useEffect, useState } from 'react';
import ChatBox from './components/ChatBox';
import { healthCheck } from './api/chat';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState('checking');
  
  useEffect(() => {
    // Check backend health on mount
    const checkBackend = async () => {
      try {
        const result = await healthCheck();
        if (result.status === 'healthy') {
          setBackendStatus('online');
        } else {
          setBackendStatus('offline');
        }
      } catch (error) {
        setBackendStatus('offline');
      }
    };
    
    checkBackend();
  }, []);
  
  return (
    <div className="App">
      {/* Backend Status Banner */}
      {backendStatus === 'offline' && (
        <div className="status-banner error">
          ⚠️ Backend không kết nối được! Vui lòng kiểm tra:
          <ul>
            <li>Backend API đang chạy tại http://localhost:8000</li>
            <li>Mock AI Service đang chạy tại http://localhost:5000</li>
            <li>Redis + Kafka containers đang chạy</li>
          </ul>
        </div>
      )}
      
      {backendStatus === 'checking' && (
        <div className="status-banner info">
          🔄 Đang kiểm tra kết nối backend...
        </div>
      )}
      
      <ChatBox />
      
      {/* Instructions */}
      <div className="instructions">
        <h3>📝 Hướng dẫn sử dụng</h3>
        <ul>
          <li><strong>Guest Mode:</strong> Sử dụng ngay không cần đăng nhập</li>
          <li><strong>Login:</strong> Đăng nhập để lưu lịch sử chat lâu dài</li>
          <li><strong>Demo Account:</strong> Username: <code>testuser</code> / Password: <code>testpass</code></li>
          <li><strong>Session:</strong> Mỗi chat session tự động lưu trong 30 phút</li>
        </ul>
      </div>
    </div>
  );
}

export default App;