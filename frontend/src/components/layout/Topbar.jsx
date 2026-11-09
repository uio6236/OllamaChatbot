import { getTaxYear } from '@/utils/tax-year.js';
import React from 'react';
import { ChevronRight, Bell, Menu, ChevronDown } from 'lucide-react';
import { nav } from '@/components/common/site-primitives.jsx';

// 기존 상단바의 구조·버튼·알림 상태를 유지합니다.
export default function Topbar({
  page,
  taxYear,
  data,
  mobile,
  setMobile,
  notification,
  setNotification,
  go,
}) {
  return (
    <header className="topbar">
      <div>
        <button className="mobile-menu" aria-label="메뉴 열기" onClick={() => setMobile(!mobile)}>
          <Menu />
        </button>
        <span>나의 연말정산</span>
        <ChevronRight size={13} />
        <b>
          {nav.find((n) => n[0] === page)?.[1] ||
            (page === 'compare' ? '시뮬레이션 비교' : '관리자 콘솔')}
        </b>
      </div>
      <div>
        <span className="year">{taxYear ?? getTaxYear(data)}년 귀속</span>
        <button className="bell" aria-label="알림" onClick={() => setNotification(!notification)}>
          <Bell size={19} />
          <i />
        </button>
        <button className="top-profile" onClick={() => go('profile')}>
          <span className="avatar">희</span>
          {data.name}
          <ChevronDown size={14} />
        </button>
      </div>
      {notification && (
        <div className="notification card">
          <b>새로운 소식</b>
          <p>예상 환급액을 확인할 준비가 되었어요.</p>
          <button
            onClick={() => {
              setNotification(false);
              go('benefits');
            }}
          >
            청년 감면 자격 확인하기 →
          </button>
        </div>
      )}
    </header>
  );
}
