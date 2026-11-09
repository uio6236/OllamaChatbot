import React from 'react';
import {
  LayoutDashboard,
  FilePenLine,
  Sparkles,
  BadgeCheck,
  ChartNoAxesCombined,
  UserRound,
  Headphones,
} from 'lucide-react';
import { categories } from '@/api/services.js';

// 원본의 공통 로고·버튼·태그·입력 틀·차트와 메뉴 상수입니다.
export const money = (n) => n.toLocaleString('ko-KR');

export const nav = [
  ['dashboard', '대시보드', LayoutDashboard],
  ['input', '정보 입력', FilePenLine],
  ['guide', 'AI 절세 가이드', Sparkles],
  ['benefits', '청년 혜택 자격진단', BadgeCheck],
  ['stats', '그룹 통계', ChartNoAxesCombined],
  ['profile', '마이페이지', UserRound],
  ['support', '고객센터', Headphones],
];

export const steps = ['기본 정보', '소득 정보', '지출 정보', '부양가족', '주거 정보', '공제·감면'];

export const colors = ['#2767f5', '#79a5ff', '#58c3ae', '#b09aec', '#d7dfec'];

export function Logo() {
  return (
    <span className="logo">
      <span className="leafmark">
        <i />
        <i />
      </span>
      희망환급<span className="logo-dot">.</span>
    </span>
  );
}

export function Btn({ children, onClick, secondary = false, ...props }) {
  return (
    <button
      {...props}
      onClick={onClick}
      className={(secondary ? 'btn secondary' : 'btn') + ' ' + (props.className || '')}
    >
      {children}
    </button>
  );
}

export function Tag({ children, tone = 'blue' }) {
  return <span className={'tag ' + tone}>{children}</span>;
}

export function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export function MiniChart() {
  return (
    <div className="minichart">
      {[36, 46, 40, 61, 49, 63, 53, 71, 62, 80, 66, 91].map((h, i) => (
        <div
          key={i}
          style={{
            height: h + '%',
          }}
        >
          <span>{i + 1}월</span>
        </div>
      ))}
    </div>
  );
}

export function Donut({ transactions }) {
  const sums = categories.map((c) =>
    transactions.filter((t) => t.category === c).reduce((a, t) => a + t.amount, 0),
  );
  const total = sums.reduce((a, b) => a + b, 0);
  let pct = 0;
  const gradient = sums
    .map((v, i) => {
      const start = pct;
      pct += total ? (v / total) * 100 : 0;
      return `${colors[i]} ${start}% ${pct}%`;
    })
    .join(',');
  return (
    <div className="donut-layout">
      <div
        className="donut"
        style={{
          background: `conic-gradient(${gradient})`,
        }}
      >
        <div>
          <small>전체 지출</small>
          <b>{money(total)}</b>
          <small>원</small>
        </div>
      </div>
      <div className="legend">
        {categories.map((c, i) => (
          <div key={c}>
            <span>
              <i
                style={{
                  background: colors[i],
                }}
              />
              {c}
            </span>
            <b>
              {money(sums[i])}
              <small>원</small>
            </b>
          </div>
        ))}
      </div>
    </div>
  );
}
