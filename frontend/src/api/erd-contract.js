// Oracle 연결은 Spring Boot에서 수행합니다. 여기서는 확인된 v3.8 경계만 구성합니다.
import { categoryCodes } from './services.js';
import { payCode } from './expense-service.js';
import { getTaxYear } from '../utils/tax-year.js';
import { requireConsentVersions } from '../config/consent-versions.js';
const yesNo = (value) =>
  ['예', '해당'].includes(value) ? 'Y' : ['아니요', '미해당'].includes(value) ? 'N' : null;
export function memberProfileDTO(gender) {
  if (!['남성', '여성'].includes(gender)) throw Error('성별 필수');
  return { GENDER: gender === '남성' ? 'M' : 'F' };
}
export function qualificationDTO(d) {
  return {
    MILITARY_MONTHS: d.militaryMonths ?? 0,
    HIRE_DATE: d.employed || null,
    COMPANY_SIZE: { 중소기업: 'SME', 중견기업: 'MID', 대기업: 'LARGE' }[d.companySize] ?? null,
    HOMELESS_HEAD_YN: yesNo(d.headOfHousehold),
  };
}
export function incomeDTO(d) {
  // null은 미선택입니다. 운영 저장 전 백엔드가 누락 여부와 스키마 제약을 검증해야 합니다.
  return {
    TAX_YEAR: getTaxYear(d),
    TOTAL_SALARY: d.salary,
    WITHHELD_TAX: d.paid,
    DEPENDENTS: d.family,
    CHILDREN: d.children ?? 0,
    MONTHLY_RENT: d.rent,
    HOUSING_SAVING: d.housingSaving ?? 0,
    PENSION_SAVING: (d.pensionSaving ?? 0) + (d.irp ?? 0),
    SME_REDUCTION_YN: yesNo(d.sme),
    DATA_ORIGIN: 'INPUT',
  };
}
// 프론트 입력 필드입니다. v3.9 컬럼명·필수값을 확인한 후 서버에서 매핑해야 합니다.
export function insuranceInput(d) {
  return {
    nationalPension: d.nationalPension ?? 0,
    healthEmploymentInsurance: d.healthEmploymentInsurance ?? 0,
  };
}
export function expenseDTO(row, categoryIdByCode = {}, uploadIdByClientId = {}) {
  const method = payCode(row.paymentMethod) || row.PAY_METHOD;
  if (!['CREDIT', 'CHECK', 'CASH'].includes(method))
    throw Error('결제수단 확인이 필요합니다. 저장 요청을 중단합니다.');
  if (!row.uploadId) throw Error('업로드 파일 연결이 필요합니다.');
  const uploadId =
    uploadIdByClientId[row.uploadId] ?? (Number.isInteger(row.uploadId) ? row.uploadId : null);
  if (!Number.isInteger(uploadId) || uploadId <= 0)
    throw Error('서버가 발급한 UPLOAD_ID 매핑이 필요합니다.');
  const code = row.CATEGORY_CODE || categoryCodes[row.category];
  const id = categoryIdByCode[code];
  if (!Number.isInteger(id) || id <= 0) throw Error('서버가 조회한 CATEGORY_ID 매핑이 필요합니다.');
  // MEMBER_ID 및 UPLOAD_ID 소유권은 인증 세션에서 서버가 검사합니다. 브라우저 회원번호는 보내지 않습니다.
  return {
    USED_DATE: row.date,
    MERCHANT_NAME: row.merchant,
    AMOUNT: row.amount,
    PAY_METHOD: method,
    CATEGORY_ID: id,
    LIST_ID: null, // 예시 상호명 목록의 번호를 실제 DB 외래키로 전송하지 않습니다.
    UPLOAD_ID: uploadId,
  };
}
export function consentDTO(user) {
  const versions = requireConsentVersions(user);
  for (const key of ['TERMS_AGREED_AT', 'PRIVACY_AGREED_AT', 'FINANCE_AGREED_AT']) {
    if (!user[key] || !Number.isFinite(Date.parse(user[key])))
      throw Error('동의 시각을 확인해주세요.');
  }
  // 최종 동의 시각과 버전은 백엔드가 발행·검증합니다. 이 DTO의 클라이언트 시간을 신뢰하지 않습니다.
  return {
    TERMS_AGREED_AT: user.TERMS_AGREED_AT,
    PRIVACY_AGREED_AT: user.PRIVACY_AGREED_AT,
    FINANCE_AGREED_AT: user.FINANCE_AGREED_AT,
    ...versions,
  };
}
