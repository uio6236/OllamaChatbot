import DeductionDetails from '@/components/common/DeductionDetails.jsx';
import React from 'react';
import { ArrowRight, SlidersHorizontal, Plus, Info } from 'lucide-react';
import { userService, settlementLabel } from '@/api/services.js';
import { newPrototypeId } from '@/api/account-service.js';
import { ChatPanel } from '@/pages/chatbot/ChatPanel.jsx';
import { money, Btn, Tag } from '@/components/common/site-primitives.jsx';

// 시뮬레이션 전후 결과를 비교하고 원본과 분리해 저장합니다.
export default function SimulationPage({
  setMode,
  simTx,
  simUpload,
  histories,
  saved,
  setSaved,
  setFormSeed,
  go,
  notify,
  sim,
  baseData,
  br,
  sr,
}) {
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">SIMULATION RESULT</div>
          <h1>조건을 바꾸니, 이렇게 달라졌어요</h1>
          <p>원본 정보는 그대로 유지하고, 변경한 조건의 결과를 비교해요.</p>
        </div>
        <Btn
          secondary
          onClick={() => {
            setMode('simulation');
            setFormSeed((s) => s + 1);
            go('input');
          }}
        >
          다시 조건 수정 <SlidersHorizontal size={16} />
        </Btn>
      </div>
      <div className="notice amber">
        <Info size={16} />
        체험용 계산 결과입니다. 실제 절세 효과나 법정 계산을 의미하지 않습니다.
      </div>
      <div className="dashboard-grid">
        <div>
          <div className="comparison">
            <section className="card">
              <small>기존 {settlementLabel(br.expectedRefund)}</small>
              <h2>
                {money(Math.abs(br.expectedRefund))}
                <span>원</span>
              </h2>
              <Tag tone="gray">원본 저장 정보</Tag>
            </section>
            <ArrowRight size={22} />
            <section className="card after">
              <small>변경 후 {settlementLabel(sr.expectedRefund)}</small>
              <h2>
                {money(Math.abs(sr.expectedRefund))}
                <span>원</span>
              </h2>
              <Tag>
                {sr.expectedRefund - br.expectedRefund >= 0 ? '+' : ''}
                {money(sr.expectedRefund - br.expectedRefund)}원 변화
              </Tag>
            </section>
          </div>
          <section className="card">
            <h3>변경 후 계산 상세 · 체험용</h3>
            <div className="review">
              <div>
                과세표준{' '}
                <b>
                  {sr.taxableIncome === null
                    ? '계산 API 연동 후 제공'
                    : `${money(sr.taxableIncome)}원`}
                </b>
              </div>
              <div>
                산출세액 <b>{money(sr.calculatedTax)}원</b>
              </div>
            </div>
            <DeductionDetails details={sr.details} />
          </section>
          <section className="card">
            <h3>변경한 조건</h3>
            <table>
              <thead>
                <tr>
                  <th>항목</th>
                  <th>기존</th>
                  <th>변경</th>
                </tr>
              </thead>
              <tbody>
                {[...new Set([...Object.keys(baseData), ...Object.keys(sim)])]
                  .filter(
                    (k) =>
                      ![
                        'consent',
                        'rentPeriod',
                        'socialInsurance',
                        'legacyAnnualRent',
                        'legacyRentNeedsReview',
                        'legacyInsuranceNeedsReview',
                      ].includes(k) && JSON.stringify(baseData[k]) !== JSON.stringify(sim[k]),
                  )
                  .map((k) => (
                    <tr key={k}>
                      <td>
                        {{
                          nationalPension: '국민연금',
                          healthEmploymentInsurance: '건강·고용보험료',
                          taxYear: '귀속 연도',
                          housingSaving: '주택청약',
                          pensionSaving: '연금저축',
                          irp: 'IRP',
                          simulationSpend: '소비 유형별 가상 추가액',
                          scenarioName: '시나리오명',
                          salary: '총급여',
                          paid: '기납부세액',
                          credit: '신용카드',
                          debit: '체크카드',
                          cash: '현금영수증',
                          family: '부양가족',
                          rent: '월세 월 납부액',
                          children: '20세 이하 자녀 수',
                          militaryMonths: '군 복무 개월 수',
                          companySize: '회사 규모',
                          headOfHousehold: '무주택 세대주',
                          rentPeriod: '월세 입력 단위',
                          sme: '감면 자격',
                          name: '이름',
                          birth: '생년월일',
                          gender: '성별',
                          housing: '주택 상태',
                          employed: '취업일',
                          email: '이메일',
                        }[k] || k}
                      </td>
                      <td>
                        {typeof baseData[k] === 'number'
                          ? money(Number(baseData[k]))
                          : baseData[k] == null
                            ? '없음'
                            : typeof baseData[k] === 'object'
                              ? '기존 가상 소비 ' + (baseData[k]?.length || 0) + '건'
                              : String(baseData[k])}
                      </td>
                      <td>
                        {typeof sim[k] === 'number'
                          ? money(Number(sim[k]))
                          : typeof sim[k] === 'object'
                            ? Array.isArray(sim[k])
                              ? sim[k]
                                  .map(
                                    (row) =>
                                      `${{ GENERAL: '일반', TRANSIT: '대중교통', MARKET: '전통시장', CULTURE: '문화체육' }[row.category] || row.category} / ${{ CREDIT: '신용카드', CHECK: '체크카드', CASH: '현금영수증' }[row.payment] || row.payment} ${money(row.amount)}원`,
                                  )
                                  .join(', ')
                              : '변경 정보'
                            : String(sim[k])}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {JSON.stringify({
              ...baseData,
              consent: false,
            }) ===
              JSON.stringify({
                ...sim,
                consent: false,
              }) && <p className="empty">변경한 조건이 없습니다.</p>}
            <div className="review">
              <div>
                변경 후 결정세액 <b>{money(sr.decidedTax)}원</b>
              </div>
              <div>
                변경 후 기납부세액 <b>{money(sr.withheldTax)}원</b>
              </div>
            </div>
            <div className="actions">
              <Btn
                onClick={() => {
                  const next = [
                    {
                      id: newPrototypeId(),
                      scenarioName: sim.scenarioName || '조건 변경 시나리오',
                      baselineData: structuredClone(baseData),
                      basePredictionId: histories[0]?.id || null,
                      date: new Date().toLocaleDateString('ko-KR'),
                      data: sim,
                      transactions: simTx,
                      upload: simUpload,
                      ...sr,
                    },
                    ...saved,
                  ];
                  setSaved(next);
                  userService.save('saved', next);
                  notify('시나리오를 이 브라우저에 별도로 저장했습니다. 원본은 유지됩니다.');
                }}
              >
                시뮬레이션 저장 <Plus size={16} />
              </Btn>
              <Btn secondary onClick={() => go('dashboard')}>
                기존 결과로 돌아가기
              </Btn>
            </div>
          </section>
        </div>
        <ChatPanel data={sim} baseline={baseData} />
      </div>
    </>
  );
}
