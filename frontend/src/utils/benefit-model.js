// 입력 기반 예비 점검입니다. 실제 연령·급여·주택·기업 요건 및 증빙은 계산/진단 서버에서 확인합니다.
export function benefitChecks(data) {
  const no = (v) => ['아니요', '미해당'].includes(v);
  const yes = (v) => ['예', '해당'].includes(v);
  const entry = (name, negative, entered, reason, requirements) => ({
    name,
    status: negative ? '비해당' : entered ? '해당' : '확인 필요',
    reason,
    requirements,
  });
  return [
    entry(
      '중소기업 취업자 감면',
      no(data.sme),
      yes(data.sme),
      no(data.sme)
        ? '신청 여부를 아니요로 입력했습니다.'
        : yes(data.sme)
          ? '신청 여부를 예로 입력했습니다. 자가 입력 기준이며 법정 자격은 확인 전입니다.'
          : '감면 신청 여부를 선택해주세요.',
      '취업 당시 연령·병역·취업일·기업 업종/규모·신청서·감면 기간 확인',
    ),
    entry(
      '월세 세액공제',
      data.housing === '주택 보유',
      false,
      data.housing === '주택 보유'
        ? '주택 보유로 입력했습니다.'
        : data.headOfHousehold === '확인 필요'
          ? '세대 및 주택 정보를 확인해주세요.'
          : data.rent <= 0
            ? '월세 월 납부액과 납부 증빙을 확인해주세요.'
            : '월 납부액은 입력되었습니다. 실제 공제 요건은 확인 전입니다.',
      '무주택·급여·세대 요건·주택·임대차 계약·실제 납부 기간 및 지급 증빙 확인',
    ),
    entry(
      '주택청약 소득공제',
      no(data.headOfHousehold) || data.housing === '주택 보유',
      false,
      no(data.headOfHousehold) || data.housing === '주택 보유'
        ? '자가 입력 기준 무주택 세대주 요건에 해당하지 않습니다.'
        : data.headOfHousehold !== '예'
          ? '무주택 세대주 여부를 선택해주세요.'
          : '청약 납입액·급여·무주택 확인서 등 증빙을 확인해주세요.',
      '무주택 세대주·해당 연도 급여 기준·청약 납입액·한도·증빙 확인',
    ),
  ];
}
