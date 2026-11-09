import { getDefaultTaxYear } from '@/utils/tax-year.js';
// 기존 관리자 도구 모음입니다. 화면 검사는 체험용이며 운영 권한은 서버에서 검사해야 합니다.
import { newPrototypeId } from '@/api/account-service.js';
import React, { useState } from 'react';
import {
  accessRecords,
  criteriaRecords,
  saveCriterion,
  predictionRecords,
  inquiryService,
  inquiryLabels,
} from '@/api/prototype-records.js';
const blank = {
  id: '',
  TAX_YEAR: getDefaultTaxYear(),
  TYPE_CODE: '',
  SALARY_MIN: 0,
  SALARY_MAX: null,
  RATE: 0,
  LIMIT_AMOUNT: 0,
  SOURCE_NOTE: '',
  UPDATED_AT: '',
  UPDATED_BY: '',
};
export function CriteriaManagement() {
  const [rows, setRows] = useState(() => criteriaRecords()),
    [d, setD] = useState(blank),
    [year, setYear] = useState(String(getDefaultTaxYear())),
    [err, setErr] = useState('');
  return (
    <>
      <h3>연도·총급여 구간별 공제 기준값</h3>
      <p className="notice amber">
        브라우저 관리 시연 · 입력한 기준값은 실제 계산 엔진과 미연동입니다. 검증된 운영 세법 기준이
        아닙니다.
      </p>
      <label className="field">
        조회 연도
        <input type="number" value={year} onChange={(e) => setYear(e.target.value)} />
      </label>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {['연도', '항목', '총급여 구간(원)', '비율·한도', '최종 수정', '작업'].map((s) => (
                <th key={s}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((r) => String(r.TAX_YEAR) === year)
              .map((r) => (
                <tr key={r.id}>
                  <td>{r.TAX_YEAR}</td>
                  <td>{r.TYPE_CODE}</td>
                  <td>
                    {r.SALARY_MIN.toLocaleString()} 초과 ~{' '}
                    {r.SALARY_MAX?.toLocaleString() || '상한 없음'} 이하
                  </td>
                  <td>
                    {r.RATE}% / {r.LIMIT_AMOUNT.toLocaleString()}원
                  </td>
                  <td>
                    {r.UPDATED_AT} · {r.UPDATED_BY}
                  </td>
                  <td>
                    <button type="button" className="text-btn" onClick={() => setD(r)}>
                      수정
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {!rows.length && <p>등록된 기준값이 없습니다. 임의의 공식 기준값은 생성하지 않습니다.</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          try {
            saveCriterion({ ...d, id: d.id || newPrototypeId() });
            setRows(criteriaRecords());
            setD(blank);
            setErr('브라우저에 저장했습니다. 계산 엔진에는 반영되지 않습니다.');
          } catch (e) {
            setErr(e.message);
          }
        }}
      >
        <h4>{d.id ? '기준값 수정' : '기준값 행 추가'}</h4>
        <div className="form-grid">
          {[
            'TAX_YEAR',
            'TYPE_CODE',
            'SALARY_MIN',
            'SALARY_MAX',
            'RATE',
            'LIMIT_AMOUNT',
            'SOURCE_NOTE',
          ].map((k) => (
            <label className="field" key={k}>
              <span>
                {
                  {
                    TAX_YEAR: '귀속연도',
                    TYPE_CODE: '항목 코드',
                    SALARY_MIN: '총급여 시작 (초과)',
                    SALARY_MAX: '총급여 끝 (이하 · 빈칸은 상한 없음)',
                    RATE: '비율 (%)',
                    LIMIT_AMOUNT: '한도 (원)',
                    SOURCE_NOTE: '근거 · 조문/신고안내 쪽수',
                  }[k]
                }
              </span>
              <input
                type={['TYPE_CODE', 'SOURCE_NOTE'].includes(k) ? 'text' : 'number'}
                required={k !== 'SALARY_MAX'}
                min="0"
                value={d[k] ?? ''}
                onChange={(e) =>
                  setD({
                    ...d,
                    [k]: ['TYPE_CODE', 'SOURCE_NOTE'].includes(k)
                      ? e.target.value
                      : k === 'SALARY_MAX' && e.target.value === ''
                        ? null
                        : Number(e.target.value),
                  })
                }
              />
            </label>
          ))}
        </div>
        <button className="btn">저장 (시연)</button>
        <button type="button" className="btn secondary" onClick={() => setD(blank)}>
          새 행 입력
        </button>
        <p role="status">{err}</p>
      </form>
    </>
  );
}
export function AccessLog() {
  const [rows] = useState(() => accessRecords());
  return (
    <>
      <h3>주요 동작 접근 기록 · 브라우저 시연</h3>
      <p>
        서버 접속 IP는 수집되지 않아 미연동으로 표시합니다. 운영 ACCESS_LOG와 무결성·보존 정책은
        서버 구현이 필요합니다. 최근 500건을 보관합니다.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {['계정', '동작', '시각', 'IP', '결과'].map((v) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.LOGIN_ID}</td>
                <td>{r.SCREEN}</td>
                <td>{r.ACCESSED_AT}</td>
                <td>미연동</td>
                <td>{r.RESULT}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
export function Predictions() {
  const [rows] = useState(() => predictionRecords()),
    [search, setSearch] = useState('');
  return (
    <>
      <h3>예측 결과 조회 · 브라우저 시연</h3>
      <input
        aria-label="예측 결과 검색"
        placeholder="계정 ID 또는 시나리오명"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {['계정 ID', '종류', '계산일 / 시나리오', '결정세액', '환급 차액'].map((v) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((r) => (r.memberId + (r.scenarioName || '')).includes(search))
              .map((r, i) => (
                <tr key={i}>
                  <td>{r.memberId}</td>
                  <td>{r.kind}</td>
                  <td>
                    {r.date} {r.scenarioName}
                  </td>
                  <td>{r.decidedTax?.toLocaleString()}원</td>
                  <td>{r.expectedRefund?.toLocaleString()}원</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      <p>
        현재 브라우저에 보관된 체험 결과만 조회합니다. 실제 전체 회원 결과 DB 조회는 미연동입니다.
      </p>
    </>
  );
}
export function InquiryManagement() {
  const [rows, setRows] = useState(() => inquiryService.list()),
    [type, setType] = useState(''),
    [status, setStatus] = useState(''),
    [err, setErr] = useState('');
  function run(fn) {
    try {
      fn();
      setRows(inquiryService.list());
      setErr('상태를 브라우저에 반영했습니다.');
    } catch (e) {
      setErr(e.message);
    }
  }
  return (
    <>
      <h3>문의 및 답변 관리</h3>
      <div className="form-grid">
        <select aria-label="문의 유형 필터" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">모든 유형</option>
          {['ERROR', 'QUESTION', 'ETC'].map((v) => (
            <option key={v} value={v}>
              {inquiryLabels[v]}
            </option>
          ))}
        </select>
        <select
          aria-label="문의 상태 필터"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">모든 상태</option>
          {['WAITING', 'CHECKING', 'ANSWERED'].map((v) => (
            <option key={v} value={v}>
              {inquiryLabels[v]}
            </option>
          ))}
        </select>
      </div>
      {rows
        .filter((q) => (!type || q.category === type) && (!status || q.status === status))
        .map((q) => (
          <form
            className="admin-inquiry"
            key={q.id}
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(() => inquiryService.answer(q.id, String(f.get('answer') || '')));
            }}
          >
            <span className={'tag ' + (q.status === 'ANSWERED' ? 'green' : 'amber')}>
              {inquiryLabels[q.status]}
            </span>
            <span className="tag gray">{inquiryLabels[q.category]}</span>
            <h3>{q.title}</h3>
            <p>{q.text}</p>
            {q.status === 'CHECKING' && <p>확인 후 답변 드리겠습니다.</p>}
            {q.status !== 'ANSWERED' && (
              <button
                type="button"
                className="btn secondary"
                onClick={() => run(() => inquiryService.checking(q.id))}
              >
                확인 중
              </button>
            )}
            <label className="field">
              최종 답변
              <textarea name="answer" defaultValue={q.answer} required rows={3} />
            </label>
            {q.answeredAt && <p>답변 시각 {new Date(q.answeredAt).toLocaleString('ko-KR')}</p>}
            <button className="btn">최종 답변 저장</button>
          </form>
        ))}
      {!rows.length && <p className="empty">접수된 문의가 없습니다.</p>}
      <p role="status">{err}</p>
    </>
  );
}
