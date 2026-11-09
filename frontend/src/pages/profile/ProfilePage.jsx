import { getTaxYear } from '@/utils/tax-year.js';
import React from 'react';
import { ChevronRight, Plus, Clock } from 'lucide-react';
import { initial, normalizeTaxData, settlementLabel } from '@/api/services.js';
import { WithdrawAccount } from '@/pages/auth/AccountForms.jsx';
import { accountService } from '@/api/account-service.js';
import { ProfileDetails } from '@/pages/profile/ProfileDetails.jsx';
import { money, Btn, Tag, Field } from '@/components/common/site-primitives.jsx';

// 계정·계산 이력·저장한 시나리오를 관리하는 기존 화면입니다.
export default function ProfilePage({
  data,
  setData,
  setTransactions,
  setSimulation,
  setCompareBase,
  session,
  setSession,
  setUpload,
  setSimTx,
  setSimUpload,
  histories,
  setHistories,
  saved,
  setSaved,
  setInquiries,
  profileTab,
  setProfileTab,
  go,
  notify,
  startSim,
  normalInput,
}) {
  return (
    <>
      <div className="heading">
        <div>
          <div className="eyebrow">MY ACCOUNT</div>
          <h1>마이페이지</h1>
          <p>나의 정보와 쌓아온 기록을 한곳에서 관리해요.</p>
        </div>
        <Tag tone="gray">브라우저 내 저장</Tag>
      </div>
      <div className="profile-hero card">
        <span className="avatar large">희</span>
        <div>
          <h2>{data.name}님</h2>
          <p>{data.email.replace(/^(.{1,2}).*(@.*)$/, '$1***$2')}</p>
        </div>
        <Tag>{session?.role || '비로그인 체험'}</Tag>
      </div>
      <div className="tabs">
        {['개인정보', '비밀번호 변경', '이전 계산 결과', '저장한 시뮬레이션', '계정 관리'].map(
          (t) => (
            <button
              className={profileTab === t ? 'active' : ''}
              onClick={() => setProfileTab(t)}
              key={t}
            >
              {t}
            </button>
          ),
        )}
      </div>
      <section className="card">
        {profileTab === '개인정보' ? (
          <ProfileDetails
            data={data}
            onChange={(u) => {
              setSession(u);
              setData({
                ...data,
                gender: u.gender || '',
              });
              notify('성별을 수정했습니다. 아이디·이메일·생년월일은 유지됩니다.');
            }}
          />
        ) : profileTab === '비밀번호 변경' ? (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget,
                f = new FormData(form);
              try {
                await accountService.changePassword(
                  String(f.get('old') || ''),
                  String(f.get('new') || ''),
                  String(f.get('confirm') || ''),
                );
                form.reset();
                notify('브라우저 시연 계정 비밀번호를 변경했습니다.');
              } catch (err) {
                notify(err.message);
              }
            }}
          >
            <h3>비밀번호 변경 (시연)</h3>
            <div className="form-grid">
              <Field label="현재 비밀번호">
                <input name="old" type="password" required />
              </Field>
              <Field label="새 비밀번호">
                <input name="new" type="password" minLength={8} required />
              </Field>
              <Field label="새 비밀번호 확인">
                <input name="confirm" type="password" required />
              </Field>
            </div>
            <Btn type="submit">비밀번호 변경</Btn>
          </form>
        ) : profileTab === '계정 관리' ? (
          <>
            {session ? (
              <WithdrawAccount
                onDone={() => {
                  setSession(null);
                  setData(initial);
                  setTransactions([]);
                  setUpload(null);
                  setHistories([]);
                  setSaved([]);
                  setInquiries([]);
                  setSimulation(null);
                  setCompareBase(null);
                  setSimTx([]);
                  go('login');
                  notify(
                    '탈퇴 상태로 전환하고 로그아웃했습니다. 30일 유예 후 자동 처리는 서버 연동이 필요합니다.',
                  );
                }}
              />
            ) : (
              <>
                <p>로그인 후 회원 탈퇴를 진행할 수 있습니다.</p>
                <Btn onClick={() => go('login')}>로그인</Btn>
              </>
            )}
          </>
        ) : (
          <>
            <h3>{profileTab}</h3>
            {(profileTab === '이전 계산 결과' ? histories : saved).length === 0 ? (
              <div className="empty">
                <Clock size={30} />
                <p>아직 저장된 기록이 없어요.</p>
                <Btn secondary onClick={profileTab === '이전 계산 결과' ? normalInput : startSim}>
                  첫 기록 만들기 <Plus size={14} />
                </Btn>
              </div>
            ) : (
              (profileTab === '이전 계산 결과' ? histories : saved).map((h, i) => (
                <div className="history-row" key={i}>
                  <span className="iconbox">
                    <Clock size={18} />
                  </span>
                  <div>
                    <b>
                      {h.date} {h.scenarioName || ''}
                    </b>
                    <p>
                      {h.taxYear || '연도 미기록'}년 귀속 ·{' '}
                      {h.legacyResult ? '이전 체험 결과' : '체험용 결과'}
                    </p>
                  </div>
                  <b>
                    {settlementLabel(h.expectedRefund)} {money(Math.abs(h.expectedRefund))}원
                  </b>
                  {h.data && (
                    <button
                      className="text-btn"
                      onClick={() => {
                        setCompareBase(h.baselineData || data);
                        setSimulation(normalizeTaxData(h.data));
                        setSimTx(h.transactions || []);
                        setSimUpload(h.upload || null);
                        go('compare');
                      }}
                    >
                      비교 결과 보기 <ChevronRight size={15} />
                    </button>
                  )}
                </div>
              ))
            )}
          </>
        )}
      </section>
    </>
  );
}
