import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/globals.css';

// 원본과 같은 클라이언트 앱을 실행합니다. 개발 모드의 추가 effect 재실행은 켜지 않습니다.
createRoot(document.getElementById('root')).render(<App />);
