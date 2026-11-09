// 기존 회원정보 조회·성별 수정 폼입니다. 변경 허용 항목은 서비스에서 제한합니다.
import React, { useState } from 'react';
import { accountService } from '@/api/account-service.js';
export function ProfileDetails({ data, onChange }) {
  const [gender, setGender] = useState(data.gender),
    [error, setError] = useState('');
  const u = accountService.current();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        try {
          onChange(accountService.updateProfile(gender));
          setError('변경했습니다.');
        } catch (e) {
          setError(e.message);
        }
      }}
    >
      <h3>회원정보 조회·수정</h3>
      <p>
        실명은 수집하지 않습니다. 아이디·생년월일·이메일은 직접 변경할 수 없으며 권한·계정 상태는
        수정 대상이 아닙니다.
      </p>
      <div className="form-grid">
        <label className="field">
          아이디
          <input readOnly value={u?.username || u?.name || '비로그인 체험'} />
        </label>
        <label className="field">
          생년월일
          <input readOnly value={u?.birth || data.birth} />
        </label>
        <label className="field">
          이메일
          <input
            readOnly
            value={(u?.email || data.email).replace(/^(.{1,2}).*(@.*)$/, '$1***$2')}
          />
        </label>
        <label className="field">
          성별
          <select required value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="">선택해주세요</option>
            <option>남성</option>
            <option>여성</option>
          </select>
        </label>
      </div>
      <button className="btn">성별 저장 (시연)</button>
      <p role="status">{error}</p>
    </form>
  );
}
