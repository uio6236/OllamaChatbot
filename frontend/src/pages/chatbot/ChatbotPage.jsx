import React from 'react';
import { ArrowUpRight, Sparkles } from 'lucide-react';
import { settlementLabel } from '@/api/services.js';
import { ChatPanel } from '@/pages/chatbot/ChatPanel.jsx';
import { money, Btn } from '@/components/common/site-primitives.jsx';

// 전체 상담 화면과 이전 상담 UI를 보여줍니다.
export default function ChatbotPage({ data, go, startSim, r }) {
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">YOUR PERSONAL TAX GUIDE</div>
          <h1>어려운 세금, 쉬운 대화로</h1>
          <p>이미 계산된 결과를 바탕으로 공제와 청년 혜택을 이해해요.</p>
        </div>
        <Btn secondary onClick={() => go('dashboard')}>
          결과와 함께 보기 <ArrowUpRight size={16} />
        </Btn>
      </div>
      <div className="guide-layout">
        <ChatPanel data={data} expanded />
        <div>
          <section className="card">
            <span className="iconbox">
              <Sparkles />
            </span>
            <h2>숫자 뒤의 이유를 알아봐요.</h2>
            <p className="muted">
              AI 가이드는 계산 엔진이 산출한 결과를 설명하는 역할이에요. 현재는 사전 작성된 예시
              응답을 제공합니다.
            </p>
            <div className="review">
              <div>
                현재 {settlementLabel(r.expectedRefund)}
                <b>{money(Math.abs(r.expectedRefund))}원</b>
              </div>
            </div>
            <Btn onClick={startSim}>조건 변경 시뮬레이션</Btn>
          </section>
        </div>
      </div>
    </>
  );
}
