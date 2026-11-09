// 성별·연령과 급여 구간을 독립적으로 비교합니다. 그룹 평균에는 사용자 결과를 합산하지 않습니다.
import React from 'react';
import { Info, ArrowRight } from 'lucide-react';
import { groupComparison } from '@/utils/group-model.js';
export default function GroupStats({ data, go }) {
  const m = groupComparison(data);
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">TAX INSIGHTS</div>
          <h1>함께 살펴보는 연말정산</h1>
          <p>성별·연령 집단과 총급여 집단을 각각 독립적으로 비교해요.</p>
        </div>
        <span className="tag gray">2024년 귀속 · 제공 원본 파일 반영</span>
      </div>
      <div className="notice amber">
        <Info size={16} />
        <span>
          제공된 국세청 2024년 귀속 4.2.3·4.2.4 XLSX 파일에서 정제한 통계입니다. 실시간 API·Oracle
          DB는 미연동입니다. 사용자·체험 회원 계산은 공식 집단 평균에 합산하지 않습니다. 나의 값은
          {m.taxYear}년 체험용 계산으로 귀속연도·계산 방식이 달라 직접적인 우열이나 절세 효과로
          해석할 수 없습니다.
        </span>
      </div>
      <div className="two-col">
        {['decidedTax', 'expectedRefund'].map((key) => {
          const max = Math.max(...m.rows.map((row) => Math.abs(row[key] ?? 0)), 1);
          return (
            <section className="card" key={key}>
              <div className="card-heading">
                <h3>{key === 'decidedTax' ? '평균 결정세액 비교' : '평균 환급세액 비교'}</h3>
                <span className="tag gray">원 · 집단 평균 / 나의 데모</span>
              </div>
              <div
                className="comparison-bars"
                role="img"
                aria-label={
                  key === 'decidedTax' ? '결정세액 3개 막대 비교' : '환급세액 3개 막대 비교'
                }
              >
                {m.rows.map((row, i) => (
                  <div className="comparison-bar" key={row.label}>
                    <strong>
                      {row[key] === null ? '확인 필요' : `${row[key].toLocaleString()}원`}
                    </strong>
                    <div className="bar-track">
                      <div
                        style={{
                          height:
                            row[key] === null
                              ? 0
                              : Math.max(2, (Math.abs(row[key] || 0) / max) * 100) + '%',
                          background:
                            row[key] < 0
                              ? '#d45b61'
                              : i === 1
                                ? '#2767f5'
                                : i === 0
                                  ? '#97b9ff'
                                  : '#58c3ae',
                        }}
                      />
                    </div>
                    <b>{row.label}</b>
                    {key === 'expectedRefund' && row[key] < 0 && (
                      <small>예상 추가 납부 {Math.abs(row[key]).toLocaleString()}원</small>
                    )}
                    <small>{row.kind}</small>
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      <section className="card stats-explanation">
        <h3>서로 다른 두 집단입니다</h3>
        <p>
          <b>성별·연령 집단:</b>{' '}
          {m.valid ? `${m.ageGroup} ${data.gender}` : '성별·생년월일 확인 필요'}. 사용자 총급여
          조건을 추가하지 않습니다.
        </p>
        <p>
          <b>총급여 집단:</b> {m.salaryGroup}. 사용자 성별·연령 조건을 추가하지 않습니다.
        </p>
        <p>
          두 조건을 동시에 만족하는 집단 평균을 만든 것이 아닙니다. 연령은 입력 생년월일의{' '}
          {m.taxYear}년 말 만 나이로 비교 집단을 선택합니다. 연령 경계는 30세 미만, 30~39, 40~49,
          50~59, 60~69, 70세 이상이며 총급여는 원본 구간의 시작 초과·끝 이하로 조회합니다.
        </p>
        <p>
          <b>평균 산식:</b> 원본 금액(백만원) × 1,000,000 ÷ 해당 그룹 신고 인원, 원 단위 반올림.
          환급세액은 환급을 받지 않은 인원도 포함한 그룹 신고 인원으로 나눈 값이며 실제 환급자만의
          평균이 아닙니다. 세액 항목별 인원을 분모로 섞지 않습니다.
        </p>
        <p>
          <b>급여 구간 모집단 주의:</b> 1억 원 이하는 결정세액 있는 자·없는 자를 합산합니다. 1억 원
          초과는 없는 자의 세부 급여 구간이 제공되지 않아 해당 세부 구간에 임의 배분하지 않고
          결정세액 있는 자만 비교합니다. 선택 구간의 모집단:{' '}
          {m.salaryPopulation || '조회 대상 없음'}.
        </p>
        <p>
          <b>평균 연봉을 제공하지 않습니다.</b> 원본은 신규 입사·중도 퇴사·이중 근로 및 합산하지
          않은 복수 사업장 신고가 포함될 수 있어 1인당 총급여를 일반적인 연봉 수준으로 해석할 수
          없습니다. 성별·연령 미상자는 4.2.3에서 제외되어 두 표의 모집단 합계도 다릅니다.
        </p>
        <p>
          출처: 국세청 4.2.3 근로소득 연말정산 신고 현황Ⅲ(성·연령), 4.2.4 현황Ⅳ(과세대상근로소득),
          2024년 귀속 · 제공 XLSX 내려받은 날짜 2026-10-28. 정제 자료 28행과 원본 파일 경로를 코드에
          보관합니다.
        </p>
        <p>
          추가 납부가 예상되면 나의 환급세액은 음수로 보존하고 빨간 막대와 추가 납부액 안내로
          구분합니다.
        </p>
        {go && (
          <button className="btn secondary" onClick={() => go('dashboard')}>
            나의 예상 결과 보기 <ArrowRight size={16} />
          </button>
        )}
      </section>
    </>
  );
}
