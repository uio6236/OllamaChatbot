import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
class Memory {
  map = new Map();
  getItem(k) {
    return this.map.get(k) ?? null;
  }
  setItem(k, v) {
    this.map.set(k, String(v));
  }
  removeItem(k) {
    this.map.delete(k);
  }
  get length() {
    return this.map.size;
  }
  key(i) {
    return [...this.map.keys()][i] ?? null;
  }
}
globalThis.localStorage = new Memory();
globalThis.sessionStorage = new Memory();
const dir = fs.mkdtempSync(path.join(process.cwd(), 'tests/.render-'));
const source = `
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { initial, taxService } from '@/api/services.js';
import App from '@/App.jsx';
import Auth from '@/pages/auth/AuthPage.jsx';
import Dashboard from '@/pages/dashboard/Dashboard.jsx';
import Input from '@/pages/tax/TaxInfoForm.jsx';
import Benefits from '@/pages/tax/BenefitsPage.jsx';
import Statistics from '@/pages/statistics/GroupStats.jsx';
import Chatbot from '@/pages/chatbot/ChatbotPage.jsx';
import Simulation from '@/pages/simulation/SimulationPage.jsx';
import Profile from '@/pages/profile/ProfilePage.jsx';
import Support from '@/pages/support/SupportPage.jsx';
import Admin from '@/pages/admin/AdminPage.jsx';
const noop = () => {};
const base = {
  data: initial,
  transactions: [],
  histories: [],
  saved: [],
  inquiries: [],
  search: '',
  setSearch: noop,
  go: noop,
  notify: noop,
  startSim: noop,
  normalInput: noop,
  profileTab: '이전 계산 결과',
  setProfileTab: noop,
  onSubmit: noop,
  onCancel: noop,
  faq: 0,
  setFaq: noop,
  supportTab: '자주 묻는 질문',
  setSupportTab: noop,
};
const apiResult = {
  taxYear: 2026,
  totalSalary: 36000000,
  withheldTax: 1523000,
  taxableIncome: 15375000,
  calculatedTax: 1046250,
  decidedTax: 1100000,
  expectedRefund: 423000,
  details: [
    {
      typeCode: 'CARD_CHECK',
      typeName: '체크카드',
      kind: 'CARD',
      baseAmount: 4000000,
      deductionAmount: 300000,
      sourceNote: '신고안내 근거',
    },
    {
      typeCode: 'CARD_LIMIT',
      typeName: '카드 한도',
      kind: 'CARD_RULE',
      baseAmount: 0,
      deductionAmount: -100000,
      sourceNote: '한도 근거',
    },
    {
      typeCode: 'STANDARD',
      typeName: '표준세액공제',
      kind: 'TAX_CREDIT',
      baseAmount: 0,
      deductionAmount: 0,
      sourceNote: '',
    },
  ],
};
const ledgerRows = [
  {
    id: 1,
    date: '2026-10-01',
    merchant: '가게',
    amount: 12345,
    category: '일반',
    paymentMethod: '신용카드',
    source: 'upload',
    method: '상호명 미매칭 · 일반 추정',
  },
  {
    id: 2,
    date: '2026-10-01',
    merchant: '교통',
    amount: 65000,
    category: '대중교통',
    paymentMethod: '체크카드',
    source: 'upload',
    method: '예시 공공데이터 상호명 대조 일치',
  },
  {
    id: 3,
    date: '2026-10-02',
    merchant: '보험',
    amount: 90000,
    category: '공제 대상 아님',
    paymentMethod: '신용카드',
    source: 'upload',
    method: '예시 공공데이터 상호명 대조 일치',
  },
  {
    id: 4,
    date: '2026-10-03',
    merchant: '가게',
    amount: 12345,
    category: '일반',
    paymentMethod: '신용카드',
    source: 'upload',
    duplicateState: 'pending',
  },
  {
    id: 5,
    date: '2025-10-01',
    merchant: '가게',
    amount: 999999,
    category: '일반',
    paymentMethod: '신용카드',
    source: 'upload',
  },
];
const cases = [
  [
    'dashboard-ledger',
    <Dashboard
      {...base}
      data={{ ...initial, taxYear: 2026 }}
      transactions={ledgerRows}
      chart={() => null}
    />,
  ],
  ['home', <App />],
  ...['login', 'signup', 'reset'].map((page) => [page, <Auth {...base} page={page} />]),
  ['dashboard-demo', <Dashboard {...base} chart={() => null} />],
  ['dashboard-api', <Dashboard {...base} result={apiResult} isDemo={false} chart={() => null} />],
  ['input', <Input {...base} mode="normal" />],
  ['simulation-input', <Input {...base} mode="simulation" />],
  ['benefits', <Benefits {...base} />],
  ['statistics', <Statistics {...base} />],
  ['chatbot', <Chatbot {...base} r={apiResult} />],
  [
    'simulation-result',
    <Simulation
      {...base}
      baseData={initial}
      sim={initial}
      br={taxService.calculate(initial)}
      sr={apiResult}
      simTx={[]}
    />,
  ],
  ['profile', <Profile {...base} />],
  ['support', <Support {...base} />],
  ['admin-denied', <Admin {...base} admin={false} />],
];
for (const [name, node] of cases) {
  const html = renderToStaticMarkup(node);
  if (!html || /NaN|undefined/.test(html)) throw Error(name + ': 렌더링 값 확인 필요');
  if (
    name === 'dashboard-api' &&
    (!html.includes('15,375,000') ||
      !html.includes('-100,000') ||
      !html.includes('200,000') ||
      !html.includes('신고안내 근거'))
  )
    throw Error('실제 응답 상세/음수 합계 렌더링 실패');
  if (
    name === 'dashboard-ledger' &&
    (!html.includes('12,345원') ||
      !html.includes('65,000원') ||
      !html.includes('90,000원') ||
      !html.includes('167,345원') ||
      html.includes('999,999원') ||
      !html.includes('소비 유형별 실제 지출 및 분류 결과'))
  )
    throw Error('지출 표의 연도/보류 제외/분류 집계 실패');
  if (
    name === 'dashboard-demo' &&
    (!html.includes('계산 연동 필요') ||
      html.includes('공제액 0원') ||
      html.includes('카드 소득공제 합계(음수 조정액 포함):'))
  )
    throw Error('미연동 공제액 표시 오류');
  if (
    name === 'dashboard-api' &&
    (!html.includes('0원') ||
      !html.includes('카드 공제한도 적용에 따른 조정액') ||
      !html.includes('공제 대상 금액') ||
      !html.includes('공제·감면 상세 내역'))
  )
    throw Error('실제 0원/음수/별도 상세 표 표시 실패');
  if (name === 'dashboard-demo') {
    const panel = html.split('<section class="card deductions">')[1].split('</section>')[0];
    if (
      (panel.match(/class="deduction-detail"/g) || []).length !== 7 ||
      panel.includes('deduction-response') ||
      !panel.includes('공제율 적용액') ||
      !panel.includes('한도 전') ||
      !panel.includes('최종 소득공제')
    )
      throw Error('v10 공제 영역 구조 복원 실패');
    for (const label of [
      '신용·체크카드·현금영수증',
      '추가 부양가족',
      '월세',
      '사회보험료',
      '주택청약',
      '연금저축·IRP',
      '중소기업 취업 청년 감면',
    ])
      if (!panel.includes(label)) throw Error('v10 항목 누락: ' + label);
  }
  console.log('PASS render:', name);
}
`;
try {
  await build({
    stdin: { contents: source, loader: 'jsx', resolveDir: process.cwd() },
    outfile: `${dir}/pages.mjs`,
    alias: { '@': path.join(process.cwd(), 'src') },
    bundle: true,
    platform: 'node',
    format: 'esm',
    packages: 'external',
    logLevel: 'silent',
  });
  await import(pathToFileURL(`${dir}/pages.mjs`));
  // 유지된 UI 파일까지 구문·import 검사를 수행합니다.
  const walk = (p) =>
    fs
      .readdirSync(p, { withFileTypes: true })
      .flatMap((e) =>
        e.isDirectory()
          ? walk(path.join(p, e.name))
          : /\.(jsx|js)$/.test(e.name)
            ? [path.join(p, e.name)]
            : [],
      );
  const modules = walk('src');
  await build({
    entryPoints: modules,
    outdir: `${dir}/modules`,
    alias: { '@': path.join(process.cwd(), 'src') },
    bundle: true,
    platform: 'browser',
    format: 'esm',
    packages: 'external',
    loader: { '.css': 'empty' },
    logLevel: 'silent',
  });
  console.log('PASS 전체 모듈 번들:', modules.length);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
