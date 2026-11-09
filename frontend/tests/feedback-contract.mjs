import assert from 'node:assert/strict';
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const dir = fs.mkdtempSync(path.join(process.cwd(), 'tests/.feedback-'));
const modules = {
  year: 'src/utils/tax-year.js',
  result: 'src/api/calculation-contract.js',
  expense: 'src/api/expense-service.js',
  erd: 'src/api/erd-contract.js',
  services: 'src/api/services.js',
  benefits: 'src/utils/benefit-model.js',
};
const loaded = {};
for (const [name, entry] of Object.entries(modules)) {
  await build({
    entryPoints: [entry],
    outfile: `${dir}/${name}.mjs`,
    platform: 'node',
    format: 'esm',
    bundle: true,
    packages: 'external',
    logLevel: 'silent',
  });
  loaded[name] = await import(pathToFileURL(`${dir}/${name}.mjs`));
}
try {
  const { getDefaultTaxYear } = loaded.year;
  for (const [date, year] of [
    ['2027-02-01T00:00:00+09:00', 2026],
    ['2027-03-31T23:59:59+09:00', 2026],
    ['2027-04-01T00:00:00+09:00', 2027],
    ['2027-05-01T00:00:00+09:00', 2027],
    ['2026-12-31T23:59:59+09:00', 2026],
    ['2027-01-01T00:00:00+09:00', 2026],
  ])
    assert.equal(getDefaultTaxYear(new Date(date)), year);
  const rows = loaded.expense.parseUploadCSV(
    '거래일자,가맹점명,이용금액,사용구분\n2026-12-01,교보문고,10000,CHECK\n2027-01-02,가게,20000,CREDIT',
  );
  assert.deepEqual(loaded.expense.uploadTotals(rows, 2026), { credit: 0, debit: 10000, cash: 0 });
  assert.deepEqual(loaded.expense.uploadTotals(rows, 2027), { credit: 20000, debit: 0, cash: 0 });
  assert.equal(rows.length, 2);
  const { initial, taxService } = loaded.services;
  const input = {
    ...initial,
    taxYear: 2026,
    nationalPension: 1000000,
    healthEmploymentInsurance: 500000,
    rent: 500000,
  };
  assert.equal(loaded.erd.incomeDTO(input).MONTHLY_RENT, 500000);
  assert.equal(loaded.erd.incomeDTO(input).SME_REDUCTION_YN, null);
  assert.equal(loaded.erd.qualificationDTO(input).HOMELESS_HEAD_YN, null);
  assert.equal(loaded.erd.incomeDTO({ ...input, sme: '아니요' }).SME_REDUCTION_YN, 'N');
  assert.equal(loaded.erd.incomeDTO({ ...input, sme: '예' }).SME_REDUCTION_YN, 'Y');
  assert.deepEqual(loaded.erd.insuranceInput(input), {
    nationalPension: 1000000,
    healthEmploymentInsurance: 500000,
  });
  assert(!('SOCIAL_INSURANCE' in loaded.erd.incomeDTO(input)));
  assert.throws(() => loaded.erd.consentDTO({}), /버전/);
  const versions = {
    TERMS_VERSION: 'team-terms',
    PRIVACY_VERSION: 'team-privacy',
    FINANCE_VERSION: 'team-finance',
    TERMS_AGREED_AT: '2026-10-30',
    PRIVACY_AGREED_AT: '2026-10-30',
    FINANCE_AGREED_AT: '2026-10-30',
  };
  assert.equal(loaded.erd.consentDTO(versions).TERMS_VERSION, 'team-terms');
  const row = { ...rows[0], uploadId: 'local-file' };
  assert.throws(() => loaded.erd.expenseDTO(row), /UPLOAD_ID/);
  assert.throws(() => loaded.erd.expenseDTO(row, {}, { 'local-file': 21 }), /CATEGORY_ID/);
  const dto = loaded.erd.expenseDTO(row, { CULTURE: 789 }, { 'local-file': 21 });
  assert.equal(dto.CATEGORY_ID, 789);
  assert.equal(dto.UPLOAD_ID, 21);
  assert(!('CATEGORY_CODE' in dto));
  assert(!('MEMBER_ID' in dto));
  assert.throws(
    () => loaded.erd.expenseDTO({ ...row, paymentMethod: '', PAY_METHOD: '' }),
    /결제수단/,
  );
  const raw = {
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
        sourceNote: '근거 확인',
      },
      {
        typeCode: 'CARD_LIMIT',
        typeName: '카드 한도',
        kind: 'CARD_RULE',
        baseAmount: 0,
        deductionAmount: -100000,
        sourceNote: '',
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
  assert.deepEqual(loaded.result.parseCalculationResult(raw), raw);
  assert.equal(loaded.result.cardDeductionTotal(raw.details), 200000);
  assert.match(loaded.result.deductionPresentation(raw.details[1]).explanation, /조정액/);
  assert.equal(
    loaded.result.parseCalculationResult({ ...raw, expectedRefund: -123 }).expectedRefund,
    -123,
  );
  assert.equal(
    loaded.result.parseCalculationResult({ ...raw, expectedRefund: 0 }).expectedRefund,
    0,
  );
  assert.throws(
    () =>
      loaded.result.parseCalculationResult({
        error: 'NO_CRITERIA',
        message: '해당 연도 기준값이 없어요',
      }),
    /기준값/,
  );
  assert.throws(
    () => loaded.result.parseCalculationResult({ ...raw, expectedRefund: NaN }),
    /결과/,
  );
  const result = taxService.calculate(input);
  assert.equal(result.details.find((d) => d.typeCode === 'RENT').baseAmount, 6000000);
  for (const key of ['tax', 'paid', 'refund', 'deductions', 'beforeDeductions'])
    assert(!(key in result));
  for (const item of result.details)
    for (const key of ['effect', 'formula', 'status', 'note']) assert(!(key in item));
  assert.equal(result.taxableIncome, null); // 미연동 과세표준은 임의 숫자를 만들지 않음
  assert.equal(loaded.benefits.benefitChecks(initial).length, 3);
  assert.equal(loaded.benefits.benefitChecks(initial)[0].status, '확인 필요');
  assert.equal(loaded.benefits.benefitChecks({ ...initial, sme: '아니요' })[0].status, '비해당');
  assert.equal(loaded.benefits.benefitChecks({ ...initial, sme: '예' })[0].status, '해당');
  assert.equal(
    loaded.result.migrateCalculationHistory({ refund: -50, tax: 200, paid: 150 }).expectedRefund,
    -50,
  );
  console.log(
    'PASS: 귀속 연도/KST 경계, 연도별 파일 집계 보존, 월세/보험료 분리, 미입력 3상태, 동의 버전 차단, 서버 발급 FK/인증 경계, 실제 계산 응답/음수/0/오류, 이전 이력 호환, 혜택 카드.',
  );
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
