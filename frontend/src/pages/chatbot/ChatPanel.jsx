import { getTaxYear } from '@/utils/tax-year.js';
// 계산 결과에 연결된 상담 UI와 대화방 상태를 관리합니다. TODO: Gemma3 호출과 대화 DB 저장은 Spring Boot를 통해 연결합니다.
import { newPrototypeId } from '@/api/account-service.js';
import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowUpRight, Send, History, Plus, ChevronDown, Check } from 'lucide-react';
import { aiService, userService } from '@/api/services.js';
const mask = (s) =>
  s
    .replace(/\b\d{6}[- ]?[1-4]\d{6}\b/g, '[주민번호 가림]')
    .replace(/\b(?:\d{4}[- ]?){3}\d{4}\b/g, '[카드번호 가림]');
export function ChatPanel({ data, baseline, expanded = false, reply }) {
  // 상담방 선택과 작성 중인 질문은 React 상태로 관리합니다.
  const [rooms, setRooms] = useState([]),
    [roomId, setRoomId] = useState(''),
    [q, setQ] = useState(''),
    [ready, setReady] = useState(false),
    [historyOpen, setHistoryOpen] = useState(false);
  const predictionKey = JSON.stringify({ data, baseline });
  function makeRoom() {
    return {
      id: newPrototypeId(),
      title: baseline ? '조건 변경 상담' : '연말정산 결과 상담',
      createdAt: new Date().toISOString(),
      predictionKey,
      MODEL_NAME: null,
      messages: [
        {
          MESSAGE_ID: 1,
          role: 'ai',
          text: reply ? reply('결과', data) : aiService.reply('결과', data, baseline),
        },
      ],
    };
  }
  // 현재 계산 조건과 연결된 기존 대화를 불러오고 없을 때만 첫 상담을 만듭니다.
  useEffect(() => {
    const all = userService.load('chat-rooms-v38', []);
    let room = all.find((r) => r.predictionKey === predictionKey);
    if (!room) {
      room = makeRoom();
      all.unshift(room);
      userService.save('chat-rooms-v38', all);
    }
    setRooms(all);
    setRoomId(room.id);
    setReady(true);
    setHistoryOpen(false);
  }, [predictionKey]);
  const related = rooms.filter((r) => r.predictionKey === predictionKey);
  const roomTitle = (room) =>
    /^(현재 결과|시나리오) 상담 /.test(room.title)
      ? room.title.startsWith('시나리오')
        ? '조건 변경 상담'
        : '연말정산 결과 상담'
      : room.title;
  const roomDate = (room) =>
    room.createdAt
      ? new Date(room.createdAt).toLocaleString('ko-KR', {
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : room.title.replace(/^(현재 결과|시나리오) 상담\s*/, '');
  const active = rooms.find((r) => r.id === roomId);
  // TODO: 실제 상담방·메시지 저장 API로 교체할 위치입니다.
  function persist(next) {
    setRooms(next);
    userService.save('chat-rooms-v38', next);
  }
  function send(text) {
    if (!text.trim() || !active) return;
    const last = active.messages.at(-1)?.MESSAGE_ID || 0;
    const messages = [
      ...active.messages,
      { MESSAGE_ID: last + 1, role: 'user', text: mask(text.trim()) },
      {
        MESSAGE_ID: last + 2,
        role: 'ai',
        text: reply ? reply(text, data) : aiService.reply(text, data, baseline),
      },
    ];
    persist(rooms.map((r) => (r.id === roomId ? { ...r, messages } : r)));
    setQ('');
  }
  return (
    <section className={'card chat ' + (expanded ? 'expanded' : '')}>
      <div className="chat-title">
        <span className="iconbox">
          <Sparkles size={20} />
        </span>
        <div>
          <h3>AI 절세 가이드</h3>
          <small>이미 계산된 결과 설명</small>
        </div>
        <span className="tag gray">체험 응답</span>
      </div>
      {expanded && (
        <div className="chat-conversation-tools">
          <div className="chat-toolbar">
            <button
              type="button"
              className={'chat-tool-button ' + (historyOpen ? 'is-open' : '')}
              aria-expanded={historyOpen}
              aria-controls="chat-history-list"
              onClick={() => setHistoryOpen(!historyOpen)}
            >
              <History size={15} />
              이전 상담
              <ChevronDown size={14} />
            </button>
            <button
              type="button"
              className="chat-tool-button"
              disabled={!ready}
              onClick={() => {
                const room = makeRoom();
                persist([room, ...rooms]);
                setRoomId(room.id);
                setHistoryOpen(false);
                setQ('');
              }}
            >
              <Plus size={15} />새 상담
            </button>
          </div>
          {historyOpen && (
            <div className="chat-history" id="chat-history-list">
              <p>이 계산 결과에 대한 상담 기록</p>
              {related.map((room) => (
                <button
                  type="button"
                  className={'chat-history-item ' + (room.id === roomId ? 'is-selected' : '')}
                  aria-pressed={room.id === roomId}
                  key={room.id}
                  onClick={() => {
                    setRoomId(room.id);
                    setHistoryOpen(false);
                    setQ('');
                  }}
                >
                  <span>
                    <b>{roomTitle(room)}</b>
                    <small>{roomDate(room)}</small>
                  </span>
                  {room.id === roomId && <Check size={15} />}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="chat-messages">
        <div className="chat-date">
          {getTaxYear(data)}년 귀속 · {baseline ? '조건 변경 결과 상담' : '연말정산 결과 상담'}
        </div>
        {active?.messages.map((m) => (
          <div key={m.MESSAGE_ID} className={'message ' + m.role}>
            {m.role === 'ai' && (
              <span className="ai-label">
                <Sparkles size={12} /> 희망 AI
              </span>
            )}
            <p>{m.text}</p>
            {m.role === 'ai' && <small>시연용 안내 · 세무 자문 아님</small>}
          </div>
        ))}
      </div>
      <div className="chat-bottom">
        <small>이렇게 물어보세요</small>
        {['소득공제와 세액공제는 어떻게 달라요?', '청년 감면에 어떤 서류가 필요해요?'].map((s) => (
          <button className="prompt" key={s} onClick={() => send(s)}>
            {s}
            <ArrowUpRight size={14} />
          </button>
        ))}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(q);
          }}
        >
          <input
            aria-label="AI 질문"
            placeholder="궁금한 점을 물어보세요"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button aria-label="질문 보내기" disabled={!ready}>
            <Send size={16} />
          </button>
        </form>
        <small className="footnote">
          체험용 답변 · 실제 AI는 연결되지 않았습니다. 대화는 현재 브라우저에 저장되며, 민감한
          개인정보는 입력하지 마세요.
        </small>
      </div>
    </section>
  );
}
