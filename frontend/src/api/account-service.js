import { consentVersions } from '../config/consent-versions.js';
// 체험용 계정 어댑터입니다. TODO: 가입·로그인·권한·잠금·탈퇴는 Spring Boot와 Oracle에서 검증·저장해야 합니다.
export const LOCK_MS = 10 * 60 * 1000;
export const ACCOUNT_KEY = 'hope-accounts-v1';
export const SESSION_KEY = 'hope-session-v1';
export function newPrototypeId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((n) => n.toString(16).padStart(2, '0'))
    .join('');
}
const cleanEmail = (v) => v.trim().toLowerCase();
export function ageOn(birth, now) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birth);
  if (!match) throw Error('올바른 생년월일을 입력해주세요.');
  const y = Number(match[1]),
    m = Number(match[2]),
    d = Number(match[3]),
    date = new Date(Date.UTC(y, m - 1, d));
  if (
    y < 1900 ||
    date.getUTCFullYear() !== y ||
    date.getUTCMonth() !== m - 1 ||
    date.getUTCDate() !== d
  )
    throw Error('올바른 생년월일을 입력해주세요.');
  const korea = new Date(now.getTime() + 9 * 60 * 60 * 1000),
    cy = korea.getUTCFullYear(),
    cm = korea.getUTCMonth() + 1,
    cd = korea.getUTCDate();
  if (y > cy || (y === cy && (m > cm || (m === cm && d > cd))))
    throw Error('미래의 생년월일은 입력할 수 없습니다.');
  return cy - y - (cm < m || (cm === m && cd < d) ? 1 : 0);
}
const publicOf = ({ passwordHash, salt, ...user }) => user;
async function derive(password, salt) {
  if (!crypto.subtle)
    throw Error(
      '계정 인증 시연은 HTTPS 환경에서 이용해주세요. 현재 미리보기에서는 빠른 체험을 이용할 수 있습니다.',
    );
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(password),
    'PBKDF2',
    false,
    ['deriveBits'],
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: Uint8Array.from(salt.match(/../g).map((x) => parseInt(x, 16))),
      iterations: 120000,
      hash: 'SHA-256',
    },
    key,
    256,
  );
  return Array.from(new Uint8Array(bits))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
export function createAccountService(storage, session, clock = () => Date.now()) {
  const read = () => JSON.parse(storage.getItem(ACCOUNT_KEY) || '[]');
  const write = (users) => storage.setItem(ACCOUNT_KEY, JSON.stringify(users));
  const current = () =>
    read().find((u) => u.id === session.getItem(SESSION_KEY) && u.status !== 'WITHDRAWN');
  const must = () => {
    const u = current();
    if (!u) throw Error('로그인이 필요합니다.');
    return u;
  };
  const mustAdmin = () => {
    const u = must();
    if (u.role !== 'ADMIN') throw Error('관리자 권한이 필요합니다.');
    return u;
  };
  const usernameCheck = (v) => {
    const n = v.trim().toLowerCase();
    if (n.startsWith('withdrawn_')) throw Error('사용할 수 없는 아이디예요.');
    if (!/^[a-z0-9_]{4,50}$/.test(n)) throw Error('아이디는 영문·숫자·밑줄 4~50자로 입력해주세요.');
    return n;
  };
  const challengeKey = 'hope-email-challenge-v1';
  const challenge = () => JSON.parse(session.getItem(challengeKey) || 'null');
  const emailCheck = (email) => {
    const v = cleanEmail(email);
    if (v.length > 100 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))
      throw Error('올바른 이메일 형식을 입력해주세요.');
    return v;
  };
  async function register(input, bootstrap = false) {
    const email = emailCheck(input.email),
      username = usernameCheck(input.username),
      name = username;
    if (!['남성', '여성'].includes(input.gender)) throw Error('성별을 선택해주세요.');
    if (ageOn(input.birth, new Date(clock())) < 14)
      throw Error('본 서비스는 만 14세 이상부터 회원가입할 수 있습니다.');
    if (!input.terms || !input.privacy || !input.financial)
      throw Error('필수 이용약관·개인정보·금융 정보 저장에 모두 동의해주세요.');
    if (input.password.length < 8) throw Error('비밀번호는 8자 이상 입력해주세요.');
    if (input.password !== input.confirm) throw Error('비밀번호 확인이 일치하지 않아요.');
    if (read().some((u) => u.username === username)) throw Error('이미 사용 중인 아이디입니다.');
    if (read().some((u) => u.email === email)) throw Error('이미 사용 중인 이메일입니다.');
    if (bootstrap && read().some((u) => u.role === 'ADMIN'))
      throw Error('최초 관리자 설정이 이미 완료되었습니다.');
    const proof = challenge();
    if (
      !proof ||
      proof.email !== email ||
      !proof.verified ||
      proof.token !== input.verificationToken ||
      proof.expiresAt <= clock()
    )
      throw Error('이메일 인증을 완료해주세요. 인증은 5분 후 만료됩니다.');
    const salt = Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map((x) => x.toString(16).padStart(2, '0'))
      .join('');
    const passwordHash = await derive(input.password, salt),
      users = read();
    if (users.some((u) => u.username === username)) throw Error('이미 사용 중인 아이디입니다.');
    if (users.some((u) => u.email === email)) throw Error('이미 사용 중인 이메일입니다.');
    if (bootstrap && users.some((u) => u.role === 'ADMIN'))
      throw Error('최초 관리자 설정이 이미 완료되었습니다.');
    const u = {
      status: 'ACTIVE',
      TERMS_AGREED_AT: new Date(clock()).toISOString(),
      PRIVACY_AGREED_AT: new Date(clock()).toISOString(),
      FINANCE_AGREED_AT: new Date(clock()).toISOString(),
      TERMS_VERSION: consentVersions.TERMS_VERSION || null,
      PRIVACY_VERSION: consentVersions.PRIVACY_VERSION || null,
      FINANCE_VERSION: consentVersions.FINANCE_VERSION || null,
      id: newPrototypeId(),
      name,
      username,
      gender: input.gender,
      email,
      birth: input.birth,
      role: bootstrap ? 'ADMIN' : 'USER',
      joinedAt: new Date(clock()).toISOString(),
      passwordHash,
      salt,
      failures: 0,
      lockedUntil: 0,
      consents: {
        terms: true,
        privacy: true,
        financial: true,
        marketing: input.marketing === true,
        version: 'UNCONFIRMED_DEMO',
        at: new Date(clock()).toISOString(),
      },
    };
    write([...users, u]);
    session.removeItem(challengeKey);
    return publicOf(u);
  }
  return {
    mode: 'BROWSER_DEMO',
    current: () => {
      const u = current();
      return u ? publicOf(u) : null;
    },
    hasAdmin: () => read().some((u) => u.role === 'ADMIN'),
    checkUsername: (value) => !read().some((u) => u.username === usernameCheck(value)),
    sendEmailCode: (value) => {
      const email = emailCheck(value);
      if (read().some((u) => u.email === email)) throw Error('이미 사용 중인 이메일입니다.');
      const bytes = crypto.getRandomValues(new Uint32Array(1));
      const code = String(bytes[0] % 1000000).padStart(6, '0'),
        expiresAt = clock() + 5 * 60 * 1000;
      session.setItem(
        challengeKey,
        JSON.stringify({
          email,
          code,
          expiresAt,
          verified: false,
          attempts: 0,
          token: newPrototypeId(),
        }),
      );
      return { demoCode: code, expiresAt };
    },
    verifyEmailCode: (value, code) => {
      const c = challenge();
      if (!c || c.email !== emailCheck(value)) throw Error('인증번호를 먼저 요청해주세요.');
      if (c.expiresAt <= clock()) throw Error('인증번호가 만료되었습니다. 다시 발송해주세요.');
      if (c.attempts >= 5) throw Error('인증번호 확인 5회 실패: 다시 발송해주세요.');
      if (c.code !== code.trim()) {
        c.attempts++;
        session.setItem(challengeKey, JSON.stringify(c));
        throw Error('인증번호가 일치하지 않습니다.');
      }
      c.verified = true;
      session.setItem(challengeKey, JSON.stringify(c));
      return c.token;
    },
    checkEmail: (email) => !read().some((u) => u.email === emailCheck(email)),
    signUp: (input) => register(input, false),
    bootstrap: (input) => register(input, true),
    async login(email, password) {
      const users = read(),
        u = users.find(
          (a) => a.email === cleanEmail(email) || a.username === email.trim().toLowerCase(),
        );
      if (!u) throw Error('이메일 또는 비밀번호를 확인해주세요.');
      if (u.status === 'WITHDRAWN') throw Error('탈퇴한 계정이에요.');
      if (u.lockedUntil > clock())
        throw Error(
          `5회 로그인 실패로 잠겼습니다. ${Math.ceil((u.lockedUntil - clock()) / 1000)}초 후 다시 시도해주세요.`,
        );
      if (u.lockedUntil) {
        u.lockedUntil = 0;
        u.failures = 0;
      }
      const hash = await derive(password, u.salt);
      if (hash !== u.passwordHash) {
        u.failures++;
        if (u.failures >= 5) {
          u.lockedUntil = clock() + LOCK_MS;
          u.failures = 0;
        }
        write(users);
        throw Error(
          u.lockedUntil
            ? '5회 로그인 실패로 10분 동안 로그인이 제한됩니다.'
            : `이메일 또는 비밀번호를 확인해주세요. (${u.failures}/5회)`,
        );
      }
      u.failures = 0;
      u.lockedUntil = 0;
      write(users);
      session.setItem(SESSION_KEY, u.id);
      return publicOf(u);
    },
    logout: () => session.removeItem(SESSION_KEY),
    members: (name = '') => {
      mustAdmin();
      return read()
        .filter((u) =>
          [u.username || u.name, u.email, u.status || 'ACTIVE'].some((v) =>
            v.toLowerCase().includes(name.trim().toLowerCase()),
          ),
        )
        .map(publicOf);
    },
    setRole: (id, role) => {
      const actor = mustAdmin();
      if (role !== 'ADMIN' && role !== 'USER') throw Error('올바른 권한이 아닙니다.');
      const users = read(),
        u = users.find((a) => a.id === id);
      if (!u) throw Error('회원을 찾을 수 없습니다.');
      if (
        u.role === 'ADMIN' &&
        role === 'USER' &&
        users.filter((a) => a.role === 'ADMIN').length <= 1
      )
        throw Error('마지막 관리자 권한은 해제할 수 없습니다.');
      if (u.status === 'WITHDRAWN') throw Error('탈퇴한 계정의 권한은 변경할 수 없습니다.');
      if (role === 'USER' && u.role === 'ADMIN' && u.id === actor.id)
        throw Error('관리자 본인의 권한은 해제할 수 없습니다.');
      if (role === 'USER' && !['남성', '여성', 'M', 'F'].includes(u.gender || ''))
        throw Error('성별이 없는 관리자는 일반 회원으로 바꿀 수 없습니다.');
      u.role = role;
      write(users);
      return publicOf(u);
    },
    updateProfile: (gender, _email) => {
      const self = must();
      if (!['남성', '여성'].includes(gender)) throw Error('성별을 선택해주세요.');
      const users = read(),
        u = users.find((a) => a.id === self.id);
      u.gender = gender;
      write(users);
      return publicOf(u);
    },
    async changePassword(old, next, confirm) {
      const u = must();
      if (u.lockedUntil > clock()) throw Error('잠금 해제 후 다시 시도해주세요.');
      if ((await derive(old, u.salt)) !== u.passwordHash)
        throw Error('현재 비밀번호를 확인해주세요.');
      if (next.length < 8 || next !== confirm)
        throw Error('새 비밀번호는 8자 이상이며 확인 값과 같아야 합니다.');
      const hash = await derive(next, u.salt),
        users = read();
      const fresh = users.find((a) => a.id === u.id);
      fresh.passwordHash = hash;
      fresh.failures = 0;
      fresh.lockedUntil = 0;
      write(users);
    },
    async withdraw(password) {
      const u = must();
      if (u.lockedUntil > clock()) throw Error('잠금 해제 후 다시 시도해주세요.');
      if ((await derive(password, u.salt)) !== u.passwordHash)
        throw Error('현재 비밀번호를 확인해주세요.');
      const users = read(),
        fresh = users.find((a) => a.id === u.id);
      if (!fresh) throw Error('회원을 찾을 수 없습니다.');
      if (fresh.role === 'ADMIN' && users.filter((a) => a.role === 'ADMIN').length <= 1)
        throw Error(
          '마지막 관리자 계정은 탈퇴할 수 없습니다. 다른 관리자에게 먼저 권한을 부여해주세요.',
        );
      fresh.status = 'WITHDRAWN';
      fresh.withdrawnAt = new Date(clock()).toISOString();
      fresh.role = 'USER';
      write(users);
      session.removeItem(SESSION_KEY);
    },
  };
}
export const DEMO_MODE_KEY = 'hope-demo-mode-v1';
export function demoStorage(storage) {
  return {
    getItem: (k) => storage.getItem(k === ACCOUNT_KEY ? 'hope-demo-accounts-v1' : k),
    setItem: (k, v) => storage.setItem(k === ACCOUNT_KEY ? 'hope-demo-accounts-v1' : k, v),
    removeItem: (k) => storage.removeItem(k === ACCOUNT_KEY ? 'hope-demo-accounts-v1' : k),
    get length() {
      return storage.length;
    },
    key: (i) => storage.key(i),
  };
}
export function enterDemoSession(storage, session, role) {
  const demo = demoStorage(storage);
  let users = JSON.parse(demo.getItem(ACCOUNT_KEY) || '[]');
  if (!users.some((u) => u.role === 'ADMIN') || !users.some((u) => u.role === 'USER')) {
    users = ['ADMIN', 'USER', 'USER'].map((r, i) => ({
      id: 'demo-member-' + i,
      name: i === 0 ? '체험 관리자' : `체험사용자${i}`,
      username: `demo${i}`,
      gender: i === 0 ? '' : i === 1 ? '여성' : '남성',
      status: 'ACTIVE',
      email: `demo${i}@example.test`,
      birth: '1999-05-20',
      role: r,
      joinedAt: new Date().toISOString(),
      passwordHash: 'DEMO_BUTTON_ONLY',
      salt: '',
      failures: 0,
      lockedUntil: 0,
      consents: {
        terms: false,
        privacy: false,
        marketing: false,
        version: 'demo-fixture',
        at: new Date().toISOString(),
      },
    }));
    demo.setItem(ACCOUNT_KEY, JSON.stringify(users));
  }
  users = users.map((u, i) => ({
    ...u,
    name: i === 0 ? '체험 관리자' : `체험사용자${i}`,
    username: u.username || `demo${i}`,
    gender: u.gender || (u.role === 'USER' ? (i === 1 ? '여성' : '남성') : ''),
    status: u.status || 'ACTIVE',
  }));
  demo.setItem(ACCOUNT_KEY, JSON.stringify(users));
  const user = users.find((u) => u.role === role && u.status !== 'WITHDRAWN');
  session.setItem(DEMO_MODE_KEY, '1');
  session.setItem(SESSION_KEY, user.id);
  return publicOf(user);
}
function normalAdapter() {
  return createAccountService(localStorage, sessionStorage);
}
function browserAdapter() {
  return createAccountService(
    sessionStorage.getItem(DEMO_MODE_KEY) ? demoStorage(localStorage) : localStorage,
    sessionStorage,
  );
}
export const accountService = {
  current: () => (typeof window === 'undefined' ? null : browserAdapter().current()),
  hasAdmin: () => normalAdapter().hasAdmin(),
  enterDemo: (role) => enterDemoSession(localStorage, sessionStorage, role),
  isDemo: () => typeof window !== 'undefined' && !!sessionStorage.getItem(DEMO_MODE_KEY),
  checkUsername: (value) => normalAdapter().checkUsername(value),
  sendEmailCode: (value) => normalAdapter().sendEmailCode(value),
  verifyEmailCode: (email, code) => normalAdapter().verifyEmailCode(email, code),
  checkEmail: (email) => normalAdapter().checkEmail(email),
  signUp: (d) => normalAdapter().signUp(d),
  bootstrap: (d) => normalAdapter().bootstrap(d),
  login: async (email, password) => {
    const user = await normalAdapter().login(email, password);
    sessionStorage.removeItem(DEMO_MODE_KEY);
    return user;
  },
  logout: () => {
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(DEMO_MODE_KEY);
  },
  members: (name = '') => browserAdapter().members(name),
  setRole: (id, role) => browserAdapter().setRole(id, role),
  updateProfile: (gender) => browserAdapter().updateProfile(gender),
  changePassword: (a, b, c) => {
    if (sessionStorage.getItem(DEMO_MODE_KEY))
      throw Error('빠른 체험 계정에는 비밀번호가 없습니다. 가입한 계정으로 로그인해주세요.');
    return browserAdapter().changePassword(a, b, c);
  },
  withdraw: (password) => {
    if (sessionStorage.getItem(DEMO_MODE_KEY))
      throw Error('빠른 체험 계정입니다. 로그아웃으로 체험을 종료해주세요.');
    return browserAdapter().withdraw(password);
  },
};
