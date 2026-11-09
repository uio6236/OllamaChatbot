// 한국 시간의 계산 기준일로 기본 귀속 연도를 선택하는 서비스 정책입니다.
// 세법의 모든 신고 일정을 정의하는 규칙이 아닙니다. 선택한 연도는 입력·계산·비교에 함께 전달합니다.
export function getDefaultTaxYear(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'numeric',
  }).formatToParts(date);
  const year = Number(parts.find((p) => p.type === 'year').value);
  const month = Number(parts.find((p) => p.type === 'month').value);
  return month <= 3 ? year - 1 : year;
}
export const getTaxYear = (data) =>
  Number.isInteger(data?.taxYear) ? data.taxYear : getDefaultTaxYear();
