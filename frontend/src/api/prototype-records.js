import { migrateCalculationHistory } from './calculation-contract.js';
// 문의·관리 기준값·접근 기록을 브라우저에 보관합니다. TODO: Oracle 저장·조회와 관리자 API로 교체합니다.
// Browser adapter contracts mirror ERD v3.8; not a server authorization boundary.
import { accountService } from './account-service.js';
export const inquiryLabels = {
  ERROR: '오류',
  QUESTION: '문의',
  ETC: '기타',
  WAITING: '접수',
  CHECKING: '확인 중',
  ANSWERED: '답변 완료',
};
const namespace = () => (accountService.isDemo() ? 'hope-demo-' : 'hope-');
function read(key, initial) {
  try {
    return JSON.parse(localStorage.getItem(namespace() + key) || 'null') ?? initial;
  } catch {
    return initial;
  }
}
function write(key, value) {
  localStorage.setItem(namespace() + key, JSON.stringify(value));
}
function actor() {
  const u = accountService.current();
  if (!u) throw Error('로그인이 필요합니다.');
  return u;
}
function admin() {
  const u = actor();
  if (u.role !== 'ADMIN') throw Error('관리자 권한이 필요합니다.');
  return u;
}
export function recordAccess(screen, result = 'SUCCESS') {
  const u = accountService.current();
  const rows = read('access-log-v38', []);
  write(
    'access-log-v38',
    [
      {
        id: Date.now() + Math.random(),
        MEMBER_ID: u?.id ?? null,
        LOGIN_ID: u?.username || u?.name || '비로그인',
        SCREEN: screen,
        ACCESSED_AT: new Date().toISOString(),
        IP_ADDRESS: null,
        RESULT: result,
      },
      ...rows,
    ].slice(0, 500),
  );
}
export function accessRecords() {
  admin();
  return read('access-log-v38', []);
}
function all() {
  return read('inquiries-v38', []);
}
export const inquiryService = {
  list() {
    const u = actor();
    return all().filter((q) => u.role === 'ADMIN' || q.memberId === u.id);
  },
  migrate(legacy) {
    const u = accountService.current();
    if (!u || !legacy.length) return;
    const rows = all();
    for (const q of legacy) {
      if (rows.some((r) => r.id === q.id && r.memberId === u.id)) continue;
      rows.push({
        ...q,
        memberId: u.id,
        category:
          { 오류: 'ERROR', 문의: 'QUESTION', 기타: 'ETC' }[q.category] || q.category || 'QUESTION',
        status: q.answer ? 'ANSWERED' : 'WAITING',
        ...(q.answer ? { answeredAt: new Date().toISOString(), answeredBy: 'legacy-demo' } : {}),
      });
    }
    write('inquiries-v38', rows);
  },
  create(type, title, text) {
    const u = actor();
    if (!['ERROR', 'QUESTION', 'ETC'].includes(type)) throw Error('문의 유형을 선택해주세요.');
    if (!title.trim() || new TextEncoder().encode(title.trim()).length > 200)
      throw Error('제목은 200바이트(한글 약 66자) 이내로 입력해주세요.');
    if (!text.trim()) throw Error('문의 내용을 입력해주세요.');
    const q = {
      id: Date.now(),
      memberId: u.id,
      title: title.trim(),
      text: text.trim(),
      category: type,
      status: 'WAITING',
      date: new Date().toLocaleDateString('ko-KR'),
      answer: '',
    };
    write('inquiries-v38', [q, ...all()]);
    return q;
  },
  checking(id) {
    admin();
    const rows = all(),
      q = rows.find((q) => q.id === id);
    if (!q) throw Error('문의를 찾을 수 없습니다.');
    if (q.status === 'ANSWERED') throw Error('답변 완료 문의입니다.');
    q.status = 'CHECKING';
    q.answer = '';
    delete q.answeredAt;
    delete q.answeredBy;
    write('inquiries-v38', rows);
    recordAccess('INQUIRY_CHECKING');
  },
  answer(id, text) {
    const u = admin();
    if (!text.trim()) throw Error('답변을 입력해주세요.');
    const rows = all(),
      q = rows.find((q) => q.id === id);
    if (!q) throw Error('문의를 찾을 수 없습니다.');
    Object.assign(q, {
      status: 'ANSWERED',
      answer: text.trim(),
      answeredAt: new Date().toISOString(),
      answeredBy: u.id,
    });
    write('inquiries-v38', rows);
    recordAccess('INQUIRY_ANSWER');
  },
};
export function criteriaRecords() {
  admin();
  return read('criteria-v38', []);
}
export function saveCriterion(row) {
  const u = admin();
  if (
    !Number.isInteger(row.TAX_YEAR) ||
    row.TAX_YEAR < 2000 ||
    !row.TYPE_CODE.trim() ||
    !row.SOURCE_NOTE.trim() ||
    !Number.isFinite(row.RATE) ||
    row.RATE < 0 ||
    row.RATE > 100 ||
    row.SALARY_MIN < 0 ||
    row.LIMIT_AMOUNT < 0 ||
    (row.SALARY_MAX !== null && row.SALARY_MAX <= row.SALARY_MIN)
  )
    throw Error('연도·항목·급여 구간(시작 초과/끝 이하)·비율 0~100·한도·근거를 확인해주세요.');
  const rows = criteriaRecords();
  if (
    rows.some(
      (r) =>
        r.id !== row.id &&
        r.TAX_YEAR === row.TAX_YEAR &&
        r.TYPE_CODE === row.TYPE_CODE &&
        r.SALARY_MIN === row.SALARY_MIN,
    )
  )
    throw Error('같은 연도·항목·구간 시작값이 이미 있습니다.');
  write('criteria-v38', [
    ...rows.filter((r) => r.id !== row.id),
    { ...row, UPDATED_AT: new Date().toISOString(), UPDATED_BY: u.username || u.name },
  ]);
  recordAccess('CRITERIA_SAVE');
}
export function predictionRecords() {
  admin();
  const rows = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i) || '';
    if (!/^hope-user-.*-(histories|saved)$/.test(key)) continue;
    const id = key.replace(/^hope-user-/, '').replace(/-(histories|saved)$/, '');
    const isDemo = id.startsWith('demo-member-');
    if (isDemo !== accountService.isDemo()) continue;
    try {
      for (const row of JSON.parse(localStorage.getItem(key) || '[]'))
        rows.push({
          ...migrateCalculationHistory(row),
          memberId: id,
          kind: key.endsWith('saved') ? '시나리오' : '현재',
        });
    } catch {}
  }
  return rows;
}
