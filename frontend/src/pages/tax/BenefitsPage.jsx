import { benefitChecks } from '@/utils/benefit-model.js';
import React from 'react';
import { ArrowRight, FilePenLine, Info, CheckCircle2, Building2, House, Users } from 'lucide-react';
import { Btn, Tag } from '@/components/common/site-primitives.jsx';

// 기존 청년 혜택 확인 화면입니다.
export default function BenefitsPage({ data, normalInput }) {
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">YOUNG & ELIGIBLE</div>
          <h1>청년의 가능성, 혜택으로 이어지도록</h1>
          <p>나에게 맞는 혜택과 추가로 확인할 조건을 살펴보세요.</p>
        </div>
        <Btn secondary onClick={normalInput}>
          자격 정보 수정 <FilePenLine size={16} />
        </Btn>
      </div>
      <div className="benefit-hero">
        <div>
          <Tag tone="green">청년 특화 혜택</Tag>
          <h2>중소기업 취업자 소득세 감면</h2>
          <p>
            취업 당시 연령과 기업 요건 등을 확인해보세요.
            <br />
            모든 조건이 확인되기 전에는 적용을 확정할 수 없어요.
          </p>
        </div>
        <Building2 size={100} strokeWidth={1} />
      </div>
      <section className="card">
        <div className="card-heading">
          <h3>나의 자격 체크리스트</h3>
          <Tag tone="amber">증빙 확인 필요</Tag>
        </div>
        {[
          ['취업 당시 연령', '청년 연령 요건 · 병역 기간 등 별도 확인', data.birth],
          ['취업일', '지원 대상 취업 기간 확인', data.employed],
          ['군 복무 개월 수', '병역 증빙 확인', String(data.militaryMonths ?? 0) + '개월'],
          ['기업 규모와 업종', '회사에 감면 대상 기업 여부 확인', data.companySize || '확인 필요'],
          ['신청 및 증빙', '감면 신청서 제출 여부 확인', '확인 필요'],
        ].map(([t, d, v]) => (
          <div className="benefit-row" key={t}>
            <span className="iconbox">
              <CheckCircle2 size={19} />
            </span>
            <div>
              <h3>{t}</h3>
              <p>{d}</p>
            </div>
            <span>{v}</span>
            <Tag tone="amber">확인 필요</Tag>
          </div>
        ))}
        <div className="notice">
          <Info size={16} />
          자격판정 서비스 연결 전입니다. 입력한 '해당' 여부는 자가 선택이며 실제 자격 승인을
          의미하지 않습니다.
        </div>
      </section>
      <div className="two-col">
        {benefitChecks(data).map((item) => (
          <section className="card" key={item.name}>
            <h3>{item.name}</h3>
            <Tag tone={item.status === '비해당' ? 'gray' : 'amber'}>{item.status} · 입력 기준</Tag>
            <p>{item.reason}</p>
            <p className="muted">필요한 정보·조건: {item.requirements}</p>
            <p className="muted">실제 계산·자격 진단 서버 미연동. 최종 혜택 판정이 아닙니다.</p>
          </section>
        ))}
        <section className="card">
          <Users className="blue" />
          <h3>부양가족 기본공제</h3>
          <p className="muted">
            추가 입력 가족 {data.family}명 · 소득·연령·중복공제 요건을 확인하세요.
          </p>
          <Btn secondary onClick={normalInput}>
            내 정보 확인하기 <ArrowRight size={14} />
          </Btn>
        </section>
      </div>
    </>
  );
}
