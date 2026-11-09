import React from 'react';
import { Logo } from '@/components/common/site-primitives.jsx';

// 기존 상단바의 구조·버튼·알림 상태를 유지합니다.
export default function PublicHeader({ go }) {
  return (
    <header className="public-header">
      <button className="bare" onClick={() => go('home')}>
        <Logo />
      </button>
      <nav>
        <a href="#features">서비스 소개</a>
        <a href="#how">이용 방법</a>
        <button onClick={() => go('support')}>고객센터</button>
      </nav>
      <div>
        <button className="text-btn" onClick={() => go('login')}>
          로그인
        </button>
      </div>
    </header>
  );
}
