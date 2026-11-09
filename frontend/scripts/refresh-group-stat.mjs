// Reproduce the 2024 GROUP_STAT snapshot from the two committed KOSIS XLSX originals.
// Usage: node scripts/refresh-group-stat.mjs (run from repository root).
import * as XLSX from 'xlsx';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const base = 'src/data/statistics',
  groups = [],
  files = [];
const num = (v) => (v == null || v === '' || v === '-' ? 0 : Number(v));
for (const [kind, stem, fid, offset] of [
  ['GENDER_AGE', 'gender-age-2024', 1, 3],
  ['SALARY', 'salary-2024', 3, 2],
]) {
  const rawPath = `${base}/${stem}.xlsx`,
    book = XLSX.read(fs.readFileSync(rawPath), { type: 'buffer' }),
    raw = XLSX.utils.sheet_to_json(book.Sheets['데이터'], { header: 1, defval: '' });
  assert.equal(String(raw[0][offset]), '2024');
  assert.equal(raw[1][offset + 132], '결정세액');
  assert.equal(raw[1][offset + 138], '환급세액');
  const source = kind === 'GENDER_AGE' ? '국세청 4.2.3 성·연령' : '국세청 4.2.4 과세대상근로소득';
  files.push(
    {
      FILE_ID: fid,
      FILE_NAME: `${stem}.xlsx`,
      FILE_PATH: rawPath,
      FILE_KIND: 'ORIGINAL',
      ORIGIN_FILE_ID: null,
      TAX_YEAR: 2024,
      SOURCE_NAME: source,
      DATA_ORIGIN: 'COLLECTED',
      BASE_DATE: '2026-10-28',
      sha256: crypto.createHash('sha256').update(fs.readFileSync(rawPath)).digest('hex'),
    },
    {
      FILE_ID: fid + 1,
      FILE_NAME: `${stem}.csv`,
      FILE_PATH: `${base}/${stem}.csv`,
      FILE_KIND: 'CLEANED',
      ORIGIN_FILE_ID: fid,
      TAX_YEAR: 2024,
      SOURCE_NAME: source,
      DATA_ORIGIN: 'COLLECTED',
      BASE_DATE: null,
    },
  );
  function build(parts, label, extra) {
    const n = parts.reduce((sum, r) => sum + num(r[offset]), 0),
      sumAt = (pos) => parts.reduce((sum, r) => sum + num(r[offset + pos]), 0);
    const row = {
      STAT_ID: groups.length + 1,
      FILE_ID: fid + 1,
      TAX_YEAR: 2024,
      GROUP_TYPE: kind,
      GROUP_LABEL: label,
      GENDER: null,
      AGE_MIN: null,
      AGE_MAX: null,
      SALARY_MIN: null,
      SALARY_MAX: null,
      PEOPLE_COUNT: n,
      TOTAL_SALARY_MIL: sumAt(19),
      REFUND_PEOPLE_COUNT: sumAt(138),
      ...extra,
    };
    for (const [key, pos] of [
      ['AVG_SALARY', 19],
      ['AVG_DECIDED_TAX', 133],
      ['AVG_WITHHELD_TAX', 135],
      ['AVG_REFUND_TAX', 139],
      ['AVG_PAYABLE_TAX', 141],
      ['AVG_CARD_DEDUCTION', 71],
      ['AVG_RENT_CREDIT', 121],
      ['AVG_SME_REDUCTION', 129],
    ])
      row[key] = n ? Math.round((sumAt(pos) * 1e6) / n) : null;
    Object.assign(row, { DECIDED_TOTAL_MIL: sumAt(133), REFUND_TOTAL_MIL: sumAt(139) });
    groups.push(row);
  }
  const start = groups.length;
  if (kind === 'GENDER_AGE') {
    const labels = [
      '30세 미만',
      '30세 이상~40세 미만',
      '40세 이상~50세 미만',
      '50세 이상~60세 미만',
      '60세 이상~70세 미만',
      '70세 이상',
    ];
    for (const [gender, pos] of [
      ['M', 7],
      ['F', 14],
    ])
      labels.forEach((label, i) =>
        build([raw[pos + i], raw[pos + i + 15]], `${gender === 'M' ? '남성' : '여성'} ${label}`, {
          GENDER: gender,
          AGE_MIN: [0, 30, 40, 50, 60, 70][i],
          AGE_MAX: [29, 39, 49, 59, 69, null][i],
          POPULATION: '결정세액 있는 자·없는 자 합산',
        }),
      );
  } else {
    const bounds = [
      10000000,
      15000000,
      20000000,
      30000000,
      40000000,
      45000000,
      50000000,
      60000000,
      80000000,
      100000000,
      200000000,
      300000000,
      500000000,
      1000000000,
      null,
    ];
    bounds.forEach((limit, i) => {
      const lo = i ? bounds[i - 1] : 0,
        label =
          (lo ? `${(lo / 10000).toLocaleString('en-US')}만 원 초과~` : '총급여 ') +
          (limit ? `${(limit / 10000).toLocaleString('en-US')}만 원 이하` : '상한 없음');
      build([raw[6 + i], ...(i < 10 ? [raw[22 + i]] : [])], label, {
        SALARY_MIN: lo,
        SALARY_MAX: limit,
        POPULATION:
          i < 10
            ? '결정세액 있는 자·없는 자 합산'
            : '결정세액 있는 자만 (없는 자 1억 초과는 세부 구간 없음)',
      });
    });
    build([raw[32]], '1억 초과 (결정세액 없는 자 · 구간 매칭 제외)', {
      POPULATION: '결정세액 없는 자만',
    });
  }
  const subset = groups.slice(start),
    keys = Object.keys(subset[0]),
    csv =
      keys.join(',') +
      '\n' +
      subset
        .map((row) => keys.map((k) => JSON.stringify(String(row[k] ?? ''))).join(','))
        .join('\n') +
      '\n';
  fs.writeFileSync(`${base}/${stem}.csv`, csv);
}
assert.equal(groups.length, 28);
// 검증용 원본 합계·모집단 설명은 DB 컬럼으로 내보내지 않고 별도 보관합니다.
const metadata = {};
for (const row of groups) {
  metadata[row.STAT_ID] = {};
  for (const key of [
    'POPULATION',
    'REFUND_PEOPLE_COUNT',
    'DECIDED_TOTAL_MIL',
    'REFUND_TOTAL_MIL',
  ]) {
    if (key in row) {
      metadata[row.STAT_ID][key] = row[key];
      delete row[key];
    }
  }
}
fs.writeFileSync(`${base}/group-stat-2024.json`, JSON.stringify(groups, null, 2) + '\n');
fs.writeFileSync(`${base}/group-stat-metadata.json`, JSON.stringify(metadata, null, 2) + '\n');
fs.writeFileSync(`${base}/stat-file.json`, JSON.stringify(files, null, 2) + '\n');
console.log('Reproduced 28 groups from 2024 originals; all averages use group PEOPLE_COUNT.');
