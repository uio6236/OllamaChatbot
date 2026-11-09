import { getDefaultTaxYear } from '../utils/tax-year.js';
// 파일의 서로 다른 컬럼을 공통 거래 형태로 변환합니다. TODO: 운영 업로드 검증·분류·거래 저장 API를 연결합니다.
import { merchantService } from './services.js';
export const columnAliases = {
  date: ['날짜', '거래일자', '거래일', '승인일시', '승인일자', '사용일자', '사용일시'],
  merchant: ['상호명', '가맹점명', '거래처명', '상호', '사용처'],
  amount: ['금액', '이용금액', '거래금액', '사용금액', '승인금액'],
  payment: ['결제수단', '사용구분', '카드구분', '카드종류'],
};
const methods = {
  신용카드: '신용카드',
  신용: '신용카드',
  CREDIT: '신용카드',
  체크카드: '체크카드',
  직불카드: '체크카드',
  체크: '체크카드',
  CHECK: '체크카드',
  DEBIT: '체크카드',
  현금영수증: '현금영수증',
  CASH: '현금영수증',
  CASH_RECEIPT: '현금영수증',
};
export const payCode = (label) =>
  ({
    신용카드: 'CREDIT',
    체크카드: 'CHECK',
    현금영수증: 'CASH',
    CREDIT: 'CREDIT',
    CHECK: 'CHECK',
    CASH: 'CASH',
  })[label];
function normalizedDate(value, row) {
  let v = String(value ?? '').trim();
  if (value instanceof Date)
    v = `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  const m =
    /^(\d{4})[-/.년]\s?(\d{1,2})[-/.월]\s?(\d{1,2})(?:일)?(?:[ T].*)?$/.exec(v) ||
    /^(\d{4})(\d{2})(\d{2})$/.exec(v);
  if (!m)
    throw Error(`${row}행 날짜가 올바르지 않습니다. YYYY-MM-DD 또는 승인일시 형식을 확인해주세요.`);
  const y = +m[1],
    mo = +m[2],
    d = +m[3],
    dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d)
    throw Error(`${row}행 날짜가 올바르지 않습니다.`);
  return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}
export function parseUploadTable(table, source = 'card', fallback = '') {
  if (table.length > 10001) throw Error('파일당 거래내역은 10,000건 이하로 업로드해주세요.');
  const header = (table[0] || []).map((v) => String(v ?? '').replace(/\s/g, ''));
  const index = (names) => header.findIndex((v) => names.includes(v));
  const di = index(columnAliases.date),
    mi = index(columnAliases.merchant),
    ai = index(columnAliases.amount),
    pi = index(columnAliases.payment);
  if ([di, mi, ai].includes(-1))
    throw Error(
      '지원하지 않는 양식입니다. 첫 행 헤더에 거래일자(승인일시), 가맹점명, 이용금액에 해당하는 열이 필요합니다.',
    );
  const rows = [];
  table.slice(1).forEach((r, i) => {
    if (r.every((v) => v === undefined || v === null || String(v).trim() === '')) return;
    const row = i + 2,
      date = normalizedDate(r[di], row),
      merchant = String(r[mi] ?? '').trim(),
      raw = String(r[ai] ?? '').trim(),
      amount = Number(raw.replace(/[,₩원\s]/g, ''));
    if (!merchant || !raw || !Number.isSafeInteger(amount))
      throw Error(`${row}행 가맹점명·금액을 확인해주세요. 취소 금액은 음수로 입력할 수 있습니다.`);
    const supplied = pi >= 0 ? String(r[pi] ?? '').trim() : '',
      method = methods[supplied.toUpperCase()];
    if (source === 'card' && method === '현금영수증')
      throw Error(`${row}행은 현금영수증입니다. 홈택스 파일 출처를 선택해주세요.`);
    const paymentMethod = source === 'hometax' ? '현금영수증' : method || fallback || '확인 필요';
    rows.push({
      id: Date.now() * 1000 + i,
      date,
      merchant,
      amount,
      ...merchantService.classify(merchant),
      source: 'upload',
      paymentMethod,
      PAY_METHOD: payCode(paymentMethod),
    });
  });
  if (!rows.length) throw Error('거래내역이 없습니다.');
  return rows;
}
export function parseUploadCSV(text, source = 'card', fallback = '') {
  const table = [];
  let row = [],
    value = '',
    quote = false;
  const input = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (c === '"') {
      if (quote && input[i + 1] === '"') {
        value += '"';
        i++;
      } else quote = !quote;
    } else if (c === ',' && !quote) {
      row.push(value);
      value = '';
    } else if ((c === '\n' || c === '\r') && !quote) {
      if (c === '\r' && input[i + 1] === '\n') i++;
      row.push(value);
      table.push(row);
      row = [];
      value = '';
    } else value += c;
  }
  if (quote) throw Error('따옴표 형식을 확인해주세요.');
  if (row.length || value) {
    row.push(value);
    table.push(row);
  }
  return parseUploadTable(table, source, fallback);
}
export async function parseUploadFile(file, source, fallback) {
  if (file.size > 5000000) throw Error('파일당 5MB 이하로 업로드해주세요.');
  if (/\.csv$/i.test(file.name)) {
    const bytes = await file.arrayBuffer();
    let text = new TextDecoder('utf-8').decode(bytes);
    if (text.includes('�')) text = new TextDecoder('euc-kr').decode(bytes);
    return parseUploadCSV(text, source, fallback);
  }
  if (!/\.xlsx$/i.test(file.name))
    throw Error('현재 CSV·XLSX 파일만 지원합니다. 암호·보호된 파일은 처리할 수 없습니다.');
  const XLSX = await import('xlsx');
  const book = XLSX.read(await file.arrayBuffer(), { type: 'array', cellDates: true });
  if (book.SheetNames.length !== 1)
    throw Error(
      '거래가 들어 있는 시트 하나만 남긴 XLSX 파일을 업로드해주세요. 여러 시트 자동 선택은 지원하지 않습니다.',
    );
  return parseUploadTable(
    XLSX.utils.sheet_to_json(book.Sheets[book.SheetNames[0]], { header: 1, defval: '' }),
    source,
    fallback,
  );
}
export const isCounted = (r) =>
  !['pending', 'excluded'].includes(r.duplicateState || '') &&
  ['신용카드', '체크카드', '현금영수증'].includes(r.paymentMethod || '');
export const transactionKey = (r) =>
  [r.date, r.merchant.replace(/\s/g, '').toLowerCase(), r.amount, r.paymentMethod].join('|');
export function flagDuplicates(existing, incoming) {
  const seen = new Map(
    existing.filter(isCounted).map((r) => [transactionKey(r), `${r.uploadId || 'legacy'}:${r.id}`]),
  );
  return incoming.map((r) => {
    const key = transactionKey(r),
      duplicateOf = seen.get(key);
    if (duplicateOf) return { ...r, duplicateState: 'pending', duplicateOf };
    if (r.paymentMethod !== '확인 필요') seen.set(key, `${r.uploadId}:${r.id}`);
    return r;
  });
}
export function uploadFiles(meta, rows) {
  if (meta?.files) return meta.files;
  if (!rows.length) return [];
  return [
    {
      id: 'legacy',
      name: meta?.name || '이전 업로드',
      count: rows.length,
      at: meta?.at || new Date().toISOString(),
      source: 'card',
      status: rows.some((r) => !isCounted(r)) ? '확인 필요' : '업로드 완료',
    },
  ];
}
export function makeMeta(files) {
  return files.length
    ? {
        name: files.map((f) => f.name).join(', '),
        count: files.reduce((s, f) => s + f.count, 0),
        at: files[files.length - 1].at,
        files,
      }
    : null;
}
export function removeUpload(rows, files, id) {
  return {
    rows: rows.filter((r) => (r.uploadId || 'legacy') !== id),
    meta: makeMeta(files.filter((f) => f.id !== id)),
  };
}
export function uploadTotals(rows, taxYear = getDefaultTaxYear()) {
  return rows.reduce(
    (sum, r) => {
      if (
        !isCounted(r) ||
        Number(r.date.slice(0, 4)) !== taxYear ||
        ['공제 제외', '공제 대상 아님'].includes(r.category)
      )
        return sum;
      if (r.paymentMethod === '체크카드') sum.debit += r.amount;
      else if (r.paymentMethod === '현금영수증') sum.cash += r.amount;
      else if (r.paymentMethod === '신용카드') sum.credit += r.amount;
      return sum;
    },
    { credit: 0, debit: 0, cash: 0 },
  );
}
export function transactionExamples(rows, category, limit = 15) {
  const all = rows
    .filter(
      (r) =>
        r.source === 'upload' &&
        (!category ||
          (r.category === '공제 제외' ? '공제 대상 아님' : r.category) ===
            (category === '공제 제외' ? '공제 대상 아님' : category)),
    )
    .sort((a, b) => b.date.localeCompare(a.date));
  return {
    count: all.length,
    total: all.reduce((s, r) => s + r.amount, 0),
    countedTotal: all.filter(isCounted).reduce((s, r) => s + r.amount, 0),
    examples: all.slice(0, limit),
  };
}
export function uploadBlocker(rows) {
  return rows.some((r) => r.paymentMethod === '확인 필요' || !r.paymentMethod)
    ? '결제수단을 알 수 없는 파일이 있습니다. 파일 목록에서 신용카드·체크카드를 선택하거나 해당 파일을 삭제해주세요.'
    : '';
}
