import { getTaxYear, getDefaultTaxYear } from './tax-year.js';
// 화면용 거래 합계와 자격 안내 상태를 구성합니다. 실제 법정 자격 확정 로직은 아직 연결되지 않았습니다.
import { groupComparison } from './group-model.js';
import { isCounted } from '../api/expense-service.js';
import { categories, taxService, settlementLabel } from '../api/services.js';
export const TAX_YEAR = getDefaultTaxYear();
export const TAX_GUIDANCE =
  'https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7794&mi=2458';
export function yearOf(date) {
  const match = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(date.trim());
  if (!match) return null;
  const [, y, m, d] = match.map(Number),
    test = new Date(Date.UTC(y, m - 1, d));
  return test.getUTCFullYear() === y && test.getUTCMonth() === m - 1 && test.getUTCDate() === d
    ? y
    : null;
}
export function youthStatus(data) {
  return ['미해당', '아니요'].includes(data.sme)
    ? {
        status: '비해당',
        reason: '자가 입력한 감면 자격이 미해당입니다. 실제 자격 심사는 연결되지 않았습니다.',
      }
    : {
        status: '확인 필요',
        reason: ['해당', '예'].includes(data.sme)
          ? '자가 입력은 해당이지만 취업 당시 연령·병역·기업 업종/규모·감면기간 및 신청 증빙이 확인되지 않았습니다.'
          : '감면 자격과 증빙이 확인되지 않았습니다.',
      };
}
export function dashboardModel(data, transactions, result = taxService.calculate(data)) {
  const taxYear = getTaxYear(data);
  const allRows = transactions.filter((t) => yearOf(t.date) === taxYear);
  const rows = allRows.filter(isCounted);
  const dates = rows
    .map((t) => t.date)
    .sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
  const total = rows.reduce((a, t) => a + t.amount, 0);
  // 동일 연도의 업로드 거래에서 소비 유형을 집계합니다. 계산 응답 details에서 추정하지 않습니다.
  const categoryOf = (row) => (row.category === '공제 제외' ? '공제 대상 아님' : row.category);
  const types = categories.map((category) => {
    const categoryRows = rows.filter((row) => categoryOf(row) === category);
    const heldCount = allRows.filter(
      (row) => categoryOf(row) === category && !isCounted(row),
    ).length;
    const matchedCount = categoryRows.filter((row) =>
      /대조.*일치|상호명 일치/.test(row.method),
    ).length;
    return {
      category,
      spent: categoryRows.reduce((sum, row) => sum + row.amount, 0),
      count: categoryRows.length,
      heldCount,
      matchedCount,
      unmatchedCount: categoryRows.length - matchedCount,
      beforeLimit: null,
      final: null,
    };
  });
  const matched = rows.filter((t) => /대조.*일치|상호명 일치/.test(t.method)).length;
  const ml = rows.filter((t) => /ML|머신러닝|모델 예측/i.test(t.method)).length;
  const user = rows.filter((t) => /사용자 수정|사용자 확인/.test(t.method)).length;
  const other = rows.length - matched - ml - user;
  const age = yearOf(data.birth) !== null ? taxYear - Number(data.birth.slice(0, 4)) : null;
  return {
    result,
    taxYear,
    rows,
    allRows,
    held: allRows.length - rows.length,
    types,
    total,
    excluded: transactions.length - allRows.length,
    period: dates.length ? `${dates[0]} ~ ${dates[dates.length - 1]}` : '거래 없음',
    annualInput: data.credit + data.debit + data.cash,
    minimum: data.salary * 0.25,
    matched,
    ml,
    user,
    other,
    needsReview: rows.length,
    youth: youthStatus(data),
    ageGroup: groupComparison(data).ageGroup,
    salaryGroup: groupComparison(data).salaryGroup,
    cultureSalary:
      data.salary <= 70000000
        ? '급여 요건 충족 · 거래 적격은 확인 필요'
        : '급여 요건 미충족 · 문화체육 우대 공제율 미적용',
  };
}
export function dashboardReply(q, data) {
  const r = taxService.calculate(data),
    y = youthStatus(data);
  const label = settlementLabel(r.expectedRefund);
  const result = `현재 ${getTaxYear(data)}년 귀속 데모 결과는 기납부세액 ${r.withheldTax.toLocaleString()}원, 예상 결정세액 ${r.decidedTax.toLocaleString()}원, ${label} ${Math.abs(r.expectedRefund).toLocaleString()}원입니다. 실제 세법 계산은 미연동입니다.`;
  if (/청년|서류|자격|혜택/.test(q))
    return `${result}\n청년 감면 상태: ${y.status}. ${y.reason} 확인할 자료는 감면 신청서, 취업·근로 증빙, 기업의 대상 업종·규모 확인자료와 필요한 경우 병역 증빙입니다. 화면에서 적용 가능 여부나 실제 감면액은 확정하지 않습니다.`;
  if (/카드|공제|차이|계산|지출/.test(q))
    return `${result}\n소득공제는 과세 대상 소득을 줄이고, 세액공제는 계산된 세금을 줄입니다. 지출액, 소득공제액, 세금 감소액은 서로 다릅니다. 결제수단별 거래내역, 최저사용기준과 한도 계산이 미연동이므로 최종 카드 소득공제액을 안내할 수 없습니다. 이전 3,600,000원은 검증된 공제액이 아닙니다. 카드 상세 표의 지출액과 도넛은 동일한 ${getTaxYear(data)}년 거래자료를 사용합니다.`;
  return `${result}\n청년 감면은 ${y.status} 상태입니다. 조건 변경 시뮬레이션은 저장된 정보의 복사본을 사용하며 비교 결과도 예시입니다. 원본 정보는 바뀌지 않습니다. 항목별 확정 공제액과 실제 절세 효과는 계산 로직 연동 후 확인할 수 있습니다.`;
}
