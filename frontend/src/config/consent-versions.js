// TODO: 팀에서 확정한 동의서 버전을 환경변수에 입력합니다. 임의의 운영 버전은 만들지 않습니다.
const env = import.meta.env || {};
export const consentVersions = {
  TERMS_VERSION: env.VITE_TERMS_VERSION || '',
  PRIVACY_VERSION: env.VITE_PRIVACY_VERSION || '',
  FINANCE_VERSION: env.VITE_FINANCE_VERSION || '',
};
export function requireConsentVersions(values) {
  for (const key of Object.keys(consentVersions)) {
    if (
      typeof values[key] !== 'string' ||
      !values[key].trim() ||
      values[key] === 'UNCONFIRMED_DEMO'
    ) {
      throw Error(`${key}: 팀에서 확정한 동의서 버전이 필요합니다. 서버 저장 요청을 중단합니다.`);
    }
  }
  return Object.fromEntries(Object.keys(consentVersions).map((key) => [key, values[key].trim()]));
}
