import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
const dir = fs.mkdtempSync(path.join(process.cwd(), 'tests/.hope-flow-'));

// 운영 소스의 JavaScript 모듈을 임시로 묶어 기존 서비스 회귀 검증을 실행합니다.
const sourceModules = {
  'account-service': 'src/api/account-service.js',
  services: 'src/api/services.js',
  'expense-service': 'src/api/expense-service.js',
  'dashboard-model': 'src/utils/dashboard-model.js',
  'group-model': 'src/utils/group-model.js',
  'prototype-records': 'src/api/prototype-records.js',
  'erd-contract': 'src/api/erd-contract.js',
};
for (const [name, entry] of Object.entries(sourceModules)) {
  await build({
    entryPoints: [entry],
    outfile: path.join(dir, `${name}.mjs`),
    bundle: true,
    platform: 'node',
    format: 'esm',
    packages: 'external',
    logLevel: 'silent',
  });
}
const { createAccountService, ageOn, LOCK_MS, ACCOUNT_KEY, enterDemoSession, demoStorage } =
  await import(pathToFileURL(path.join(dir, 'account-service.mjs')).href);
const {
  parseUploadCSV,
  parseUploadFile,
  parseUploadTable,
  uploadTotals,
  transactionExamples,
  flagDuplicates,
  removeUpload,
  makeMeta,
  uploadBlocker,
} = await import(pathToFileURL(path.join(dir, 'expense-service.mjs')).href);
const { taxService, initial, normalizeTaxData, validateTaxData, settlementLabel, merchantService } =
  await import(pathToFileURL(path.join(dir, 'services.mjs')).href);
const { dashboardModel } = await import(pathToFileURL(path.join(dir, 'dashboard-model.mjs')).href);
const { groupComparison } = await import(pathToFileURL(path.join(dir, 'group-model.mjs')).href);
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
const storage = new Memory(),
  session = new Memory();
let now = Date.parse('2026-10-28T15:00:00Z');
const svc = createAccountService(storage, session, () => now);
const input = {
  username: 'worker',
  gender: '여성',
  email: 'worker@example.test',
  birth: '1999-05-20',
  password: 'DemoPass123!',
  confirm: 'DemoPass123!',
  terms: true,
  privacy: true,
  financial: true,
  marketing: false,
  verificationToken: '',
};
const verified = (data) => {
  const sent = svc.sendEmailCode(data.email);
  return { ...data, verificationToken: svc.verifyEmailCode(data.email, sent.demoCode) };
};
for (const key of ['terms', 'privacy', 'financial'])
  await assert.rejects(svc.signUp({ ...input, [key]: false }), /필수/);
await assert.rejects(svc.signUp({ ...input, birth: '2012-10-30' }), /만 14세/);
assert.equal(ageOn('2012-10-29', new Date(now)), 14);
for (const birth of ['2027-01-01', '2001-02-29', '2026-02-30', 'abc'])
  await assert.rejects(svc.signUp({ ...input, birth }));
await assert.rejects(svc.signUp({ ...input, email: 'invalid' }), /이메일/);
await assert.rejects(svc.signUp({ ...input, username: 'x' }), /아이디/);
await assert.rejects(svc.signUp({ ...input, gender: '' }), /성별/);
await assert.rejects(svc.signUp({ ...input, confirm: 'wrong' }), /일치/);
await assert.rejects(svc.signUp(input), /인증/);
const challenge = svc.sendEmailCode(input.email);
const wrong = challenge.demoCode === '000000' ? '111111' : '000000';
assert.throws(() => svc.verifyEmailCode(input.email, wrong), /일치/);
assert.throws(() => svc.verifyEmailCode('different@example.test', challenge.demoCode), /먼저/);
const proof = svc.verifyEmailCode(input.email, challenge.demoCode);
now += 300000;
assert.throws(() => svc.verifyEmailCode(input.email, challenge.demoCode), /만료/);
await assert.rejects(svc.signUp({ ...input, verificationToken: proof }), /인증/);
const repeated = svc.sendEmailCode(input.email);
for (let i = 0; i < 5; i++)
  assert.throws(
    () => svc.verifyEmailCode(input.email, repeated.demoCode === '000000' ? '111111' : '000000'),
    /일치/,
  );
assert.throws(() => svc.verifyEmailCode(input.email, repeated.demoCode), /5회/);
const admin = await svc.bootstrap(
  verified({ ...input, username: 'first_admin', email: 'admin@example.test' }),
);
const worker = await svc.signUp({ ...verified(input), role: 'ADMIN' });
assert.equal(worker.role, 'USER');
assert.equal(worker.name, 'worker');
assert.equal(worker.gender, '여성');
assert.equal(worker.consents.financial, true);
assert(worker.FINANCE_AGREED_AT);
assert.equal(worker.FINANCE_VERSION, null);
assert.equal(svc.checkUsername('WORKER'), false);
assert.equal(svc.checkEmail(' WORKER@EXAMPLE.TEST '), false);
await assert.rejects(svc.signUp({ ...input, email: 'other@example.test' }), /아이디/);
await assert.rejects(
  svc.signUp({ ...input, username: 'other', email: ' WORKER@EXAMPLE.TEST ' }),
  /이미 사용/,
);
await assert.rejects(
  svc.bootstrap({ ...input, username: 'another', email: 'another@example.test' }),
  /이미 완료/,
);
assert.throws(() => svc.members(), /로그인/);
await svc.login('WORKER', input.password);
assert.throws(() => svc.setRole(worker.id, 'ADMIN'), /권한/);
await svc.login('first_admin', input.password);
assert.equal(svc.members('ork').length, 1);
assert.throws(() => svc.setRole(admin.id, 'USER'), /마지막/);
await assert.rejects(svc.withdraw(input.password), /마지막/);
svc.setRole(worker.id, 'ADMIN');
assert.throws(() => svc.setRole(admin.id, 'USER'), /본인/);
assert.equal(svc.members('worker')[0].role, 'ADMIN');
svc.setRole(worker.id, 'USER');
assert.equal(svc.members('worker')[0].role, 'USER');
svc.logout();
for (let i = 1; i <= 4; i++)
  await assert.rejects(svc.login('worker', 'wrong'), new RegExp(`${i}/5`));
await assert.rejects(svc.login('worker', 'wrong'), /10분/);
await assert.rejects(svc.login(input.email, input.password), /잠겼/);
now += LOCK_MS - 1;
await assert.rejects(svc.login(input.email, input.password), /잠겼/);
now++;
await svc.login(input.email, input.password);
assert.equal(svc.current().failures, 0);
await assert.rejects(svc.login(input.email, 'wrong'), /1\/5/);
await svc.login(input.email, input.password);
assert.equal(svc.current().failures, 0);
const key = `hope-user-${worker.id}-`;
for (const item of ['data', 'transactions', 'histories', 'saved', 'chat', 'inquiries', 'upload'])
  storage.setItem(key + item, 'sensitive');
storage.setItem(`hope-user-${admin.id}-data`, 'keep');
await assert.rejects(svc.withdraw('wrong'), /비밀번호/);
await svc.withdraw(input.password);
assert.equal(svc.current(), null);
assert([...storage.map.keys()].some((k) => k.startsWith(key)));
assert.equal(
  JSON.parse(storage.getItem(ACCOUNT_KEY)).find((u) => u.id === worker.id).status,
  'WITHDRAWN',
);
await assert.rejects(svc.login(input.email, input.password), /탈퇴/);
assert.equal(svc.checkUsername('worker'), false);
assert.equal(storage.getItem(`hope-user-${admin.id}-data`), 'keep');
assert(!storage.getItem(ACCOUNT_KEY).includes(input.password));
const csv =
  '날짜,상호명,금액,결제수단\n2026-10-01,서울교통공사,65000,체크카드\n2026-10-02,우리상점,20000,신용카드';
const a = parseUploadCSV(csv).map((r) => ({ ...r, uploadId: 'a' })),
  b = parseUploadCSV('날짜,상호명,금액\n2026-10-03,교보문고,30000', 'hometax').map((r) => ({
    ...r,
    uploadId: 'b',
  }));
assert.equal(a[0].category, '대중교통');
assert.match(a[0].classificationBasis, /서울교통공사/);
assert.equal(b[0].paymentMethod, '현금영수증');
assert.deepEqual(uploadTotals([...a, ...b]), { credit: 20000, debit: 65000, cash: 30000 });
const unknown = parseUploadCSV('날짜,상호명,금액\n2026-10-04,미등록상호,1000');
assert.equal(unknown[0].paymentMethod, '확인 필요');
assert.match(unknown[0].classificationBasis, /일致|일치하는 상호명이 없어/);
assert.deepEqual(uploadTotals(unknown), { credit: 0, debit: 0, cash: 0 });
assert.match(uploadBlocker(unknown), /결제수단/);
assert.equal(
  parseUploadCSV('날짜,상호명,금액\n2026-10-04,상호,1000', 'card', '체크카드')[0].paymentMethod,
  '체크카드',
);
assert.equal(parseUploadCSV(csv, 'card', '신용카드')[0].paymentMethod, '체크카드');
assert.throws(() => parseUploadCSV('날짜,상호명,금액\n2026-02-30,교보문고,1000'), /날짜/);
assert.throws(() => parseUploadCSV('date,merchant,amount\n2026-10-01,shop,100'), /양식/);
const dup = flagDuplicates(
  a,
  a.map((r) => ({ ...r, id: r.id + 100, uploadId: 'dup' })),
);
assert(dup.every((r) => r.duplicateState === 'pending'));
assert.deepEqual(uploadTotals([...a, ...dup]), uploadTotals(a));
assert.equal(dashboardModel(initial, [...a, ...dup]).total, 85000);
assert.equal(dashboardModel(initial, [...a, ...dup]).held, 2);
const files = [
  { id: 'a', name: 'a.csv', count: 2, at: '2026-10-29', source: 'card', status: '업로드 완료' },
  { id: 'b', name: 'b.csv', count: 1, at: '2026-10-29', source: 'hometax', status: '업로드 완료' },
];
const deleted = removeUpload([...a, ...b], files, 'a');
assert.deepEqual(deleted.rows, b);
assert.equal(deleted.meta.files[0].id, 'b');
assert.deepEqual(a, deleted.rows.length ? a : a);
assert.equal(makeMeta([]), null);
const many = Array.from({ length: 20 }, (_, i) => ({ ...a[1], id: i }));
const selected = transactionExamples(many, '일반');
assert.equal(selected.count, 20);
assert.equal(selected.examples.length, 15);
assert.equal(selected.total, 400000);
assert.equal(transactionExamples(a, '전통시장').count, 0);
assert.equal(merchantService.classify('교보문고옆카페').category, '일반');
const legacy = { ...initial, rent: 12000000 };
delete legacy.rentPeriod;
const converted = normalizeTaxData(legacy);
assert.equal(converted.rent, 0);
assert.equal(converted.legacyAnnualRent, 12000000);
assert.equal(converted.legacyRentNeedsReview, true);
assert.equal(
  taxService
    .calculate({ ...converted, rent: 500000, rentPeriod: 'monthly' })
    .details.find((d) => d.typeCode === 'RENT').baseAmount,
  6000000,
);
assert.match(validateTaxData({ ...initial, family: 1, children: 2 }), /자녀/);
assert.equal(validateTaxData({ ...initial, family: 2, children: 2 }), '');
const original = structuredClone(initial),
  copy = { ...original, debit: original.debit + 1000000 };
assert.equal(taxService.calculate(original).expectedRefund, -117000);
assert.equal(taxService.calculate(copy).expectedRefund, -72000);
assert.deepEqual(original, initial);
assert.equal(settlementLabel(-300000), '예상 추가 납부액');
assert.equal(settlementLabel(0), '환급 및 추가 납부 예상액');
assert.equal(settlementLabel(1), '예상 환급액');
const groups = groupComparison({ ...initial, gender: '여성', salary: 30000000 });
assert.equal(groups.rows.length, 3);
assert.match(groups.rows[0].label, /30세 미만 여성/);
assert.match(groups.rows[2].label, /2,000만 원 초과~3,000만 원 이하/);
assert.equal(
  groupComparison({ ...initial, gender: '남성', salary: 30000000 }).rows[2].decidedTax,
  groups.rows[2].decidedTax,
);
assert.equal(
  groupComparison({ ...initial, salary: 60000000 }).rows[0].decidedTax,
  groupComparison(initial).rows[0].decidedTax,
);
assert(groupComparison({ ...initial, paid: 0 }).rows[1].expectedRefund < 0);
const realBeforeDemo = storage.getItem(ACCOUNT_KEY);
enterDemoSession(storage, session, 'ADMIN');
const demoService = createAccountService(demoStorage(storage), session, () => now);
assert.equal(demoService.current().role, 'ADMIN');
const demoUser = demoService.members().find((u) => u.role === 'USER');
demoService.setRole(demoUser.id, 'ADMIN');
assert.equal(storage.getItem(ACCOUNT_KEY), realBeforeDemo);
enterDemoSession(storage, session, 'USER');
assert.equal(demoService.current().role, 'USER');
assert.throws(() => demoService.members(), /권한/);
assert.equal(storage.getItem(ACCOUNT_KEY), realBeforeDemo);
// v3.8 ingestion, statutory-boundary source data, service authorization and inquiry transition checks.
const XLSX = await import('xlsx');
const book = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(
  book,
  XLSX.utils.aoa_to_sheet([
    ['승인일시', '가맹점명', '이용금액', '사용구분'],
    [new Date(2026, 9, 1), '검증상점', 100, 'CHECK'],
  ]),
  '거래',
);
const xlsxRows = await parseUploadFile(
  new File([XLSX.write(book, { type: 'array', bookType: 'xlsx' })], 'input.xlsx'),
  'card',
  '',
);
assert.equal(xlsxRows[0].PAY_METHOD, 'CHECK');
assert.equal(xlsxRows[0].date, '2026-10-01');
assert.equal(xlsxRows[0].CATEGORY_CODE, 'GENERAL');
assert.equal(
  parseUploadCSV('승인일시,가맹점명,이용금액,사용구분\n2026/10/01 11:10,가게,-1000,CREDIT')[0]
    .amount,
  -1000,
);
assert.throws(() => parseUploadCSV('거래일자,가맹점명,이용금액\n2026-10-01,가게,NaN'), /2행/);
assert.equal(transactionExamples(many, '일반', 30).examples.length, 20);
const s1499 = groupComparison({ ...initial, salary: 15000000 }),
  s1501 = groupComparison({ ...initial, salary: 15000001 });
assert.equal(s1499.salaryStat.SALARY_MAX, 15000000);
assert.equal(s1501.salaryStat.SALARY_MIN, 15000000);
assert.equal(groupComparison({ ...initial, birth: '1956-12-31' }).ageStat.AGE_MIN, 70);
assert.equal(groupComparison({ ...initial, birth: '1966-12-31' }).ageStat.AGE_MAX, 69);
assert.equal(groupComparison({ ...initial, gender: '' }).rows[0].decidedTax, null);
const official = JSON.parse(fs.readFileSync('src/data/statistics/group-stat-2024.json'));
assert.equal(official.length, 28);
assert.equal(official.filter((r) => r.GROUP_TYPE === 'GENDER_AGE').length, 12);
const statMetadata = JSON.parse(fs.readFileSync('src/data/statistics/group-stat-metadata.json'));
for (const row of official) {
  assert.equal(
    row.AVG_REFUND_TAX,
    Math.round((statMetadata[row.STAT_ID].REFUND_TOTAL_MIL * 1e6) / row.PEOPLE_COUNT),
  );
  assert.equal(
    row.AVG_DECIDED_TAX,
    Math.round((statMetadata[row.STAT_ID].DECIDED_TOTAL_MIL * 1e6) / row.PEOPLE_COUNT),
  );
}
assert.equal(groups.rows[0].decidedTax, 510931);
assert.equal(groups.rows[2].decidedTax, 135390);
const simOriginal = structuredClone(initial);
const simCopy = {
  ...initial,
  nationalPension: 100000,
  housingSaving: 100000,
  pensionSaving: 100000,
  simulationSpend: [{ category: 'TRANSIT', payment: 'CHECK', amount: 1000000 }],
};
assert(
  taxService.calculate(simCopy).expectedRefund > taxService.calculate(simOriginal).expectedRefund,
);
assert.deepEqual(simOriginal, initial);
globalThis.window = {};
globalThis.localStorage = storage;
globalThis.sessionStorage = session;
const records = await import(pathToFileURL(path.join(dir, 'prototype-records.mjs')).href);
const dto = await import(pathToFileURL(path.join(dir, 'erd-contract.mjs')).href);
const uDemo = enterDemoSession(storage, session, 'USER');
const one = records.inquiryService.create('ERROR', '업로드 확인', '화면 테스트');
assert.equal(one.status, 'WAITING');
assert.equal(one.answer, '');
assert.throws(() => records.inquiryService.checking(one.id), /권한/);
enterDemoSession(storage, session, 'ADMIN');
assert(records.inquiryService.list().some((q) => q.id === one.id));
records.inquiryService.checking(one.id);
let checking = records.inquiryService.list().find((q) => q.id === one.id);
assert.equal(checking.status, 'CHECKING');
assert.equal(checking.answer, '');
assert.equal(checking.answeredAt, undefined);
assert.throws(() => records.inquiryService.answer(one.id, ' '), /답변/);
records.inquiryService.answer(one.id, '최종 답변입니다.');
checking = records.inquiryService.list().find((q) => q.id === one.id);
assert.equal(checking.status, 'ANSWERED');
assert(checking.answeredAt && checking.answeredBy);
records.saveCriterion({
  id: 'criterion',
  TAX_YEAR: 2026,
  TYPE_CODE: 'DEMO',
  SALARY_MIN: 0,
  SALARY_MAX: 30000000,
  RATE: 15,
  LIMIT_AMOUNT: 100000,
  SOURCE_NOTE: '테스트 전용 근거',
  UPDATED_AT: '',
  UPDATED_BY: '',
});
assert.equal(records.criteriaRecords().length, 1);
assert.throws(() => records.saveCriterion({ ...records.criteriaRecords()[0], RATE: 101 }), /확인/);
assert(records.accessRecords().some((r) => r.SCREEN === 'INQUIRY_ANSWER'));
const demoActor = demoService.current();
const noGender = demoService.members().find((u) => u.id !== demoActor.id && u.role === 'ADMIN');
if (noGender) {
  const accounts = JSON.parse(demoStorage(storage).getItem(ACCOUNT_KEY));
  accounts.find((u) => u.id === noGender.id).gender = '';
  demoStorage(storage).setItem(ACCOUNT_KEY, JSON.stringify(accounts));
  assert.throws(() => demoService.setRole(noGender.id, 'USER'), /성별/);
}
assert.deepEqual(dto.memberProfileDTO('여성'), { GENDER: 'F' });
assert.equal(dto.incomeDTO({ ...initial, pensionSaving: 100, irp: 200 }).PENSION_SAVING, 300);
assert.equal(dto.qualificationDTO({ ...initial, companySize: '중소기업' }).COMPANY_SIZE, 'SME');
assert.equal(
  dto.expenseDTO({ ...xlsxRows[0], uploadId: 10 }, { GENERAL: 123 }).PAY_METHOD,
  'CHECK',
);
enterDemoSession(storage, session, 'USER');
assert.throws(() => records.criteriaRecords(), /권한/);
assert.throws(() => records.accessRecords(), /권한/);
console.log(
  'PASS: ERD v3.8 withdrawal retention and login denial; signup checks, verification failure/expiry/retry, age KST, separate consent records, financial consent, USER-only registration, username/email login, locks, last/self admin protection and withdrawal retention; CSV/XLSX date cells/column aliases/cancellation/error rows, inquiry transitions/admin checks/criteria/logs/ERD DTO, official 28-group source averages/boundaries, simulation additions, multi-file CSV/methods/duplicates/deletion, classification evidence/15 limit, legacy monthly rent re-entry, family validation, zero/additional payment, independent 3-bar groups, original simulation and isolated demo roles.',
);
fs.rmSync(dir, { recursive: true, force: true });
