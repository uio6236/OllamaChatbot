import { getDefaultTaxYear, getTaxYear } from '../utils/tax-year.js';
import { parseCalculationResult } from './calculation-contract.js';
// 입력 기본값·브라우저 저장·기존 데모 계산·상호명 대조·고정 AI 응답입니다. TODO: 기존 함수 경계를 Spring Boot API로 교체합니다.
export const initial = {
  taxYear: getDefaultTaxYear(),
  nationalPension: 0,
  healthEmploymentInsurance: 0,
  housingSaving: 0,
  pensionSaving: 0,
  irp: 0,
  name: '사용자',
  birth: '1999-05-20',
  gender: '여성',
  email: 'hope@example.com',
  salary: 36000000,
  paid: 1523000,
  credit: 0,
  debit: 0,
  cash: 0,
  family: 0,
  children: 0,
  militaryMonths: 0,
  companySize: '확인 필요',
  headOfHousehold: '확인 필요',
  rentPeriod: 'monthly',
  rent: 0,
  housing: '무주택',
  sme: '확인 필요',
  employed: '2023-03-01',
  consent: false,
};
export function annualRent(d) {
  return (d.rent ?? 0) * 12;
}
export function normalizeTaxData(d) {
  return {
    ...d,
    taxYear: getTaxYear(d),
    nationalPension: d.nationalPension ?? 0,
    healthEmploymentInsurance: d.healthEmploymentInsurance ?? 0,
    // 과거 통합 보험료를 임의로 배분하지 않습니다. 원본 값은 보존하고 재입력 안내만 합니다.
    legacyInsuranceNeedsReview:
      d.legacyInsuranceNeedsReview || (d.socialInsurance > 0 && d.nationalPension == null),
    housingSaving: d.housingSaving ?? 0,
    pensionSaving: d.pensionSaving ?? 0,
    irp: d.irp ?? 0,
    children: d.children ?? 0,
    militaryMonths: d.militaryMonths ?? 0,
    companySize: d.companySize ?? '확인 필요',
    headOfHousehold: d.headOfHousehold ?? '확인 필요',
    rent: d.rentPeriod === 'monthly' ? d.rent : 0,
    legacyAnnualRent: d.legacyAnnualRent ?? (d.rentPeriod !== 'monthly' ? d.rent : null),
    legacyRentNeedsReview: d.legacyRentNeedsReview || (d.rentPeriod !== 'monthly' && d.rent > 0),
    rentPeriod: 'monthly',
  };
}
export function validateTaxData(d) {
  if (!Number.isInteger(d.taxYear) || d.taxYear < 1900 || d.taxYear > 9999)
    return '귀속 연도를 확인해주세요.';
  if (!['확인 필요', '예', '아니요'].includes(d.headOfHousehold))
    return '무주택 세대주 여부를 확인해주세요.';
  if (!['확인 필요', '예', '아니요', '해당', '미해당'].includes(d.sme))
    return '감면 신청 여부를 확인해주세요.';
  if (
    !Number.isInteger(d.family) ||
    d.family < 0 ||
    d.family > 20 ||
    !Number.isInteger(d.children ?? 0) ||
    (d.children ?? 0) < 0 ||
    (d.children ?? 0) > d.family
  )
    return '20세 이하 자녀 수는 추가 부양가족 수(본인 제외) 이하여야 합니다.';
  if (
    !Number.isInteger(d.militaryMonths ?? 0) ||
    (d.militaryMonths ?? 0) < 0 ||
    (d.militaryMonths ?? 0) > 120
  )
    return '군 복무 개월 수는 0~120 사이의 정수로 입력해주세요.';
  if (
    [
      d.salary,
      d.paid,
      d.credit,
      d.debit,
      d.cash,
      d.rent,
      d.nationalPension ?? 0,
      d.healthEmploymentInsurance ?? 0,
      d.housingSaving ?? 0,
      d.pensionSaving ?? 0,
      d.irp ?? 0,
      ...(d.simulationSpend || []).map((r) => r.amount),
    ].some((v) => !Number.isFinite(v) || v < 0)
  )
    return '금액은 0 이상으로 입력해주세요.';
  if (!['중소기업', '중견기업', '대기업', '확인 필요'].includes(d.companySize ?? '확인 필요'))
    return '회사 규모를 선택해주세요.';
  return '';
}
export function settlementLabel(refund) {
  return refund > 0 ? '예상 환급액' : refund < 0 ? '예상 추가 납부액' : '환급 및 추가 납부 예상액';
}
export const categories = ['일반', '대중교통', '전통시장', '문화체육', '공제 대상 아님'];
export const categoryCodes = {
  일반: 'GENERAL',
  대중교통: 'TRANSIT',
  전통시장: 'MARKET',
  문화체육: 'CULTURE',
  '공제 제외': 'EXCLUDED',
  '공제 대상 아님': 'EXCLUDED',
};
export const sampleTransactions = [
  ['2026-12-18', '희망마트', 84500, '일반'],
  ['2026-12-17', '서울교통공사', 65000, '대중교통'],
  ['2026-12-16', '광장시장', 42000, '전통시장'],
  ['2026-12-15', '교보문고', 28000, '문화체육'],
  ['2026-12-14', '보험료 자동납부', 90000, '공제 제외'],
  ['2026-12-13', '블루커피', 5800, '일반'],
].map((a, i) => ({
  id: i,
  date: String(a[0]),
  merchant: String(a[1]),
  amount: Number(a[2]),
  category: String(a[3]),
  method: i === 0 || i === 5 ? '미매칭 · 확인 필요' : '예시 상호명 일치',
}));
const scopedKey = (key) =>
  key.startsWith('admin-')
    ? 'hope-' + key
    : 'hope-user-' +
      (typeof window !== 'undefined'
        ? sessionStorage.getItem('hope-session-v1') || 'guest'
        : 'guest') +
      '-' +
      key;
export const userService = {
  load: (key, fallback) => {
    try {
      return JSON.parse(localStorage.getItem(scopedKey(key)) || 'null') ?? fallback;
    } catch {
      return fallback;
    }
  },
  save: (key, value) => localStorage.setItem(scopedKey(key), JSON.stringify(value)),
};
// TODO: Spring Boot 계산 API로 교체합니다. 이 어댑터는 기존 체험 계산만 수행합니다.
export const taxService = {
  calculate: (d) => {
    const extraCard = (d.simulationSpend || []).reduce(
      (sum, row) => sum + row.amount * (row.payment === 'CREDIT' ? 0.15 : 0.3),
      0,
    );
    const cardAmount = d.credit * 0.15 + (d.debit + d.cash) * 0.3 + extraCard;
    const familyAmount = d.family * 300000;
    const calculatedTax = Math.round(1640000 + (d.salary - 36000000) * 0.06);
    const insurance = (d.nationalPension ?? 0) + (d.healthEmploymentInsurance ?? 0);
    const reduction =
      cardAmount * 0.15 +
      familyAmount * 0.15 +
      annualRent(d) * 0.1 +
      (['해당', '예'].includes(d.sme) ? 200000 : 0) +
      insurance * 0.15 +
      (d.housingSaving ?? 0) * 0.04 +
      ((d.pensionSaving ?? 0) + (d.irp ?? 0)) * 0.1;
    const decidedTax = Math.max(0, Math.round(calculatedTax - reduction));
    const detail = (typeCode, typeName, kind, baseAmount, deductionAmount) => ({
      typeCode,
      typeName,
      kind,
      baseAmount,
      deductionAmount: Math.round(deductionAmount),
      sourceNote: '체험용 계산 결과 · 법정 계산 근거 및 신고안내 쪽수는 계산 API 연동 후 제공',
    });
    return parseCalculationResult(
      {
        taxYear: getTaxYear(d),
        totalSalary: d.salary,
        withheldTax: d.paid,
        // 과세표준의 법정 계산은 미연동입니다. 화면에서 체험값임을 함께 표시합니다.
        taxableIncome: null,
        calculatedTax,
        decidedTax,
        expectedRefund: d.paid - decidedTax,
        details: [
          detail('CARD_CREDIT', '신용카드', 'CARD', d.credit, d.credit * 0.15),
          detail('CARD_CHECK', '체크카드', 'CARD', d.debit, d.debit * 0.3),
          detail('CARD_CASH', '현금영수증', 'CARD', d.cash, d.cash * 0.3),
          
          detail('CARD_TRANSIT', '대중교통', 'CARD', 0, 0),
          detail('CARD_MARKET', '전통시장', 'CARD', 0, 0),
          detail('CARD_CULTURE', '문화체육', 'CARD', 0, 0),
          ...(extraCard
            ? [
                detail(
                  'DEMO_EXTRA_SPEND',
                  '가상 추가 소비',
                  'CARD',
                  (d.simulationSpend || []).reduce((s, r) => s + r.amount, 0),
                  extraCard,
                ),
              ]
            : []),
          detail('EARNED_DEDUCTION', '근로소득공제', 'INCOME_DEDUCTION', 0, 0),
          detail('FAMILY', '인적공제(본인·부양가족)', 'INCOME_DEDUCTION', d.family, familyAmount),
          detail(
            'NATIONAL_PENSION',
            '국민연금',
            'INCOME_DEDUCTION',
            d.nationalPension ?? 0,
            d.nationalPension ?? 0,
          ),
          detail(
            'HEALTH_EMPLOYMENT',
            '건강·고용보험료',
            'INCOME_DEDUCTION',
            d.healthEmploymentInsurance ?? 0,
            d.healthEmploymentInsurance ?? 0,
          ),
          detail('RENT', '월세', 'TAX_CREDIT', annualRent(d), annualRent(d) * 0.1),
          detail(
            'HOUSING_SAVING',
            '주택청약',
            'INCOME_DEDUCTION',
            d.housingSaving ?? 0,
            (d.housingSaving ?? 0) * 0.04,
          ),
          detail(
            'PENSION_SAVING',
            '연금저축·IRP',
            'TAX_CREDIT',
            (d.pensionSaving ?? 0) + (d.irp ?? 0),
            ((d.pensionSaving ?? 0) + (d.irp ?? 0)) * 0.1,
          ),
          detail(
            'SME',
            '중소기업 취업자 감면',
            'TAX_REDUCTION',
            0,
            ['해당', '예'].includes(d.sme) ? 200000 : 0,
          ),
          detail('EARNED_CREDIT', '근로소득세액공제', 'TAX_CREDIT', 0, 0),
          detail('STANDARD_CREDIT', '표준세액공제', 'TAX_CREDIT', 0, 0),
          detail('CARD_LIMIT_BASE', '카드 기본한도', 'CARD_RULE', 0, -100000),
          detail('CARD_LIMIT_EXTRA', '카드 추가한도', 'CARD_RULE', 0, -50000),
        ],
      },
      { allowPending: true },
    );
  },
};
export const merchantService = {
  classify: (name) => {
    const normalize = (value) => value.replace(/\s/g, '').toLowerCase();
    const defaults = [
      ['서울교통공사', '대중교통'],
      ['코레일', '대중교통'],
      ['광장시장', '전통시장'],
      ['교보문고', '문화체육'],
      ['국립박물관', '문화체육'],
      ['보험료 자동납부', '공제 대상 아님'],
    ];
    let list = defaults;
    try {
      if (typeof localStorage !== 'undefined') {
        const raw = JSON.parse(localStorage.getItem('hope-admin-merchants') || 'null');
        if (typeof raw === 'string')
          list = raw
            .split('\n')
            .map((line) => line.split(',').map((v) => v.trim()))
            .filter((p) => p.length === 2 && (categories.includes(p[1]) || p[1] === '공제 제외'));
      }
    } catch {}
    const priority = ['공제 대상 아님', '공제 제외', '대중교통', '전통시장', '문화체육', '일반'];
    const match = [...list]
      .sort((a, b) => priority.indexOf(a[1]) - priority.indexOf(b[1]))
      .find(([merchant]) => normalize(name) === normalize(merchant));
    return {
      CATEGORY_CODE: categoryCodes[match?.[1] || '일반'],
      LIST_ID: match ? list.indexOf(match) + 1 : null,
      category: match?.[1] === '공제 제외' ? '공제 대상 아님' : match?.[1] || '일반',
      method: match ? '예시 공공데이터 상호명 대조 일치' : '상호명 미매칭 · 일반 추정',
      matchedMerchant: match?.[0],
      classificationBasis: match
        ? `예시 공공데이터 목록의 «${match[0]}»와 공백 제외 완전 일치. 실제 공공데이터 API는 미연동입니다.`
        : '예시 공공데이터 목록에 일치하는 상호명이 없어 일반으로 추정 분류했습니다.',
    };
  },
};
export function parseCSV(text) {
  const lines = text
    .replace(/^\uFEFF/, '')
    .trim()
    .split(/\r?\n/);
  const parse = (s) => {
    const a = [];
    let v = '',
      q = false;
    for (let i = 0; i < s.length; i++) {
      if (s[i] === '"') {
        if (q && s[i + 1] === '"') {
          v += '"';
          i++;
        } else q = !q;
      } else if (s[i] === ',' && !q) {
        a.push(v.trim());
        v = '';
      } else v += s[i];
    }
    if (q) throw Error('따옴표 형식을 확인해주세요.');
    a.push(v.trim());
    return a;
  };
  const h = parse(lines.shift() || '');
  const idx = ['날짜', '상호명', '금액'].map((k) => h.indexOf(k));
  if (idx.includes(-1)) throw Error('CSV 첫 행에 날짜,상호명,금액 헤더가 필요합니다.');
  if (!lines.length) throw Error('거래내역이 없습니다.');
  return lines.filter(Boolean).map((l, i) => {
    const a = parse(l),
      amount = Number((a[idx[2]] || '').replace(/,/g, ''));
    if (!a[idx[0]] || !a[idx[1]] || !a[idx[2]]?.trim() || !Number.isFinite(amount) || amount < 0)
      throw Error(`${i + 2}행의 날짜·상호명·금액을 확인해주세요.`);
    return {
      id: Date.now() + i,
      date: a[idx[0]],
      merchant: a[idx[1]],
      amount,
      ...merchantService.classify(a[idx[1]]),
    };
  });
}
export const aiService = {
  reply: (q, d, baseline) => {
    const r = taxService.calculate(d);
    if (baseline) {
      const old = taxService.calculate(baseline);
      return `조건 변경으로 예상 환급액이 ${old.expectedRefund.toLocaleString()}원에서 ${r.expectedRefund.toLocaleString()}원으로 ${Math.abs(r.expectedRefund - old.expectedRefund).toLocaleString()}원 ${r.expectedRefund >= old.expectedRefund ? '늘었어요' : '줄었어요'}. 변경된 입력으로 비교한 체험용 결과입니다. 원본 정보는 그대로 유지돼요. 실제 세법 계산 결과는 아닙니다.`;
    }
    if (q.includes('청년') || q.includes('서류'))
      return '청년 중소기업 취업자 소득세 감면은 취업 당시 연령, 회사의 업종·규모, 취업일 등을 확인해야 해요. 근로계약서와 회사의 감면 신청 여부를 확인해주세요. 현재 확정되지 않은 자격은 계산에서 제외했어요.';
    if (q.includes('차이') || q.includes('소득공제'))
      return '소득공제는 세금을 매기는 소득을 줄이고, 세액공제는 계산된 세금을 줄여요. 공제액 전체가 환급되는 것은 아니에요. 이 화면의 금액은 시연용 계산 결과입니다.';
    return `기납부 소득세 ${r.withheldTax.toLocaleString()}원과 예시 결정세액 ${r.decidedTax.toLocaleString()}원의 차이로 ${settlementLabel(r.expectedRefund)}은 ${Math.abs(r.expectedRefund).toLocaleString()}원이에요. 체크카드 사용금액이나 주거 조건을 바꾸고 시뮬레이션으로 비교해보세요. 실제 신고 전에는 증빙과 국세청 기준 확인이 필요해요.`;
  },
};
