import { getDefaultTaxYear } from '@/utils/tax-year.js';
import React from 'react';
import {
  ArrowUpRight,
  ArrowRight,
  ChevronRight,
  FilePenLine,
  Sparkles,
  SlidersHorizontal,
  ShieldCheck,
  Leaf,
  TrendingUp,
  CheckCircle2,
} from 'lucide-react';
import { Logo, Btn, Tag, MiniChart } from '@/components/common/site-primitives.jsx';

// 현재 사이트의 랜딩 화면을 그대로 분리했습니다.
export default function HomePage({ go, startSim, normalInput }) {
  return (
    <>
      <main className="landing">
        <div className="hero">
          <section className="hero-copy">
            <div className="pill">
              <span />
              청년의 내일을 응원하는 연말정산
            </div>
            <h1>
              나의 연말정산,
              <br />
              <em>희망</em>이 되는 환급.
            </h1>
            <p>
              복잡한 연말정산은 가볍게,
              <br />
              놓치기 쉬운 절세 혜택은 꼼꼼하게 찾아보세요.
            </p>
            <div className="hero-actions">
              <Btn onClick={() => go('signup')}>
                나의 예상 환급액 알아보기 <ArrowRight size={18} />
              </Btn>
              <button className="text-btn" onClick={() => go('dashboard')}>
                체험 먼저 해보기 <ArrowUpRight size={17} />
              </button>
            </div>
            <div className="hero-trust">
              <span>
                <ShieldCheck size={15} />
                개인정보는 최소한으로
              </span>
              <span>
                <CheckCircle2 size={15} />
                별도 비용 없이 체험
              </span>
            </div>
          </section>
          <div className="hero-visual">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="float-badge">
              <span className="iconbox mint">
                <ShieldCheck />
              </span>
              <div>
                <b>놓친 혜택 없이, 꼼꼼하게</b>
                <small>청년을 위한 맞춤 가이드</small>
              </div>
              <CheckCircle2 size={17} color="#37a78e" />
            </div>
            <div className="hero-result">
              <div className="result-top">
                <Logo />
                <Tag>{getDefaultTaxYear()}년 귀속</Tag>
              </div>
              <small>사용자님의 예상 환급액</small>
              <h2>
                423,000<span>원</span>
                <span className="sparkle-symbol">✧</span>
              </h2>
              <div className="result-growth">
                <TrendingUp size={15} />
                나의 가능성을 숫자로 확인해요
              </div>
              <div className="hero-equation">
                <div>
                  기납부세액<b>1,523,000원</b>
                </div>
                <span>−</span>
                <div>
                  예상 결정세액<b>1,100,000원</b>
                </div>
              </div>
              <div className="hero-chart-title">
                <b>한눈에 보는 나의 지출</b>
                <small>1월 — 12월</small>
              </div>
              <MiniChart />
              <div className="preview-disclaimer">
                시연용 예시 데이터 · 실제 세액과 다를 수 있어요
              </div>
            </div>
            <div className="float-ai">
              <span className="iconbox">
                <Sparkles />
              </span>
              <div>
                <b>희망 AI가 알려드려요</b>
                <p>청년 감면 혜택도 확인해볼까요?</p>
              </div>
              <ArrowUpRight size={18} />
            </div>
            <span className="decor-star s1">✧</span>
            <span className="decor-star s2">✦</span>
          </div>
        </div>
        <div className="landing-strip">
          <span>
            어려운 세금 용어 대신, <b>나에게 필요한 이야기.</b>
          </span>
          <div>
            정보 입력 <ChevronRight size={15} /> 예상 결과 확인 <ChevronRight size={15} /> AI 맞춤
            가이드
          </div>
        </div>
        <section id="features" className="feature-section">
          <div className="eyebrow">SMART TAX, BRIGHTER TOMORROW</div>
          <h2>환급을 넘어, 더 나은 내일을 준비해요.</h2>
          <p>처음 하는 연말정산도 혼자 고민하지 않도록.</p>
          <div className="features">
            {[
              [
                FilePenLine,
                '01',
                '차근차근, 쉬운 정보 입력',
                '나의 소득과 지출을 단계별로 정리하고\n연말정산의 첫걸음을 시작하세요.',
              ],
              [
                Sparkles,
                '02',
                '나를 이해하는 AI 가이드',
                '계산 결과가 왜 나왔는지, 어떤 혜택을\n확인해야 하는지 쉽게 알아보세요.',
              ],
              [
                SlidersHorizontal,
                '03',
                '바꿔보며 찾는 절세 방향',
                '카드 사용, 월세 등 조건을 바꾸고\n변경 전후의 예시 결과를 비교하세요.',
              ],
            ].map(([Icon, n, title, desc]) => (
              <button
                className="feature"
                key={n}
                onClick={() => (n === '01' ? normalInput() : n === '02' ? go('guide') : startSim())}
              >
                <div>
                  <span className="feature-icon">
                    <Icon size={24} />
                  </span>
                  <small>{n}</small>
                </div>
                <h3>{title}</h3>
                <p>{desc}</p>
                <ArrowUpRight size={19} />
              </button>
            ))}
          </div>
        </section>
        <section id="how" className="how-section">
          <div>
            <Tag>HOW IT WORKS</Tag>
            <h2>
              내 정보를 채우면,
              <br />
              환급의 흐름이 보여요.
            </h2>
            <p>
              원본 정보는 그대로 두고 조건만 바꿔보는
              <br />
              시뮬레이션까지, 한곳에서 이어집니다.
            </p>
            <Btn onClick={() => go('dashboard')}>
              예시 대시보드 둘러보기 <ArrowRight size={16} />
            </Btn>
          </div>
          <div>
            {[
              ['01', '나의 소득·지출 입력', '여섯 단계로 나누어 필요한 정보를 입력해요.'],
              ['02', '예상 결과와 AI 설명 확인', '환급액과 공제 항목을 함께 이해해요.'],
              ['03', '조건 변경하고 결과 비교', '저장된 정보로 바로 시작하고 차이를 확인해요.'],
            ].map(([n, t, d]) => (
              <article key={n}>
                <span>{n}</span>
                <div>
                  <h3>{t}</h3>
                  <p>{d}</p>
                </div>
                <CheckCircle2 size={20} />
              </article>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <Leaf size={34} />
          <h2>나의 내일에, 작은 희망을 더하세요.</h2>
          <p>지금 희망환급에서 나의 연말정산을 시작해보세요.</p>
        </section>
      </main>
      <footer>
        <Logo />
        <span>© 2025 희망환급. 청년을 위한 연말정산 프로토타입.</span>
        <span>시연용 서비스 · 실제 세무 신고에 사용할 수 없습니다.</span>
      </footer>
    </>
  );
}
