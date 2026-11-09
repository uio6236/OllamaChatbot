import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { userService, categories } from '@/api/services.js';
import { MemberManagement } from '@/pages/auth/AccountForms.jsx';
import { accountService } from '@/api/account-service.js';
import {
  CriteriaManagement,
  AccessLog,
  Predictions,
  InquiryManagement,
} from '@/pages/admin/AdminTools.jsx';
import { recordAccess } from '@/api/prototype-records.js';
import { Btn, Tag, Field } from '@/components/common/site-primitives.jsx';

// 권한 상태에 따라 기존 관리자 콘솔 또는 접근 안내를 보여줍니다.
export default function AdminPage({
  admin,
  adminTab,
  setAdminTab,
  publicList,
  setPublicList,
  refreshSession,
  go,
  notify,
}) {
  return (
    <>
      {!admin ? (
        <section className="card empty">
          <ShieldCheck size={40} />
          <h2>관리자 권한이 필요합니다</h2>
          <p>
            관리자로 로그인한 계정만 접근할 수 있습니다. 현재 권한 검사는 이 브라우저의 시연
            로직입니다.
          </p>
          <Btn onClick={() => go('login')}>로그인 화면으로</Btn>
        </section>
      ) : (
        <>
          <div className="heading">
            <div>
              <div className="eyebrow">ADMIN WORKSPACE · DEMO</div>
              <h1>관리자 콘솔</h1>
              <p>일반 사용자 기능과 분리된 관리 도구입니다. 모든 변경은 시연용입니다.</p>
            </div>
            <Tag>관리자</Tag>
          </div>
          <div className="tabs">
            {[
              '문의 관리',
              '회원 관리',
              '공제 기준값',
              '공공데이터 목록',
              '예측 결과',
              '접근 기록',
            ].map((t) => (
              <button
                className={adminTab === t ? 'active' : ''}
                key={t}
                onClick={() => {
                  recordAccess('ADMIN_' + t);
                  setAdminTab(t);
                }}
              >
                {t}
              </button>
            ))}
          </div>
          <section className="card">
            {adminTab === '문의 관리' ? (
              <InquiryManagement />
            ) : adminTab === '회원 관리' ? (
              <MemberManagement onChange={refreshSession} />
            ) : adminTab === '공제 기준값' ? (
              <CriteriaManagement />
            ) : adminTab === '접근 기록' ? (
              <AccessLog />
            ) : adminTab === '예측 결과' ? (
              <Predictions />
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (
                    publicList.split('\n').some((l) => {
                      const p = l.split(',');
                      return (
                        p.length !== 2 ||
                        !p[0].trim() ||
                        !(categories.includes(p[1]?.trim()) || p[1]?.trim() === '공제 제외')
                      );
                    })
                  )
                    return notify('상호명,분류 형식을 확인해주세요. 분류는 5종 중 하나여야 해요.');
                  if (accountService.current()?.role !== 'ADMIN')
                    return notify('관리자 권한이 필요합니다.');
                  userService.save('admin-merchants', publicList);
                  recordAccess('MERCHANT_LIST_SAVE');
                  notify(
                    '관리 목록을 저장했어요. 이 브라우저에서 다음 업로드부터 저장한 예시 목록을 대조합니다. 기존 거래는 유지됩니다.',
                  );
                }}
              >
                <h3>공공데이터 관리 목록</h3>
                <p className="muted">
                  상호명,분류 · 목록 관리 시연용이며 실시간 공공데이터 연동 전입니다.
                </p>
                <Field label="예시 상호 목록">
                  <textarea
                    rows={9}
                    value={publicList}
                    onChange={(e) => setPublicList(e.target.value)}
                  />
                </Field>
                <Btn type="submit">목록 검증하고 저장</Btn>
              </form>
            )}
          </section>
        </>
      )}
    </>
  );
}
