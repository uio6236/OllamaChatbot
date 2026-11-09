import React from 'react';
import { Plus, Search, Send, Mail } from 'lucide-react';
import { inquiryService, inquiryLabels } from '@/api/prototype-records.js';
import { Btn, Tag, Field } from '@/components/common/site-primitives.jsx';

// FAQ·문의 작성·내 문의 목록을 보여줍니다.
export default function SupportPage({
  inquiries,
  setInquiries,
  search,
  setSearch,
  faq,
  setFaq,
  supportTab,
  setSupportTab,
  notify,
}) {
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">WE ARE HERE TO HELP</div>
          <h1>무엇을 도와드릴까요?</h1>
          <p>자주 묻는 질문부터 나의 문의까지, 편하게 확인하세요.</p>
        </div>
        <Btn onClick={() => setSupportTab('문의 작성')}>
          <Plus size={16} />
          문의하기
        </Btn>
      </div>
      <div className="tabs">
        {['자주 묻는 질문', '문의 내역', '문의 작성'].map((t) => (
          <button
            key={t}
            className={supportTab === t ? 'active' : ''}
            onClick={() => setSupportTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <section className="card">
        {supportTab === '자주 묻는 질문' ? (
          <>
            <div className="search wide">
              <Search size={18} />
              <input
                placeholder="궁금한 내용을 검색해보세요"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            {[
              [
                '예상 환급액은 실제 금액과 같은가요?',
                '현재 결과는 체험용 계산입니다. 실제 세법 계산이 아니며, 실제 신고·납부에 사용할 수 없습니다.',
              ],
              [
                '시뮬레이션을 하면 원래 정보가 바뀌나요?',
                '아니요. 저장된 정보의 복사본으로 같은 입력 폼을 재사용합니다. 원본은 유지되며 시뮬레이션 결과는 선택적으로 따로 저장할 수 있어요.',
              ],
              [
                '카드 내역은 어떻게 분류하나요?',
                '예시 공공데이터 상호명 목록과 대조합니다. 미매칭 거래는 일반으로 임시 분류됩니다. 거래 유형은 대시보드에서 조회하고 파일은 정보 입력에서 교체할 수 있어요. 머신러닝은 사용하지 않습니다.',
              ],
              [
                'AI가 직접 세금을 계산하나요?',
                'AI는 계산 결과를 설명하는 역할입니다. 이 프로토타입은 실제 LLM 대신 예시 응답을 사용해요.',
              ],
              [
                '입력한 정보는 어디에 저장되나요?',
                '현재는 이 브라우저에 보관됩니다. 업로드는 파일별 삭제할 수 있습니다. 탈퇴 시 계정은 즉시 로그인 차단되며, 30일 경과 후 식별 정보 자동 처리는 서버 구현이 필요합니다.',
              ],
            ]
              .filter(([q, a]) => (q + a).includes(search))
              .map(([q, a], i) => (
                <div className="faq" key={q}>
                  <button onClick={() => setFaq(faq === i ? null : i)}>
                    <span>Q</span>
                    {q}
                    <Plus size={17} />
                  </button>
                  {faq === i && <p>{a}</p>}
                </div>
              ))}
          </>
        ) : supportTab === '문의 작성' ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              try {
                inquiryService.create(
                  String(f.get('category') || ''),
                  String(f.get('title') || ''),
                  String(f.get('text') || ''),
                );
                setInquiries(inquiryService.list());
                setSupportTab('문의 내역');
                notify('문의가 브라우저에 접수되었습니다. 서버 전송은 미연동입니다.');
              } catch (err) {
                notify(err.message);
              }
            }}
          >
            <h3>문의 작성</h3>
            <Field label="문의 유형">
              <select name="category" required>
                <option value="">유형을 선택해주세요</option>
                <option value="ERROR">오류</option>
                <option value="QUESTION">문의</option>
                <option value="ETC">기타</option>
              </select>
            </Field>
            <Field label="제목">
              <input name="title" maxLength={66} required placeholder="문의 제목을 입력해주세요" />
            </Field>
            <Field label="문의 내용">
              <textarea
                rows={6}
                name="text"
                required
                placeholder="주민등록번호, 카드번호 등 민감한 정보는 적지 마세요."
              />
            </Field>
            <Btn type="submit">
              문의 접수 (시연) <Send size={15} />
            </Btn>
          </form>
        ) : inquiries.length ? (
          inquiries.map((q) => (
            <details className="inquiry" key={q.id}>
              <summary>
                <Tag tone={q.status === 'ANSWERED' ? 'green' : 'amber'}>
                  {inquiryLabels[q.status] || '접수'}
                </Tag>
                <span className="tag gray">{inquiryLabels[q.category] || '문의'}</span>
                <b>{q.title}</b>
                <small>{q.date}</small>
              </summary>
              <p>{q.text}</p>
              {q.answeredAt && (
                <small>답변 시각: {new Date(q.answeredAt).toLocaleString('ko-KR')}</small>
              )}
              <div className="review">
                <b>답변</b>
                <p>
                  {q.status === 'CHECKING'
                    ? '확인 후 답변 드리겠습니다.'
                    : q.answer || '접수되었습니다. 답변을 기다리고 있습니다.'}
                </p>
              </div>
            </details>
          ))
        ) : (
          <div className="empty">
            <Mail size={32} />
            <p>접수된 문의가 없어요.</p>
            <Btn secondary onClick={() => setSupportTab('문의 작성')}>
              문의 작성하기
            </Btn>
          </div>
        )}
      </section>
    </>
  );
}
