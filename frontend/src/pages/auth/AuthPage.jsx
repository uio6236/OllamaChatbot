import React from 'react';
import { Leaf } from 'lucide-react';
import { AccountForms } from '@/pages/auth/AccountForms.jsx';
import { accountService } from '@/api/account-service.js';

// 공통 인증 화면 배치와 로그인 완료 처리를 유지합니다.
export default function AuthPage({ page, setSession, go, notify }) {
  return (
    <main className="auth">
      <div className="auth-intro">
        <div className="eyebrow">YOUR TOMORROW STARTS HERE</div>
        <h1>
          반가워요,
          <br />
          당신의 내일을
          <br />
          함께 준비해요<span>.</span>
        </h1>
        <p>
          어려운 연말정산에
          <br />
          든든한 가이드가 되어드릴게요.
        </p>
        <div className="auth-leaf">
          <Leaf size={120} strokeWidth={1} />
        </div>
      </div>
      <AccountForms
        key={page}
        page={page}
        go={go}
        onLogin={(u) => {
          setSession(u);
          go(u.role === 'ADMIN' ? 'admin' : 'dashboard');
          notify(
            accountService.isDemo()
              ? '로그인 없이 별도 데이터로 체험을 시작했습니다.'
              : '이 브라우저의 시연 계정으로 로그인했습니다.',
          );
        }}
      />
    </main>
  );
}
