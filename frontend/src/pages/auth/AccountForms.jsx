// 가입·로그인·이메일 인증·빠른 체험 UI입니다. TODO: 실제 인증은 Spring Boot API에서 재검증해야 합니다.
import React, { useState, useEffect } from 'react';
import { accountService } from '@/api/account-service.js';
import { recordAccess } from '@/api/prototype-records.js';
// 동의서 버전은 별도 설정합니다. 미확정 버전의 서버 DTO는 생성할 수 없습니다.
const notice =
  '브라우저 내 기능 시연입니다. 계정·권한·잠금 정보는 이 브라우저에만 저장되며 서버 보안 기능은 아직 연결되지 않았습니다. 동의서 운영 버전 미확정 시 로컬 체험만 제공하며 서버에 동의를 저장하지 않습니다. 실제 사용하는 비밀번호·개인정보는 입력하지 마세요.';
const agreements = [
  [
    'terms',
    '[필수] 서비스 이용약관 동의',
    '희망환급은 소득·지출 입력, 예상 결과 조회, 시뮬레이션 및 안내를 제공합니다. 만 14세 이상 가입할 수 있으며 관리자는 기존 계정에 권한을 부여합니다. 본인에게 사용 권한이 있는 자료만 등록해야 합니다. 계산·분류·AI는 시연이며 실제 신고·자격 확정·세무 자문이 아닙니다. 마이페이지에서 탈퇴할 수 있으며 마지막 관리자는 인계가 필요합니다. 운영 주체·시행일·분쟁 처리 등은 서비스 정책 확정 전 보완해야 합니다.',
  ],
  [
    'privacy',
    '[필수] 개인정보 수집·이용 동의',
    '목적: 계정 식별, 로그인, 연령 확인, 그룹 비교 및 서비스 지원. 항목: 아이디, 이메일, 비밀번호 파생 해시, 생년월일, 성별, 동의 이력. 보유기간·보존 정책은 운영 검토가 필요합니다. 탈퇴 후 30일 유예기간 동안 아이디·이메일을 유지하고 이후 식별 정보 처리 예정입니다. 현재 브라우저에만 저장하며 외부 서버로 계정 정보를 보내지 않습니다. 주민등록번호 전체는 수집하지 않습니다. 필수 동의 거부 시 가입할 수 없습니다. 운영 주체·문의처·법적 보존 대상 및 기간·위탁 정책은 확정 전입니다.',
  ],
  [
    'financial',
    '[필수] 금융 정보 저장 동의',
    '목적: 연말정산 예상 계산, 거래 자동 분류, 결과 조회 및 시뮬레이션. 저장 항목: 사용자가 제출한 급여·기납부세액·결제수단별 지출액, 거래일·상호명·금액·결제수단, 파일 처리 메타정보, 가족 수·월세·주거 및 감면 자격 입력, 계산·시뮬레이션 기록. 원본 CSV·XLSX 파일 자체와 카드번호 전체·계좌 비밀번호는 저장하지 않습니다. 탈퇴 요청 시 즉시 삭제하지 않으며 30일 유예 및 이후 식별 정보 처리 정책은 운영 검토가 필요합니다. 업로드 파일별 삭제도 가능합니다. 거부 시 가입할 수 없습니다. 실제 금융기관·국세청 조회나 운영 서버 저장은 연결되지 않았습니다.',
  ],
  [
    'marketing',
    '[선택] 마케팅 정보 수신 동의',
    '혜택 및 서비스 소식 안내를 위해 이메일과 동의 이력을 사용합니다. 동의 철회 또는 탈퇴 시까지 보유합니다. 거부해도 가입·서비스 이용에 영향이 없습니다. 메일 발송은 미연동입니다.',
  ],
];
export function AccountForms({ page, go, onLogin }) {
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [setup, setSetup] = useState(false),
    [hasAdmin, setHasAdmin] = useState(() => accountService.hasAdmin());
  const [email, setEmail] = useState(''),
    [username, setUsername] = useState(''),
    [checkedEmail, setCheckedEmail] = useState(''),
    [checkedUsername, setCheckedUsername] = useState(''),
    [gender, setGender] = useState('');
  const [password, setPassword] = useState(''),
    [confirm, setConfirm] = useState('');
  const [code, setCode] = useState(''),
    [demoCode, setDemoCode] = useState(''),
    [expiresAt, setExpiresAt] = useState(0),
    [now, setNow] = useState(Date.now()),
    [proof, setProof] = useState(''),
    [verificationMessage, setVerificationMessage] = useState('');
  const [consent, setConsent] = useState({
    terms: false,
    privacy: false,
    marketing: false,
    financial: false,
  });
  const signup = page === 'signup' || setup;
  useEffect(() => {
    if (!expiresAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);
  const expired = expiresAt > 0 && now >= expiresAt;
  const check = (kind) => {
    try {
      const available =
        kind === 'username'
          ? accountService.checkUsername(username)
          : accountService.checkEmail(email);
      if (!available)
        throw Error(`이미 사용 중인 ${kind === 'username' ? '아이디' : '이메일'}입니다.`);
      if (kind === 'username') setCheckedUsername(username);
      else setCheckedEmail(email);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <section className="card auth-card" key={page}>
      <span className="tag amber">브라우저 시연 · 서버 미연동</span>
      <h2>
        {setup
          ? '최초 관리자 초기 설정'
          : signup
            ? '희망환급 회원가입'
            : page === 'reset'
              ? '비밀번호 재설정'
              : '다시 만나 반가워요'}
      </h2>
      <p className="muted">{notice}</p>
      {setup && (
        <p className="notice amber">
          이 브라우저에 관리자 계정이 없을 때 최초 1회 설정합니다. 운영 서버의 비공개 초기 설정은
          별도 구현이 필요합니다.
        </p>
      )}
      <form
        noValidate
        onSubmit={async (e) => {
          e.preventDefault();
          setError('');
          setBusy(true);
          try {
            const f = new FormData(e.currentTarget);
            if (page === 'reset' && !setup) {
              setError('이메일 재설정 API는 미연동입니다. 메일이 발송되지 않았습니다.');
              return;
            }
            if (signup) {
              if (checkedUsername !== username || !username)
                throw Error('아이디 중복확인을 해주세요.');
              if (checkedEmail !== email || !email) throw Error('이메일 중복확인을 해주세요.');
              if (!proof || expired)
                throw Error('이메일 인증을 완료해주세요. 만료된 경우 다시 인증해주세요.');
              const payload = {
                username,
                gender,
                verificationToken: proof,
                email,
                birth: String(f.get('birth') || ''),
                password,
                confirm,
                ...consent,
              };
              await (setup ? accountService.bootstrap(payload) : accountService.signUp(payload));
              setHasAdmin(accountService.hasAdmin());
              setSetup(false);
              setConsent({ terms: false, privacy: false, marketing: false, financial: false });
              setProof('');
              setPassword('');
              setConfirm('');
              go('login');
              setError('계정이 이 브라우저에 등록되었습니다. 아이디 또는 이메일로 로그인해주세요.');
            } else {
              const u = await accountService.login(email, password);
              recordAccess('LOGIN');
              onLogin(u);
            }
          } catch (err) {
            if (!signup) recordAccess('LOGIN', 'FAIL');
            setError(err.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {signup && (
          <div className="field">
            <label htmlFor="signup-id">아이디 *</label>
            <div className="input-action">
              <input
                id="signup-id"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  setCheckedUsername('');
                }}
                placeholder="영문·숫자·밑줄 4~50자"
                autoComplete="username"
              />
              <button className="btn secondary" type="button" onClick={() => check('username')}>
                중복확인
              </button>
            </div>
            {checkedUsername === username && username && (
              <small role="status">사용 가능한 아이디입니다.</small>
            )}
          </div>
        )}
        {signup && (
          <label className="field">
            <span>비밀번호 *</span>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              minLength={8}
              required
              autoComplete={signup ? 'new-password' : 'current-password'}
              placeholder="시연용 비밀번호 8자 이상"
            />
          </label>
        )}
        {signup && (
          <label className="field">
            <span>비밀번호 확인 *</span>
            <input
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              type="password"
              required
              autoComplete="new-password"
            />
            {confirm && (
              <small role="status">
                {password === confirm ? '비밀번호가 일치합니다.' : '비밀번호가 일치하지 않습니다.'}
              </small>
            )}
          </label>
        )}
        <div className="field">
          <label htmlFor="account-email">
            {signup || page === 'reset' ? '이메일 *' : '아이디 또는 이메일 *'}
          </label>
          <div className="input-action">
            <input
              id="account-email"
              name="email"
              type={signup || page === 'reset' ? 'email' : 'text'}
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setCheckedEmail('');
                setProof('');
                setDemoCode('');
                setExpiresAt(0);
                setVerificationMessage('');
              }}
              autoComplete="off"
            />
            {signup && (
              <button className="btn secondary" type="button" onClick={() => check('email')}>
                중복확인
              </button>
            )}
          </div>
          {signup && checkedEmail === email && email && (
            <small role="status">사용 가능한 이메일입니다.</small>
          )}
        </div>{' '}
        {!signup && page !== 'reset' && (
          <label className="field">
            <span>비밀번호 *</span>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              minLength={8}
              required
              autoComplete={signup ? 'new-password' : 'current-password'}
              placeholder="시연용 비밀번호 8자 이상"
            />
          </label>
        )}
        {signup && (
          <>
            <div className="email-verification">
              <h3>이메일 인증 · 체험</h3>
              <p>
                이메일 발송 API가 연결되지 않아 실제 메일은 보내지 않습니다. 아래에 표시되는 체험
                인증번호로 동작을 확인하세요.
              </p>
              <button
                className="btn secondary"
                type="button"
                onClick={() => {
                  try {
                    if (checkedEmail !== email || !email)
                      throw Error('이메일 중복확인을 먼저 해주세요.');
                    const result = accountService.sendEmailCode(email);
                    setDemoCode(result.demoCode);
                    setExpiresAt(result.expiresAt);
                    setNow(Date.now());
                    setProof('');
                    setCode('');
                    setVerificationMessage(
                      '체험 인증번호를 생성했습니다. 실제 이메일은 발송되지 않았습니다.',
                    );
                  } catch (err) {
                    setVerificationMessage(err.message);
                  }
                }}
              >
                인증번호 발송 (체험)
              </button>
              {demoCode && (
                <p>
                  체험 인증번호: <b>{demoCode}</b> ·{' '}
                  {expired
                    ? '만료됨'
                    : `${Math.max(0, Math.ceil((expiresAt - now) / 1000))}초 남음`}
                </p>
              )}
              <div className="input-action">
                <input
                  aria-label="인증번호"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="6자리 인증번호"
                />
                <button
                  className="btn secondary"
                  type="button"
                  onClick={() => {
                    try {
                      setProof(accountService.verifyEmailCode(email, code));
                      setVerificationMessage('인증 성공 (브라우저 체험)');
                    } catch (err) {
                      setProof('');
                      setVerificationMessage(err.message);
                    }
                  }}
                >
                  인증확인
                </button>
              </div>
              <p role="status">
                {expired ? '인증번호가 만료되었습니다. 다시 발송해주세요.' : verificationMessage}
              </p>
            </div>
            <label className="field">
              <span>생년월일 * · 만 14세 이상</span>
              <input type="date" name="birth" required />
              <small>주민등록번호 전체는 수집하지 않습니다.</small>
            </label>
            <fieldset className="gender-choice">
              <legend>성별 *</legend>
              {['남성', '여성'].map((g) => (
                <button
                  key={g}
                  type="button"
                  aria-pressed={gender === g}
                  className={'btn ' + (gender === g ? '' : 'secondary')}
                  onClick={() => setGender(g)}
                >
                  {g}
                </button>
              ))}
            </fieldset>
            <div className="agreement-list">
              <p>
                아래 내용은 검토용 초안입니다. 이용약관·개인정보·금융 동의 버전은 각각 미확정이며,
                시연 동의일시만 따로 보관합니다. 운영 전 전문과 버전 확정이 필요합니다.
              </p>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={Object.values(consent).every(Boolean)}
                  onChange={(e) =>
                    setConsent({
                      terms: e.target.checked,
                      privacy: e.target.checked,
                      marketing: e.target.checked,
                      financial: e.target.checked,
                    })
                  }
                />
                전체 동의 (선택 포함)
              </label>
              {agreements.map(([key, label, text]) => (
                <div key={key}>
                  <label className="checkline">
                    <input
                      type="checkbox"
                      checked={consent[key]}
                      onChange={(e) => setConsent({ ...consent, [key]: e.target.checked })}
                    />
                    {label}
                  </label>
                  <details>
                    <summary>동의문 초안 보기 · 내용·버전 확인 필요</summary>
                    <p>{text}</p>
                  </details>
                </div>
              ))}
            </div>
          </>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button disabled={busy} className="btn" type="submit">
          {busy
            ? '처리 중…'
            : setup
              ? '최초 관리자 만들기 (시연)'
              : signup
                ? '동의하고 회원가입'
                : page === 'reset'
                  ? '재설정 요청'
                  : '로그인'}
        </button>
      </form>
      {!signup && page === 'login' && (
        <>
          <button className="text-btn" onClick={() => go('reset')}>
            비밀번호를 잊으셨나요?
          </button>
          {!hasAdmin && (
            <button
              className="btn secondary"
              onClick={() => {
                setSetup(true);
                setError('');
              }}
            >
              최초 관리자 초기 설정 (시연)
            </button>
          )}
        </>
      )}
      {!signup && page === 'login' && (
        <div className="quick-demo">
          <div className="divider">로그인 없이 바로 체험해보세요</div>
          <p className="muted">
            별도 체험 데이터로 시작하며 가입한 회원 계정에는 영향을 주지 않습니다.
          </p>
          <button
            type="button"
            className="btn secondary"
            onClick={() => onLogin(accountService.enterDemo('USER'))}
          >
            일반 사용자 체험
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => onLogin(accountService.enterDemo('ADMIN'))}
          >
            관리자 기능 체험
          </button>
        </div>
      )}
      <p className="auth-switch">
        {signup ? '이미 계정이 있으신가요?' : '아직 회원이 아니신가요?'}{' '}
        <button
          onClick={() => {
            setSetup(false);
            setError('');
            go(signup ? 'login' : 'signup');
          }}
        >
          {signup ? '로그인' : '일반 회원가입'}
        </button>
      </p>
    </section>
  );
}
export function MemberManagement({ onChange }) {
  const [name, setName] = useState(''),
    [rev, setRev] = useState(0),
    [message, setMessage] = useState('');
  let users = [];
  try {
    users = accountService.members(name);
  } catch {
    return <p role="alert">관리자 권한이 필요합니다.</p>;
  }
  return (
    <>
      <h3>회원 관리</h3>
      <p className="muted">
        {accountService.isDemo()
          ? '빠른 체험용 회원 목록입니다. 권한 변경은 체험 데이터에만 반영됩니다.'
          : '이 브라우저에서 가입한 계정의 권한만 변경하는 시연입니다.'}
      </p>
      <label className="field">
        <span>아이디·이메일·계정 상태 검색 · 부분 일치</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="아이디, 이메일 또는 ACTIVE / WITHDRAWN"
        />
      </label>
      <p>{users.length}명</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>아이디</th>
              <th>이메일</th>
              <th>가입일</th>
              <th>계정 상태</th>
              <th>현재 권한</th>
              <th>권한 관리</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username || u.name}</td>
                <td>{u.email.replace(/^(.{1,2}).*(@.*)$/, '$1***$2')}</td>
                <td>{new Date(u.joinedAt).toLocaleDateString('ko-KR')}</td>
                <td>{u.status || 'ACTIVE'}</td>
                <td>
                  <span className={'tag ' + (u.role === 'ADMIN' ? 'blue' : 'gray')}>{u.role}</span>
                </td>
                <td>
                  <button
                    className="text-btn"
                    onClick={() => {
                      if (
                        !window.confirm(
                          `${u.name} (${u.email}) 회원의 관리자 권한을 ${u.role === 'ADMIN' ? '해제' : '부여'}하시겠습니까? (브라우저 시연)`,
                        )
                      )
                        return;
                      try {
                        accountService.setRole(u.id, u.role === 'ADMIN' ? 'USER' : 'ADMIN');
                        recordAccess('MEMBER_ROLE_CHANGE');
                        setMessage('권한을 변경했습니다.');
                        setRev(rev + 1);
                        onChange();
                      } catch (err) {
                        recordAccess('MEMBER_ROLE_CHANGE', 'FAIL');
                        setMessage(err.message);
                      }
                    }}
                  >
                    {u.role === 'ADMIN' ? '관리자 권한 해제' : '관리자 권한 부여'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!users.length && <p>검색 결과가 없습니다.</p>}
      {message && <p role="status">{message}</p>}
    </>
  );
}
export function WithdrawAccount({ onDone }) {
  const [open, setOpen] = useState(false),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  return (
    <>
      <h3>회원 탈퇴</h3>
      <p className="muted">
        탈퇴 요청 시 계정 상태가 WITHDRAWN으로 변경되고 즉시 로그아웃되며 다시 로그인할 수 없습니다.
        아이디·이메일은 30일 유예기간 동안 유지됩니다. 30일 경과 후 식별 정보를 식별 불가하게
        처리하는 작업과 데이터 활용·보존 정책은 백엔드에서 구현·검토해야 합니다. 문의·접근 기록은
        보존 대상입니다. 현재 브라우저 시연은 자동 정리 작업을 수행하지 않습니다.
      </p>
      <button className="btn secondary danger" onClick={() => setOpen(!open)}>
        회원 탈퇴
      </button>
      {open && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setError('');
            const f = new FormData(e.currentTarget);
            if (f.get('confirm') !== 'on') {
              setError('탈퇴 및 30일 유예 안내를 확인해주세요.');
              return;
            }
            if (
              !window.confirm(
                '계정을 탈퇴 상태로 전환하고 로그아웃하시겠습니까? 30일 후 자동 처리는 서버 미연동입니다.',
              )
            )
              return;
            setBusy(true);
            try {
              await accountService.withdraw(String(f.get('password') || ''));
              onDone();
            } catch (err) {
              setError(err.message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>마지막 관리자는 다른 관리자에게 권한을 부여한 후 탈퇴할 수 있습니다.</p>
          <label className="field">
            <span>현재 비밀번호 재확인</span>
            <input type="password" name="password" required />
          </label>
          <label className="checkline">
            <input type="checkbox" name="confirm" required />
            로그인 차단·30일 유예·이후 식별 정보 처리 예정 안내를 확인했습니다.
          </label>
          <button className="btn danger" disabled={busy}>
            {busy ? '탈퇴 처리 중…' : '재확인하고 탈퇴하기'}
          </button>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </form>
      )}
    </>
  );
}
