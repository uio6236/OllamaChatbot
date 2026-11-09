import React from 'react';
import { ArrowRight, LogOut, ShieldCheck, Leaf, ChevronDown } from 'lucide-react';
import { accountService } from '@/api/account-service.js';
import { nav, Logo } from '@/components/common/site-primitives.jsx';

// 기존 메뉴·체험 사용자 정보·로그아웃을 포함한 사이드바입니다.
export default function Sidebar({
  page,
  data,
  mobile,
  session,
  setSession,
  admin,
  go,
  notify,
  normalInput,
}) {
  return (
    <aside className={'sidebar ' + (mobile ? 'open' : '')}>
      <button className="bare" onClick={() => go('home')}>
        <Logo />
      </button>
      <div className="workspace-label">MY TAX WORKSPACE</div>
      <nav>
        {nav.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => (id === 'input' ? normalInput() : go(id))}
            className={page === id || (page === 'compare' && id === 'dashboard') ? 'active' : ''}
          >
            <Icon size={19} />
            {label}
            {page === id && <i />}
          </button>
        ))}
      </nav>
      {admin && (
        <button
          className={'admin-link ' + (page === 'admin' ? 'active' : '')}
          onClick={() => go('admin')}
        >
          <ShieldCheck size={18} />
          관리자 콘솔
        </button>
      )}
      <div className="sidebar-bottom">
        <div className="tip">
          <span className="iconbox">
            <Leaf size={19} />
          </span>
          <b>작은 준비, 더 큰 환급</b>
          <p>
            놓치기 쉬운 혜택을
            <br />
            미리 확인해보세요.
          </p>
          <button onClick={() => go('benefits')}>
            청년 혜택 알아보기 <ArrowRight size={14} />
          </button>
        </div>
        <button className="sidebar-user" onClick={() => go('profile')}>
          <span className="avatar">{data.name.slice(-2, -1) || '희'}</span>
          <span>
            <b>{data.name}</b>
            <small>
              {admin
                ? '관리자 · 브라우저 시연'
                : session
                  ? '일반 회원 · 브라우저 시연'
                  : '비로그인 체험'}
            </small>
          </span>
          <ChevronDown size={15} />
        </button>
        <button
          className="logout"
          onClick={() => {
            accountService.logout();
            setSession(null);
            go('login');
            notify('로그아웃했습니다.');
          }}
        >
          <LogOut size={14} />
          로그아웃
        </button>
      </div>
    </aside>
  );
}
