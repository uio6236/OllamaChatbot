// CSV·XLSX를 읽고 업로드 단위로 거래를 묶습니다. 중복 후보는 사용자 확인 전 집계에서 보류합니다.
import React, { useState, useId } from 'react';
import {
  parseUploadFile,
  payCode,
  transactionExamples,
  uploadFiles,
  makeMeta,
  flagDuplicates,
  isCounted,
  removeUpload,
} from '@/api/expense-service.js';
import { recordAccess } from '@/api/prototype-records.js';
export function ExpenseUpload({ rows, meta, onChange }) {
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [source, setSource] = useState('card'),
    [fallback, setFallback] = useState('');
  const files = uploadFiles(meta, rows);
  const changeMethod = (id, value) => {
    const others = rows.filter((r) => (r.uploadId || 'legacy') !== id);
    const selected = rows
      .filter((r) => (r.uploadId || 'legacy') === id)
      .map((r) => ({
        ...r,
        paymentMethod:
          r.paymentMethod === '확인 필요' || !r.paymentMethod ? value : r.paymentMethod,
        PAY_METHOD: payCode(
          r.paymentMethod === '확인 필요' || !r.paymentMethod ? value : r.paymentMethod,
        ),
      }));
    onChange(
      [...others, ...flagDuplicates(others, selected)],
      makeMeta(files.map((f) => (f.id === id ? { ...f, paymentMethod: value } : f))),
    );
  };
  const resolve = (id, include) => {
    if (
      include &&
      !window.confirm(
        '중복 가능 거래를 별개의 정상 거래로 확인하고 집계에 포함하시겠습니까? 같은 거래를 두 번 포함하지 않도록 확인해주세요.',
      )
    )
      return;
    onChange(
      rows.map((r) =>
        (r.uploadId || 'legacy') === id && r.duplicateState === 'pending'
          ? { ...r, duplicateState: include ? 'included' : 'excluded' }
          : r,
      ),
      meta,
    );
  };
  return (
    <div className="inline-note upload-inline">
      <h3>카드·현금영수증 거래내역 업로드</h3>
      <p>
        현재 지원: CSV(UTF-8·한글 인코딩), 단일 시트 XLSX · 첫 행에 거래일자/승인일시/사용일자,
        가맹점명/상호명, 이용금액/금액 등의 열이 있어야 합니다. 사용구분/결제수단은 선택 열입니다.
        카드사별 모든 원본 양식·다중 시트·암호 파일 자동 인식은 지원하지 않습니다.
      </p>
      <p>
        파일 처리 → 예시 공공데이터 상호명 대조 → 데모 계산 → 결과 조회. 실제 MERCHANT_LIST
        80,665행과 공공데이터 API는 미연동이며 예시 목록만 대조합니다. 머신러닝은 사용하지 않습니다.
      </p>
      <div className="form-grid">
        <label className="field">
          <span>업로드 파일 출처</span>
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="card">카드사 이용내역</option>
            <option value="hometax">홈택스 현금영수증 사용내역</option>
          </select>
        </label>
        {source === 'card' ? (
          <label className="field">
            <span>파일에 결제수단이 없는 경우</span>
            <select value={fallback} onChange={(e) => setFallback(e.target.value)}>
              <option value="">선택해주세요</option>
              <option>신용카드</option>
              <option>체크카드</option>
            </select>
            <small>파일에 유효한 결제수단이 있으면 해당 값을 우선합니다.</small>
          </label>
        ) : (
          <p>홈택스 출처의 모든 거래는 현금영수증으로 처리합니다.</p>
        )}
      </div>
      <div className="actions">
        <label className="btn">
          {busy ? '파일 처리 중…' : 'CSV·XLSX 파일 추가 (여러 개 가능)'}
          <input
            aria-label="거래내역 CSV·XLSX 파일 추가"
            type="file"
            multiple
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            disabled={busy}
            onChange={async (e) => {
              const input = e.target,
                selected = Array.from(input.files || []);
              if (!selected.length) return;
              setError('');
              setBusy(true);
              let nextRows = [...rows],
                nextFiles = [...files];
              const messages = [];
              for (const file of selected) {
                const id = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                    .map((n) => n.toString(16).padStart(2, '0'))
                    .join(''),
                  at = new Date().toISOString();
                try {
                  const incoming = (await parseUploadFile(file, source, fallback)).map((r) => ({
                    ...r,
                    uploadId: id,
                    uploadName: file.name,
                  }));
                  if (nextRows.length + incoming.length > 10000)
                    throw Error('전체 등록 거래는 10,000건 이하로 유지해주세요.');
                  const flagged = flagDuplicates(nextRows, incoming),
                    duplicates = flagged.filter((r) => r.duplicateState === 'pending').length;
                  nextRows.push(...flagged);
                  nextFiles.push({
                    id,
                    name: file.name,
                    count: flagged.length,
                    at,
                    source,
                    paymentMethod: source === 'hometax' ? '현금영수증' : fallback,
                    status: flagged.some((r) => !isCounted(r)) ? '확인 필요' : '업로드 완료',
                  });
                  if (duplicates)
                    messages.push(
                      `${file.name}: 기존에 등록된 내역과 중복될 가능성이 있는 거래가 ${duplicates}건 발견되었습니다. (같은 파일 내 중복 포함)`,
                    );
                } catch (err) {
                  nextFiles.push({
                    id,
                    name: file.name,
                    count: 0,
                    at,
                    source,
                    status: '처리 실패',
                    error: err.message,
                  });
                  messages.push(
                    `${file.name}: ${err.message} 지원하는 헤더가 첫 행에 있는지 확인해주세요. 지원하지 않는 양식은 카드사·홈택스에서 다른 형식으로 내보내거나 해당 열 이름·날짜·금액을 확인한 뒤 다시 업로드해주세요.`,
                  );
                }
              }
              onChange(nextRows, makeMeta(nextFiles));
              recordAccess('UPLOAD');
              setError(messages.join('\n'));
              input.value = '';
              setBusy(false);
            }}
          />
        </label>
      </div>
      <h4>업로드 파일 관리 · {files.length}개</h4>
      {!files.length && <p>등록된 파일이 없습니다. 새 파일을 추가해도 기존 파일은 유지됩니다.</p>}
      <div className="upload-files">
        {files.map((file) => {
          const fileRows = rows.filter((r) => (r.uploadId || 'legacy') === file.id),
            unknown = fileRows.some((r) => r.paymentMethod === '확인 필요' || !r.paymentMethod),
            pending = fileRows.filter((r) => r.duplicateState === 'pending').length,
            excluded = fileRows.filter((r) => r.duplicateState === 'excluded').length;
          const status =
            file.status === '처리 실패'
              ? '처리 실패'
              : unknown || pending
                ? '확인 필요'
                : '업로드 완료';
          return (
            <article className="upload-file" key={file.id}>
              <div className="card-heading">
                <b>{file.name}</b>
                <span className={'tag ' + (status === '업로드 완료' ? 'green' : 'amber')}>
                  {status}
                </span>
              </div>
              <p>
                {file.source === 'hometax' ? '홈택스 현금영수증 사용내역' : '카드사 이용내역'} ·{' '}
                {Array.from(new Set(fileRows.map((r) => r.paymentMethod || '확인 필요'))).join(
                  ' / ',
                ) || '거래 없음'}{' '}
                · {fileRows.length}건
              </p>
              {file.error && (
                <p className="error">
                  {file.error} · 안내된 헤더와 오류 행을 확인한 뒤 다시 추가해주세요.
                </p>
              )}
              {unknown && (
                <label className="field">
                  <span>누락된 결제수단 선택 · 선택 전 집계 제외</span>
                  <select
                    aria-label={`${file.name} 결제수단`}
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) changeMethod(file.id, e.target.value);
                    }}
                  >
                    <option value="">결제수단 선택 필요</option>
                    <option>신용카드</option>
                    <option>체크카드</option>
                  </select>
                </label>
              )}
              {pending > 0 && (
                <div className="duplicate-note">
                  <p role="status">
                    기존에 등록된 내역과 중복될 가능성이 있는 거래가 {pending}건 발견되었습니다.
                    확인 전 집계에서 제외합니다.
                  </p>
                  <details>
                    <summary>중복 가능 거래 확인 ({pending}건)</summary>
                    <ul>
                      {fileRows
                        .filter((r) => r.duplicateState === 'pending')
                        .map((r) => (
                          <li key={r.id}>
                            {r.date} · {r.merchant} · {r.amount.toLocaleString()}원 ·{' '}
                            {r.paymentMethod}
                          </li>
                        ))}
                    </ul>
                  </details>
                  <div className="actions">
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={() => resolve(file.id, false)}
                    >
                      중복으로 확인 · 집계 제외
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={() => resolve(file.id, true)}
                    >
                      별개 거래로 확인 · 집계 포함
                    </button>
                  </div>
                </div>
              )}
              {excluded > 0 && (
                <p>사용자 확인으로 중복 {excluded}건 집계 제외 · 원본 거래는 조회에 유지됩니다.</p>
              )}
              <button
                type="button"
                className="text-btn danger"
                onClick={() => {
                  if (
                    !window.confirm(
                      `${file.name}에서 등록한 거래 ${fileRows.length}건을 모두 삭제하시겠습니까? 다른 파일의 거래는 유지됩니다.`,
                    )
                  )
                    return;
                  const next = removeUpload(rows, files, file.id);
                  onChange(next.rows, next.meta);
                  recordAccess('UPLOAD_DELETE');
                }}
              >
                파일 삭제
              </button>
            </article>
          );
        })}
      </div>
      {error && (
        <p className="error" role="status" style={{ whiteSpace: 'pre-line' }}>
          {error}
        </p>
      )}
      <p>
        중복 기준: 거래일·공백 제외 상호명·금액·결제수단 일치. 중복 가능 거래는 보존하며 확인 전
        집계 제외, 별개 거래로 확인한 경우에만 포함합니다. 카드사와 현금영수증의 결제수단이 다른
        거래는 자동 중복 판정을 하지 않습니다. 결제수단 누락은 임의로 신용카드에 포함하지 않습니다.
      </p>
      <TransactionExamples rows={rows} />
    </div>
  );
}
export function TransactionExamples({ rows }) {
  const [open, setOpen] = useState(false),
    [category, setCategory] = useState('일반'),
    [file, setFile] = useState(''),
    [limit, setLimit] = useState(15);
  const id = useId();
  const categories = ['일반', '대중교통', '전통시장', '문화체육', '공제 대상 아님'];
  const fileIds = Array.from(new Set(rows.map((r) => r.uploadId || 'legacy')));
  const matches = transactionExamples(
    file ? rows.filter((r) => (r.uploadId || 'legacy') === file) : rows,
    category,
    limit,
  );
  return (
    <div className="transaction-examples">
      <button
        type="button"
        className="dash-jump"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        결제수단 거래 분류 확인하기 {open ? '⌃' : '⌄'}
      </button>
      {open && (
        <div id={id}>
          <label className="field">
            <span>업로드별 조회</span>
            <select
              value={file}
              onChange={(e) => {
                setFile(e.target.value);
                setLimit(15);
              }}
            >
              <option value="">전체 업로드 파일</option>
              {fileIds.map((id) => (
                <option key={id} value={id}>
                  {rows.find((r) => (r.uploadId || 'legacy') === id)?.uploadName || id}
                </option>
              ))}
            </select>
          </label>
          <div className="type-buttons">
            <button
              type="button"
              className={!category ? 'selected' : ''}
              onClick={() => {
                setCategory('');
                setLimit(15);
              }}
            >
              전체 유형
            </button>
            {categories.map((c) => (
              <button
                type="button"
                className={c === category ? 'selected' : ''}
                aria-pressed={c === category}
                onClick={() => {
                  setCategory(c);
                  setLimit(15);
                }}
                key={c}
              >
                {c}
              </button>
            ))}
          </div>
          <p>
            {category || '전체 유형'} 전체 {matches.count}건 · 전체 거래 합계{' '}
            {matches.total.toLocaleString()}원 · 집계 포함 합계{' '}
            {matches.countedTotal.toLocaleString()}원. 처음 15건을 표시하며 더보기로 나머지 거래를
            조회할 수 있습니다.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>거래일</th>
                  <th>거래처명</th>
                  <th>거래금액</th>
                  <th>결제수단</th>
                  <th>소비 유형</th>
                  <th>분류 근거 / 집계 상태</th>
                </tr>
              </thead>
              <tbody>
                {matches.examples.map((r) => (
                  <tr key={`${r.uploadId}:${r.id}`}>
                    <td>{r.date}</td>
                    <td>{r.merchant}</td>
                    <td>{r.amount.toLocaleString('ko-KR')}원</td>
                    <td>{r.paymentMethod || '확인 필요'}</td>
                    <td>{r.category === '공제 제외' ? '공제 대상 아님' : r.category}</td>
                    <td>
                      {r.classificationBasis || r.method}
                      <small className="block-note">
                        {r.duplicateState === 'pending'
                          ? '중복 확인 전 · 집계 제외'
                          : r.duplicateState === 'excluded'
                            ? '중복 확인 · 집계 제외'
                            : isCounted(r)
                              ? '집계 포함'
                              : '결제수단 확인 전 · 집계 제외'}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {matches.examples.length < matches.count && (
            <button type="button" className="btn secondary" onClick={() => setLimit(limit + 15)}>
              더보기 ({matches.examples.length} / {matches.count}건)
            </button>
          )}
          {!matches.count && <p className="empty">해당 거래내역이 없습니다</p>}
          <p>
            소비 유형 자동 분류는 추정 결과이며 실제 세법상 공제 적격성을 보증하지 않습니다. 현재
            예시 공공데이터 목록을 사용하며 일치하는 상호명이 없으면 일반으로 분류합니다. 조회
            전용이며 소비 유형을 직접 수정할 수 없습니다. 소득공제액은 지출 합계와 다릅니다.
          </p>
        </div>
      )}
    </div>
  );
}
