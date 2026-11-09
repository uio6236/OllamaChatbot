// 계산 API의 응답과 UI 설명은 분리합니다. 선택 문구(effect/formula 등)에 의존하지 않습니다.
export const kindLabels = {
  INCOME_DEDUCTION: '소득공제',
  TAX_CREDIT: '세액공제',
  TAX_REDUCTION: '세액감면',
  CARD: '카드 소득공제',
  CARD_RULE: '카드 한도 조정',
};
const numeric = (value, field) => {
  if (typeof value !== 'number' || !Number.isFinite(value))
    throw Error(`${field} 계산 결과를 확인해주세요.`);
  return value;
};
export function parseCalculationResult(raw, { allowPending = false } = {}) {
  if (raw?.error) {
    const error = new Error(raw.message || '계산 결과를 불러올 수 없습니다.');
    error.code = raw.error;
    throw error;
  }
  if (!raw || !Array.isArray(raw.details)) throw Error('항목별 계산 결과가 없습니다.');
  const result = {};
  for (const key of [
    'taxYear',
    'totalSalary',
    'withheldTax',
    'taxableIncome',
    'calculatedTax',
    'decidedTax',
    'expectedRefund',
  ]) {
    result[key] =
      allowPending && key === 'taxableIncome' && raw[key] === null ? null : numeric(raw[key], key);
  }
  result.details = raw.details.map((item) => ({
    typeCode: String(item.typeCode || ''),
    typeName: String(item.typeName || '항목명 확인 필요'),
    kind: String(item.kind || ''),
    baseAmount: numeric(item.baseAmount, 'baseAmount'),
    deductionAmount: numeric(item.deductionAmount, 'deductionAmount'),
    sourceNote: typeof item.sourceNote === 'string' ? item.sourceNote : '',
  }));
  return result;
}
// 예전 브라우저 계산 이력만 새 계약으로 변환합니다. 새 API 응답에는 이전 필드가 필요하지 않습니다.
export function migrateCalculationHistory(row) {
  if ('expectedRefund' in row) return row;
  return {
    ...row,
    taxYear: row.data?.taxYear ?? null,
    decidedTax: row.tax ?? 0,
    withheldTax: row.paid ?? 0,
    expectedRefund: row.refund ?? 0,
    calculatedTax: row.beforeDeductions ?? 0,
    taxableIncome: null,
    details: [],
    legacyResult: true,
  };
}
export function deductionPresentation(item) {
  return {
    kindLabel: kindLabels[item.kind] || item.kind || '유형 확인 필요',
    explanation:
      item.kind === 'CARD_RULE' && item.deductionAmount < 0
        ? '카드 공제한도 적용에 따른 조정액입니다. 카드 공제 합계에 음수 그대로 반영합니다.'
        : item.deductionAmount === 0
          ? '이번 결과의 공제액은 0원입니다. 미선택·미적용도 정상 결과입니다.'
          : '',
  };
}
export const cardDeductionTotal = (details) =>
  details
    .filter((d) => ['CARD', 'CARD_RULE'].includes(d.kind))
    .reduce((sum, d) => sum + d.deductionAmount, 0);
