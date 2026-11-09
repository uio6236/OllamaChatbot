// 일반 입력과 시뮬레이션이 함께 사용하는 6단계 폼입니다. 입력은 임시 상태에 두고 완료 시 상위로 전달합니다.
import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  ChevronLeft,
  Check,
  Info,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from 'lucide-react';
import { normalizeTaxData, validateTaxData } from '@/api/services.js';
import { uploadTotals, uploadBlocker } from '@/api/expense-service.js';
import { ExpenseUpload } from '@/components/expense/ExpenseUpload.jsx';
const steps = ['기본 정보', '소득 정보', '지출 정보', '부양가족', '주거 정보', '공제·감면'];
function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export default function TaxInfoForm({
  mode,
  data,
  transactions,
  upload,
  onSubmit,
  onCancel,
  onTaxYearChange,
}) {
  // 편집 중인 값은 임시 상태입니다. 완료할 때만 App의 저장/계산 처리에 전달합니다.
  const [d, setD] = useState(() => normalizeTaxData(data)),
    [step, setStep] = useState(0),
    [err, setErr] = useState('');
  const [tx, setTx] = useState(() => structuredClone(transactions)),
    [uploadMeta, setUploadMeta] = useState(() => structuredClone(upload));
  // 파일 추가·삭제 또는 귀속 연도 변경 시 업로드 거래에서만 실제 지출 합계를 갱신합니다.
  useEffect(() => {
    setD((current) => ({ ...current, ...uploadTotals(tx, current.taxYear) }));
  }, [tx, d.taxYear]);
  const familyError =
    (d.children ?? 0) > d.family
      ? '20세 이하 자녀 수는 추가 부양가족 수(본인 제외)보다 많을 수 없습니다.'
      : '';
  const move = (next) => {
    if (next > step) {
      const error =
        validateTaxData(d) || (step >= 2 && mode !== 'simulation' ? uploadBlocker(tx) : '');
      if (error) {
        setErr(error);
        return;
      }
      if (step === 1 && (!Number.isFinite(d.salary) || !Number.isFinite(d.paid))) {
        setErr('총급여·기납부 소득세는 필수입니다.');
        return;
      }
    }
    setErr('');
    setStep(next);
  };
  const f = (key, label, type = 'number', hint = '', unit = '원') => (
    <Field label={label} hint={hint}>
      <input
        required
        type={type}
        min={type === 'number' ? 0 : undefined}
        step={type === 'number' ? 1 : undefined}
        readOnly={
          ['name', 'birth', 'email'].includes(String(key)) ||
          (mode === 'simulation' && key === 'employed')
        }
        value={typeof d[key] === 'number' && !Number.isFinite(d[key]) ? '' : String(d[key] ?? '')}
        onChange={(e) =>
          setD({
            ...d,
            ...(key === 'rent' ? { legacyRentNeedsReview: false } : {}),
            ...(['nationalPension', 'healthEmploymentInsurance'].includes(key)
              ? { legacyInsuranceNeedsReview: false }
              : {}),
            [key]:
              type === 'number'
                ? e.target.value === ''
                  ? NaN
                  : Number(e.target.value)
                : e.target.value,
          })
        }
      />
      {type === 'number' && <span className="input-unit">{unit}</span>}
    </Field>
  );
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">MY TAX INFORMATION</div>
          <h1>{mode === 'simulation' ? '조건 변경 시뮬레이션' : '연말정산 정보 입력'}</h1>
          <p>나의 정보를 하나씩 채우고, 환급의 가능성을 확인해보세요.</p>
        </div>
        <span className="tag blue">{step + 1} / 6 단계</span>
      </div>
      {mode === 'simulation' && (
        <div className="notice amber">
          <SlidersHorizontal size={18} />
          시뮬레이션 모드 · 변경한 값은 실제 저장정보에 반영되지 않습니다.
        </div>
      )}
      <div className="stepper">
        {steps.map((s, i) => (
          <button
            type="button"
            key={s}
            onClick={() => move(i)}
            className={i === step ? 'current' : i < step ? 'done' : ''}
          >
            <span>{i < step ? <Check size={16} /> : i + 1}</span>
            {s}
          </button>
        ))}
      </div>
      <form
        className="card form-card"
        onSubmit={(e) => {
          e.preventDefault();
          const error =
            validateTaxData(d) || (step >= 2 && mode !== 'simulation' ? uploadBlocker(tx) : '');
          if (error) {
            setErr(error);
            return;
          }
          setErr('');
          if (step < 5) move(step + 1);
          else if (!d.consent) setErr('시연용 예시 결과 확인에 동의해주세요.');
          else {
            try {
              onSubmit(d, tx, uploadMeta);
            } catch (error) {
              setErr(error.message || '계산 요청을 확인해주세요.');
            }
          }
        }}
      >
        <div className="section-number">STEP 0{step + 1}</div>
        <h2>{steps[step]}를 확인해주세요</h2>
        <p className="muted">
          {mode === 'simulation'
            ? '저장된 정보가 자동으로 입력되어 있어요. 원하는 항목만 바꿔보세요.'
            : '입력한 정보는 이 브라우저에서 시연용으로 보관됩니다.'}
        </p>
        <div className="form-grid">
          {step === 0 && (
            <>
              <p className="full muted">
                실명은 수집하지 않습니다. 아이디·생년월일·이메일은 조회 전용입니다. 가입 성별 변경은
                마이페이지에서 진행해주세요.
              </p>
              <Field
                label="귀속 연도"
                hint="기본 연도는 서비스 정책에 따라 1~3월 전년도, 4~12월 해당 연도로 선택합니다."
              >
                <input
                  type="number"
                  required
                  min="1900"
                  max="9999"
                  value={d.taxYear}
                  onChange={(e) => {
                    const year = Number(e.target.value);
                    setD({ ...d, taxYear: year });
                    onTaxYearChange?.(year);
                  }}
                />
              </Field>
              {f('birth', '생년월일', 'date')}
              <Field label="성별">
                <select
                  disabled
                  value={d.gender}
                  onChange={(e) => setD({ ...d, gender: e.target.value })}
                >
                  <option value="">선택해주세요</option>
                  <option>여성</option>
                  <option>남성</option>
                </select>
              </Field>
              {f('email', '이메일', 'email')}
            </>
          )}
          {step === 1 && (
            <>
              {f('salary', '연간 총급여', 'number', '비과세 소득을 제외한 연간 급여')}
              {f(
                'paid',
                '연간 기납부 소득세',
                'number',
                '지방소득세·4대 보험료가 아니라 급여에서 미리 납부한 소득세입니다.',
              )}
              {d.legacyInsuranceNeedsReview && (
                <p className="notice amber full">
                  기존 사회보험료 합계는 임의로 나누지 않았습니다. 두 항목을 확인해 다시
                  입력해주세요.
                </p>
              )}
              {f(
                'nationalPension',
                '국민연금 연간 납부액',
                'number',
                '급여명세서 등에 표시된 국민연금 본인 납부액입니다.',
              )}
              {f(
                'healthEmploymentInsurance',
                '건강보험료·고용보험료 연간 납부액',
                'number',
                '본인 납부액을 국민연금과 구분하여 입력합니다.',
              )}
            </>
          )}
          {step === 2 && (
            <>
              <div className="review full">
                <h3>{d.taxYear}년 업로드 거래 집계</h3>
                <div>
                  신용카드 <b>{d.credit.toLocaleString()}원</b>
                </div>
                <div>
                  체크카드 <b>{d.debit.toLocaleString()}원</b>
                </div>
                <div>
                  현금영수증 <b>{d.cash.toLocaleString()}원</b>
                </div>
                <p>
                  다른 연도 거래{' '}
                  {tx.filter((row) => Number(row.date.slice(0, 4)) !== d.taxYear).length}건은
                  보존하며 이번 계산에서만 제외합니다.
                </p>
              </div>
              <p className="full muted">
                {mode === 'simulation'
                  ? '실제 지출은 유지됩니다. 아래에 소비 유형·결제수단별 가상 추가 금액을 입력하세요.'
                  : '실제 사용금액은 CSV·XLSX 업로드로만 입력합니다. 선택 연도의 집계 포함 거래를 자동 합산합니다.'}
              </p>
              {mode === 'simulation' ? (
                <div className="inline-note full">
                  <h3>소비 유형·결제수단별 가상 추가 사용액</h3>
                  <p>
                    업로드 없이 원본 지출에 가상 금액을 추가합니다. 원본 거래는 변경되지 않습니다.
                    체험용 결과 비교이며 유형별 법정 공제율·한도는 미연동입니다.
                  </p>
                  {(d.simulationSpend || []).map((row, i) => (
                    <div className="form-grid" key={i}>
                      <select
                        aria-label={`가상 소비 유형 ${i + 1}`}
                        value={row.category}
                        onChange={(e) =>
                          setD({
                            ...d,
                            simulationSpend: d.simulationSpend.map((r, j) =>
                              j === i ? { ...r, category: e.target.value } : r,
                            ),
                          })
                        }
                      >
                        {[
                          ['GENERAL', '일반'],
                          ['TRANSIT', '대중교통'],
                          ['MARKET', '전통시장'],
                          ['CULTURE', '문화체육'],
                        ].map(([v, l]) => (
                          <option key={v} value={v}>
                            {l}
                          </option>
                        ))}
                      </select>
                      <select
                        aria-label={`가상 결제수단 ${i + 1}`}
                        value={row.payment}
                        onChange={(e) =>
                          setD({
                            ...d,
                            simulationSpend: d.simulationSpend.map((r, j) =>
                              j === i ? { ...r, payment: e.target.value } : r,
                            ),
                          })
                        }
                      >
                        {[
                          ['CREDIT', '신용카드'],
                          ['CHECK', '체크카드'],
                          ['CASH', '현금영수증'],
                        ].map(([v, l]) => (
                          <option key={v} value={v}>
                            {l}
                          </option>
                        ))}
                      </select>
                      <input
                        aria-label={`가상 추가 금액 ${i + 1}`}
                        type="number"
                        min="0"
                        required
                        value={row.amount}
                        onChange={(e) =>
                          setD({
                            ...d,
                            simulationSpend: d.simulationSpend.map((r, j) =>
                              j === i ? { ...r, amount: Number(e.target.value) } : r,
                            ),
                          })
                        }
                      />
                      <button
                        type="button"
                        className="text-btn"
                        onClick={() =>
                          setD({
                            ...d,
                            simulationSpend: d.simulationSpend.filter((_, j) => j !== i),
                          })
                        }
                      >
                        가상 항목 삭제
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() =>
                      setD({
                        ...d,
                        simulationSpend: [
                          ...(d.simulationSpend || []),
                          { category: 'GENERAL', payment: 'CREDIT', amount: 0 },
                        ],
                      })
                    }
                  >
                    가상 소비 추가
                  </button>
                </div>
              ) : (
                <ExpenseUpload
                  rows={tx}
                  meta={uploadMeta}
                  onChange={(rows, meta) => {
                    setErr('');
                    setTx(rows);
                    setUploadMeta(meta);
                    setD((current) => ({ ...current, ...uploadTotals(rows, current.taxYear) }));
                  }}
                />
              )}
            </>
          )}
          {step === 3 && (
            <>
              <Field label="추가 부양가족 수 (본인 제외)" hint="소득·연령·중복 공제 요건 별도 확인">
                <input
                  required
                  type="number"
                  min="0"
                  max="20"
                  step="1"
                  value={d.family}
                  onChange={(e) => setD({ ...d, family: Number(e.target.value) })}
                />
              </Field>
              <Field label="20세 이하 자녀 수" hint="추가 부양가족 중 해당 자녀 수를 입력해주세요.">
                <input
                  required
                  type="number"
                  min="0"
                  max="20"
                  step="1"
                  value={d.children ?? 0}
                  onChange={(e) => setD({ ...d, children: Number(e.target.value) })}
                />
              </Field>
              {familyError && (
                <p className="error full" role="alert">
                  {familyError}
                </p>
              )}
              <div className="inline-note">
                <Users />
                <b>기본공제 요건을 확인해주세요</b>
                <p>
                  실제 공제 가능 여부는 가족별 연령·소득·중복 공제를 확인해야 합니다. 자녀별 법정
                  공제 계산은 미연동입니다.
                </p>
              </div>
            </>
          )}
          {step === 4 && (
            <>
              <Field label="주택 보유 상태">
                <select value={d.housing} onChange={(e) => setD({ ...d, housing: e.target.value })}>
                  <option>무주택</option>
                  <option>주택 보유</option>
                  <option>확인 필요</option>
                </select>
              </Field>
              <Field label="무주택 세대주 여부">
                <select
                  required
                  value={d.headOfHousehold}
                  onChange={(e) => setD({ ...d, headOfHousehold: e.target.value })}
                >
                  <option value="확인 필요">확인 필요</option>
                  <option>예</option>
                  <option>아니요</option>
                </select>
                <small>무주택이면서 세대주인 경우 예를 선택해주세요.</small>
              </Field>
              {f(
                'rent',
                '월세 월 납부액 (원)',
                'number',
                '한 달에 납부하는 월세입니다. 데모 계산은 월 납부액 × 12개월로 환산합니다. 실제 납부 기간·계약·증빙 검증은 미연동입니다.',
              )}
              {d.legacyRentNeedsReview && (
                <p className="notice amber full">
                  과거 연간 월세 {d.legacyAnnualRent?.toLocaleString()}원은 보존했습니다. 월
                  납부액을 확인하여 다시 입력해주세요.
                </p>
              )}
              {f('housingSaving', '주택청약 연간 납입액')}
              <p>연간 환산 월세: {(d.rent * 12).toLocaleString()}원</p>
            </>
          )}
          {step === 5 && (
            <>
              <Field label="중소기업 취업자 감면 신청 여부">
                <select
                  value={{ 해당: '예', 미해당: '아니요' }[d.sme] || d.sme}
                  onChange={(e) => setD({ ...d, sme: e.target.value })}
                >
                  <option>확인 필요</option>
                  <option value="예">예</option>
                  <option value="아니요">아니요</option>
                </select>
              </Field>
              {f('pensionSaving', '연금저축 연간 납입액')}
              {f('irp', 'IRP 연간 납입액')}
              {f('employed', '입사일', 'date')}
              <Field label="군 복무 개월 수">
                <input
                  required
                  type="number"
                  min="0"
                  max="120"
                  step="1"
                  disabled={mode === 'simulation'}
                  value={d.militaryMonths ?? 0}
                  onChange={(e) => setD({ ...d, militaryMonths: Number(e.target.value) })}
                />
                <small>복무 이력이 없으면 0개월을 입력해주세요.</small>
              </Field>
              <Field label="회사 규모">
                <select
                  disabled={mode === 'simulation'}
                  required
                  value={d.companySize}
                  onChange={(e) => setD({ ...d, companySize: e.target.value })}
                >
                  <option value="확인 필요">확인 필요</option>
                  <option>중소기업</option>
                  <option>중견기업</option>
                  <option>대기업</option>
                </select>
              </Field>
              <div className="notice amber full">
                <Info size={16} />
                입사일·병역·기업 규모·무주택 세대주 정보는 자격 검토용으로 구분합니다.
                입사일·병역·기업 규모는 시나리오 저장 컬럼이 없어 시뮬레이션에서 변경할 수 없습니다.
                법정 자격 판정·계산은 아직 연결되지 않아 이 입력만으로 공제·감면을 확정하지
                않습니다.
              </div>
              <div className="review full">
                {mode === 'simulation' && (
                  <Field label="시나리오 이름">
                    <input
                      value={d.scenarioName || ''}
                      onChange={(e) => setD({ ...d, scenarioName: e.target.value })}
                      placeholder="예: 연금 추가 납입"
                    />
                  </Field>
                )}
                <p>
                  보험료·청약·연금은 체험용 결과에 반영됩니다. 실제 법정 계산·한도는 미연동입니다.
                </p>
                <h3>계산 전 마지막 확인</h3>
                <div>
                  총급여 <b>{d.salary.toLocaleString()}원</b>
                </div>
                <div>
                  기납부세액 <b>{d.paid.toLocaleString()}원</b>
                </div>
                <div>
                  카드·현금 사용 합계 <b>{(d.credit + d.debit + d.cash).toLocaleString()}원</b>
                </div>
                <div>
                  추가 가족 / 20세 이하 자녀{' '}
                  <b>
                    {d.family}명 / {d.children ?? 0}명
                  </b>
                </div>
                <label className="checkline">
                  <input
                    type="checkbox"
                    required
                    checked={d.consent}
                    onChange={(e) => setD({ ...d, consent: e.target.checked })}
                  />
                  실제 세법 계산이 아닌 시연용 예시 결과임을 확인했습니다.
                </label>
              </div>
            </>
          )}
        </div>
        {err && (
          <p className="error" role="alert">
            {err}
          </p>
        )}
        <div className="form-bottom">
          <button
            className="btn secondary"
            type="button"
            onClick={() => (step ? move(step - 1) : onCancel())}
          >
            <ChevronLeft size={16} />
            {step ? '이전 단계' : '취소'}
          </button>
          <span>입력 정보는 이 브라우저에서 보관됩니다</span>
          <button className="btn" type="submit">
            {step === 5
              ? mode === 'simulation'
                ? '변경 조건으로 계산하기'
                : '정보 저장하고 계산하기'
              : '다음 단계'}
            <ArrowRight size={16} />
          </button>
        </div>
      </form>
      <div className="privacy">
        <ShieldCheck size={16} />
        주민등록번호와 카드번호 전체는 수집하지 않습니다.
      </div>
    </>
  );
}
