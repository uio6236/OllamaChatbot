import DeductionDetails from '@/components/common/DeductionDetails.jsx';
// 예상 계산 결과·공제 내역·거래 분포를 보여주는 기존 대시보드입니다.
import React from 'react';
import { TransactionExamples } from '@/components/expense/ExpenseUpload.jsx';
import {
  ArrowRight,
  ChevronDown,
  Info,
  SlidersHorizontal,
  Wallet,
  ShieldCheck,
  ChartNoAxesCombined,
  Leaf,
} from 'lucide-react';
import { dashboardModel, TAX_GUIDANCE } from '@/utils/dashboard-model.js';
import { settlementLabel } from '@/api/services.js';
const money = (value) => value.toLocaleString('ko-KR');
const pending = '계산 연동 필요';
function Badge({ children, tone = 'blue' }) {
  return <span className={'tag ' + tone}>{children}</span>;
}
function Jump({ children, onClick }) {
  return (
    <button type="button" className="dash-jump" onClick={onClick}>
      {children}
      <ArrowRight size={14} />
    </button>
  );
}
export default function Dashboard({
  data,
  transactions,
  startSim,
  normalInput,
  go,
  chart,
  chat,
  result,
  isDemo = true,
}) {
  const m = dashboardModel(data, transactions, result),
    r = m.result;
  const resultLabel = settlementLabel(r.expectedRefund);
  // v10의 화면 그룹·펼침 구조를 유지하고 새 응답 필드는 이 표시 경계에서만 연결합니다.
  const insuranceTotal = (data.nationalPension ?? 0) + (data.healthEmploymentInsurance ?? 0);
  const cardDetails = r.details.filter((item) => ['CARD', 'CARD_RULE'].includes(item.kind));
  const groupAmount = (group) => {
    if (isDemo) return pending;
    const codes = {
      family: ['FAMILY'],
      rent: ['RENT'],
      social: ['NATIONAL_PENSION', 'HEALTH_EMPLOYMENT'],
      housingSaving: ['HOUSING_SAVING'],
      pension: ['PENSION_SAVING'],
      sme: ['SME'],
    };
    const items =
      group === 'cards'
        ? cardDetails
        : r.details.filter((item) => codes[group]?.includes(item.typeCode));
    if (group !== 'cards' && new Set(items.map((item) => item.kind)).size > 1)
      return '항목별 계산 상세 참조';
    return items.length
      ? `${money(items.reduce((sum, item) => sum + item.deductionAmount, 0))}원`
      : '제공된 계산 내역 없음';
  };
  const deductions = [
    {
      id: 'cards',
      type: '소득공제',
      name: '신용·체크카드·현금영수증',
      status: '확인 필요',
      reason:
        '업로드된 결제수단 정보는 조회할 수 있지만, 적격 증빙·최저사용기준·한도 계산은 미연동입니다. 실제 사용금액은 업로드된 거래내역을 집계합니다.',
    },
    {
      id: 'family',
      type: '소득공제',
      name: '추가 부양가족',
      status: data.family > 0 ? '확인 필요' : '미적용',
      reason:
        data.family > 0
          ? `${data.family}명 입력 · 가족별 소득·연령·중복공제 요건 및 증빙 확인 필요. 공제액은 미산출입니다.`
          : '추가 부양가족 0명 입력. 법정 인적공제 계산은 미연동입니다.',
    },
    {
      id: 'rent',
      type: '세액공제',
      name: '월세',
      status: data.rent <= 0 || data.housing === '주택 보유' ? '미적용' : '확인 필요',
      reason: `월세 월 납부액 ${money(data.rent)}원 입력 · 주택 상태 ${data.housing}. ${data.housing === '주택 보유' ? '무주택 요건 미충족으로 표시합니다.' : data.rent <= 0 ? '월세 입력 금액이 없습니다.' : '급여·세대·주택·계약·납부증빙 등 확인 필요.'} 법정 계산은 미연동이며 상단 데모 계산과 별개입니다.`,
    },
    {
      id: 'social',
      type: '소득공제',
      name: '사회보험료',
      status: insuranceTotal > 0 ? '확인 필요' : '미적용',
      reason: `국민연금 ${money(data.nationalPension ?? 0)}원 / 건강·고용보험료 ${money(data.healthEmploymentInsurance ?? 0)}원 (합계 ${money(insuranceTotal)}원). 법정 인정액·공제 산식은 미연동입니다.`,
    },
    {
      id: 'housingSaving',
      type: '소득공제',
      name: '주택청약',
      status: (data.housingSaving ?? 0) > 0 ? '확인 필요' : '미적용',
      reason: `연간 납입액 ${money(data.housingSaving ?? 0)}원. 무주택 세대주·급여·납입 증빙 및 한도 확인 필요.`,
    },
    {
      id: 'pension',
      type: '세액공제',
      name: '연금저축·IRP',
      status: (data.pensionSaving ?? 0) + (data.irp ?? 0) > 0 ? '확인 필요' : '미적용',
      reason: `연금저축 ${money(data.pensionSaving ?? 0)}원 / IRP ${money(data.irp ?? 0)}원 입력. 실제 세액공제율·한도는 미연동입니다.`,
    },
    {
      id: 'sme',
      type: '세액감면',
      name: '중소기업 취업 청년 감면',
      status: m.youth.status,
      reason: m.youth.reason,
    },
  ];
  const taxSteps = [
    ['총급여', `${money(r.totalSalary)}원`, `${r.taxYear}년 귀속 · 사용자 입력값`],
    ['근로소득공제', pending, '법정 산식 미연동'],
    ['근로소득금액', pending, '총급여에서 근로소득공제를 차감하는 단계'],
    ['그 밖의 소득공제', pending, '인적·연금·특별·카드 등 소득공제 세부 계산 필요'],
    [
      '과세표준',
      r.taxableIncome === null ? pending : `${money(r.taxableIncome)}원`,
      '소득공제와 종합한도 반영 후 산출',
    ],
    [
      '산출세액',
      `${money(r.calculatedTax)}원`,
      isDemo ? '체험용 계산 결과 · 법정 계산 미연동' : '계산 API 결과',
    ],
    ['세액감면·공제', pending, '개별 요건·한도·적용 순서 미연동'],
    ['결정세액', `${money(r.decidedTax)}원`, isDemo ? '체험용 계산 결과' : '계산 API 결과'],
    [
      settlementLabel(r.expectedRefund),
      `${money(Math.abs(r.expectedRefund))}원`,
      '기납부세액과 데모 결정세액의 차이',
    ],
  ];
  return (
    <div className="dashboard-v3">
      <div className="heading">
        <div>
          <div className="eyebrow">A LITTLE PREPARATION, A BRIGHTER TOMORROW</div>
          <h1>
            {data.name}님, 환급의 가능성을 확인해요 <span className="wave">✧</span>
          </h1>
          <p>결과부터 계산 근거까지, 나의 연말정산을 차근차근.</p>
        </div>
        <button className="btn" onClick={startSim}>
          <SlidersHorizontal size={16} />
          조건 변경 시뮬레이션
        </button>
      </div>
      <div className="notice">
        <Info size={16} />
        <span>
          <b>
            {r.taxYear}년 귀속 · {isDemo ? '체험용 계산' : '계산 결과'}
          </b>{' '}
          {isDemo && '실제 세법·증빙·자격 검증은 미연동입니다.'}
        </span>
        <Badge tone="gray">{isDemo ? 'DEMO' : '계산 결과'}</Badge>
      </div>
      <div className="dashboard-grid">
        <div className="dashboard-left">
          <section className="dash-results" aria-label="연말정산 핵심 지표">
            <div className="dash-metrics">
              <div className="dash-primary">
                <Badge>
                  {r.taxYear}년 귀속 · {isDemo ? '체험값' : '계산값'}
                </Badge>
                <p>{resultLabel}</p>
                <h2>
                  {money(Math.abs(r.expectedRefund))}
                  <span>원</span>
                </h2>
                <small>실제 신고·환급 금액이 아닌 시연 결과</small>
              </div>
              <div className="dash-secondary">
                <Wallet size={18} />
                <span>기납부세액</span>
                <b>
                  {money(r.withheldTax)}
                  <small>원</small>
                </b>
                <p>이미 낸 세금 · 입력값</p>
              </div>
              <div className="dash-secondary">
                <ShieldCheck size={18} />
                <span>예상 결정세액</span>
                <b>
                  {money(r.decidedTax)}
                  <small>원</small>
                </b>
                <p>최종 부담할 세금 · 데모값</p>
              </div>
            </div>
            <div className="dash-equation">
              <span>기납부세액 − 결정세액 = 환급액</span>
              <b>
                {money(r.withheldTax)}원 − {money(r.decidedTax)}원 = {money(r.expectedRefund)}원
              </b>
              {r.expectedRefund < 0 && (
                <small>
                  차이가 음수이므로 {money(Math.abs(r.expectedRefund))}원을 예상 추가 납부액으로
                  표시합니다.
                </small>
              )}
              <Jump onClick={normalInput}>입력 정보 수정</Jump>
            </div>
          </section>
          <section className="card dash-calculation">
            <details>
              <summary className="dash-disclosure">
                <div>
                  <h3>세금 계산 상세</h3>
                  <p>과세표준과 공제 적용 흐름을 확인하세요.</p>
                </div>
                <span>
                  <Badge tone="gray">법정 계산 미연동</Badge>
                  <ChevronDown size={17} />
                </span>
              </summary>
              <ol className="dash-tax-steps">
                {taxSteps.map(([title, value, reason], i) => (
                  <li key={title}>
                    <span className="dash-step-number">{i + 1}</span>
                    <div>
                      <b>{title}</b>
                      <small>{reason}</small>
                    </div>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ol>
              <div className="dash-note">
                기납부세액 {money(r.withheldTax)}원은 결정세액 계산 후 정산에 사용됩니다.
                {isDemo
                  ? '현재 결과는 체험용이며 법정 계산·증빙 검증은 미연동입니다.'
                  : '계산 API에서 제공한 결과입니다.'}
              </div>
              <DeductionDetails details={r.details} calculationConnected={!isDemo} />
            </details>
          </section>
          <section className="card deductions">
            <div className="card-heading">
              <h3>계산에 반영된 공제·감면</h3>
              <Badge tone="amber">{isDemo ? '실제 반영액 미산출' : '계산 결과'}</Badge>
            </div>
            <p className="dash-description">
              아래 상태는 입력·증빙 확인 상태입니다. 실제 공제액은 계산 결과와 구분해 확인하세요.
            </p>
            {deductions.map((item) => (
              <details className="deduction-detail" key={item.id}>
                <summary>
                  <span className="deduction-label">
                    <Badge tone={item.type === '세액감면' ? 'gray' : 'blue'}>{item.type}</Badge>
                    <b>{item.name}</b>
                  </span>
                  <span className="deduction-value">
                    <Badge tone={item.status === '미적용' ? 'gray' : 'amber'}>{item.status}</Badge>
                    <small>
                      상세 확인 <ChevronDown size={12} />
                    </small>
                  </span>
                </summary>
                <div className="dash-deduction-body">
                  <p>{item.reason}</p>
                  <p className="dash-amount-state">
                    최종 {item.type} 반영액: <b>{groupAmount(item.id)}</b>
                  </p>
                  {item.id === 'cards' && (
                    <>
                      <h4>카드 소득공제 세부 내역</h4>
                      <p className="dash-description">
                        {m.taxYear}년 거래내역 기준 · 도넛 차트와 같은 자료 · 지출액은 저장된
                        거래금액의 집계이며 세법상 적격 확정 금액이 아닙니다.
                      </p>
                      <div className="dash-table-scroll">
                        <table
                          className="dash-card-table"
                          aria-label="소비 유형별 실제 지출 및 분류 결과"
                        >
                          <thead>
                            <tr>
                              <th>소비 유형</th>
                              <th>
                                실제 지출액
                                <br />
                                <small>저장 내역 집계</small>
                              </th>
                              <th>
                                공제율 적용액
                                <br />
                                <small>한도 전</small>
                              </th>
                              <th>
                                최종 소득공제
                                <br />
                                <small>반영액</small>
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {m.types.map((row) => (
                              <tr key={row.category}>
                                <th scope="row">{row.category}</th>
                                <td>{money(row.spent)}원</td>
                                <td>{pending}</td>
                                <td>{pending}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr>
                              <th>합계</th>
                              <td>{money(m.total)}원</td>
                              <td colSpan={2}>최종 카드 소득공제 합계: {groupAmount('cards')}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                      <div className="dash-rule-list">
                        <div>
                          <b>최저사용기준</b>
                          <p>
                            총급여 {money(data.salary)}원 × 25% = {money(m.minimum)}원. 참고 기준만
                            표시하며, 초과분 배분 계산은 미연동입니다.
                          </p>
                        </div>
                        <div>
                          <b>결제수단 확인 필요</b>
                          <p>
                            일반 사용분은 신용카드 15%, 체크·직불·선불카드 및 현금영수증 30%가 안내
                            기준입니다. 업로드 결제수단을 표시하며 누락 값은 확인 필요로 구분합니다.
                            실제 공제율·한도 계산이 미연동이므로 공제 적용액은 산출하지 않습니다.
                          </p>
                        </div>
                        <div>
                          <b>유형·문화체육 자격</b>
                          <p>
                            대중교통·전통시장 40%, 문화체육 30%는 적격 사용분에 대한 안내
                            기준입니다. 문화체육은 총급여 7천만원 이하 조건이며, 현재 상태:{' '}
                            {m.cultureSalary}. 지정 사업자·서비스 종류·사용일 확인이 필요하며,
                            수영장·체력단련장 시설이용료는 2025년 7월 1일 이후 적격 사용분 확인이
                            필요합니다.
                          </p>
                        </div>
                        <div>
                          <b>추가공제·한도</b>
                          <p>
                            최저사용기준 차감 순서, 급여별 기본한도·추가공제·중복 제외와 유형별 배분
                            로직은 모두 미연동입니다. ‘공제 대상 아님’도 현재 분류 결과이며 증빙
                            검증 전입니다.
                          </p>
                        </div>
                      </div>
                      <div className="dash-note">
                        <b>지출액 ≠ 소득공제액 ≠ 실제 세금 감소액</b>
                        <br />
                        실제 지출액을 최종 카드 공제액으로 확정하지 않습니다. 유형별 최종 반영액과
                        합계는 계산 서비스 연동 후 함께 표시합니다.
                      </div>
                      <a
                        className="dash-source"
                        href={TAX_GUIDANCE}
                        target="_blank"
                        rel="noreferrer"
                      >
                        국세청 공제 기준 안내 확인 ↗
                      </a>
                      <TransactionExamples rows={m.allRows} />
                    </>
                  )}
                </div>
              </details>
            ))}
          </section>
          <section className="card expense-summary">
            <div className="card-heading">
              <h3>한눈에 보는 나의 소비</h3>
              <Jump onClick={normalInput}>입력 정보 수정</Jump>
            </div>
            <p className="dash-description">{m.taxYear}년 귀속 거래자료 · 소비 분포</p>
            {chart(m.rows)}
            <p className="dash-description">
              결제수단 미확인·중복 보류 또는 중복 제외 {m.held}건은 차트·지출액 합계·자동 입력
              집계에서 제외합니다. 위 분류 조회에서는 해당 거래도 확인할 수 있습니다.
            </p>
            <div className="dash-source-facts">
              <div>
                <span>업로드된 거래내역 기간</span>
                <b>{m.period}</b>
              </div>
              <div>
                <span>집계 포함 / 다른 연도·날짜 오류 제외</span>
                <b>
                  {m.rows.length}건 / {m.excluded}건
                </b>
              </div>
              <div>
                <span>선택 연도 업로드 집계액</span>
                <b>{money(m.annualInput)}원</b>
              </div>
              <div>
                <span>차트·상세 표의 거래 합계</span>
                <b>{money(m.total)}원</b>
              </div>
            </div>
            <p className="dash-description">
              {m.annualInput !== m.total
                ? '공제 제외 분류·집계 보류 내역에 따라 계산 입력 합계와 소비 합계가 다를 수 있습니다.'
                : '합계가 같아도 연간 내역의 완전성·중복·세법상 적격은 별도 확인이 필요합니다.'}{' '}
              소비 유형은 세법상 자격 판정과 구분합니다.
            </p>
            <div className="dash-provenance">
              <Badge tone="gray">상호명 대조 {m.matched}건</Badge>
              <Badge tone="gray">머신러닝 미사용</Badge>
              <Badge tone="gray">조회 전용</Badge>
              <Badge tone="amber">미매칭·기타 {m.other}건</Badge>
            </div>
            <p className="dash-description">
              상호명 대조는 예시 목록을 사용합니다. 분류 조회는 증빙 확인을 대신하지 않습니다.
              세법상 적격 검증이 미연동이므로 {m.needsReview}건 모두 확인이 필요합니다.
            </p>
            {m.needsReview > 0 && (
              <p className="dash-description">
                거래 분류는 위 소득공제 상세에서 조회할 수 있습니다. 파일 교체는 정보 입력에서
                진행해주세요.
              </p>
            )}
          </section>
          <section className="card dash-youth">
            <div className="card-heading">
              <h3>
                <Leaf size={18} /> 청년 혜택 자격진단
              </h3>
              <Badge tone={m.youth.status === '미적용' ? 'gray' : 'amber'}>{m.youth.status}</Badge>
            </div>
            <h4>중소기업 취업자 소득세 감면</h4>
            <p>{m.youth.reason}</p>
            <div className="dash-note">
              <b>확인할 증빙</b>
              <br />
              감면 신청서, 취업·근로 증빙, 대상 기업 업종·규모 확인자료, 해당 시 병역 증빙. 현재
              확인 완료된 증빙이 없어 ‘적용 가능’을 확정하지 않습니다.
            </div>
            <Jump onClick={() => go('benefits')}>자격진단 상세 확인</Jump>
          </section>
          <section className="card dash-group">
            <div className="card-heading">
              <h3>
                <ChartNoAxesCombined size={18} /> 그룹 통계 비교
              </h3>
              <Badge tone="gray">2024년 귀속 기준</Badge>
            </div>
            <div className="dash-group-fields">
              <div>
                <small>성별</small>
                <b>{data.gender}</b>
              </div>
              <div>
                <small>연령대</small>
                <b>{m.ageGroup}</b>
                <small>{m.taxYear}년 말 기준</small>
              </div>
              <div>
                <small>연간 총급여</small>
                <b>{m.salaryGroup}</b>
              </div>
            </div>
            <p>
              통계 상세는 성별·연령 집단 평균, 나의 결과, 총급여 집단 평균의 막대 3개를
              결정세액·환급세액 그래프에 각각 표시합니다. 두 집단은 독립적이며 성별·연령·급여를
              동시에 만족하는 평균이 아닙니다. 집단 평균은 제공된 국세청 2024년 귀속 XLSX에서 정제한
              값이며 Oracle DB·실시간 API는 미연동입니다.
            </p>
            <p className="dash-description">
              나의 결과는 {m.taxYear}년 귀속 체험용 계산, 비교 통계는 2024년 귀속입니다. 귀속연도가
              달라 직접 비교할 수 없습니다.
            </p>
            <Jump onClick={() => go('stats')}>그룹 통계 상세 보기</Jump>
          </section>
        </div>
        <aside className="dash-ai" aria-label="AI 절세 가이드">
          {chat}
        </aside>
      </div>
      <p className="page-footer">
        작은 준비가 모여, 더 나은 내일이 됩니다. <Leaf size={12} /> 희망환급
      </p>
    </div>
  );
}
