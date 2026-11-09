import { getTaxYear } from './tax-year.js';
import metadata from '../data/statistics/group-stat-metadata.json';
// 제공된 2024년 통계 스냅샷에서 독립된 두 그룹을 조회합니다. TODO: 동일 구조의 서버 조회 API로 교체할 수 있습니다.
import { taxService } from '../api/services.js';
import stats from '../data/statistics/group-stat-2024.json';
export function groupComparison(d, result = taxService.calculate(d)) {
  const taxYear = getTaxYear(d);
  const age = taxYear - Number(d.birth.slice(0, 4));
  const gender = d.gender === '여성' ? 'F' : d.gender === '남성' ? 'M' : null;
  const a = stats.find(
    (r) =>
      r.GROUP_TYPE === 'GENDER_AGE' &&
      r.GENDER === gender &&
      r.AGE_MIN !== null &&
      age >= r.AGE_MIN &&
      (r.AGE_MAX === null || age <= r.AGE_MAX),
  );
  const s = stats.find(
    (r) =>
      r.GROUP_TYPE === 'SALARY' &&
      r.SALARY_MIN !== null &&
      d.salary > r.SALARY_MIN &&
      (r.SALARY_MAX === null || d.salary <= r.SALARY_MAX),
  );
  const valid = !!a;
  const r = result,
    ageGroup = a?.GROUP_LABEL.replace(/^(남성|여성) /, '') || '성별·연령 정보 확인 필요',
    salaryGroup = s?.GROUP_LABEL || '총급여 구간 없음';
  return {
    taxYear,
    salaryPopulation: metadata[s?.STAT_ID]?.POPULATION || '조회 대상 없음',
    ageGroup,
    salaryGroup,
    valid,
    ageStat: a,
    salaryStat: s,
    rows: [
      {
        label: a ? `${ageGroup} ${d.gender} 평균` : '성별·연령 정보 확인 필요',
        decidedTax: a?.AVG_DECIDED_TAX ?? null,
        expectedRefund: a?.AVG_REFUND_TAX ?? null,
        kind: '2024 국세통계 · 성별·연령 집단',
      },
      {
        label: '나의 계산 결과',
        decidedTax: r.decidedTax,
        expectedRefund: r.expectedRefund,
        kind:
          r.expectedRefund < 0
            ? `${taxYear}년 데모 · 추가 납부 ${Math.abs(r.expectedRefund).toLocaleString()}원`
            : `${taxYear}년 데모 계산`,
      },
      {
        label: `${salaryGroup} 집단 평균`,
        decidedTax: s?.AVG_DECIDED_TAX ?? null,
        expectedRefund: s?.AVG_REFUND_TAX ?? null,
        kind: '2024 국세통계 · 총급여 집단',
      },
    ],
  };
}
