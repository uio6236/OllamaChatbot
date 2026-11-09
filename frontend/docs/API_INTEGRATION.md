# Spring Boot · MyBatis · Oracle · Gemma3 연결 안내

이 문서는 구현할 위치를 설명합니다. 현재 외부 API 호출을 추가하지 않았으며 React는 Oracle에 직접 접속하지 않습니다. 문서에 없는 API 경로나 DB 컬럼을 확정하지 않습니다.

## 계산 결과

`src/api/calculation-contract.js`의 `parseCalculationResult(response)`로 서버 응답을 검증합니다. `{error: 'NO_CRITERIA', message: '...'}`는 오류로 전달합니다. 응답의 필수 숫자값 누락·NaN을 0으로 숨기지 않습니다.

- `taxYear`, `totalSalary`, `withheldTax`, `taxableIncome`, `calculatedTax`, `decidedTax`, `expectedRefund`
- `details[]`: `typeCode`, `typeName`, `kind`, `baseAmount`, `deductionAmount`, `sourceNote`
- 종류: `INCOME_DEDUCTION`, `TAX_CREDIT`, `TAX_REDUCTION`, `CARD`, `CARD_RULE`
- `effect`, `formula`, `note`, `status`는 응답 계약에 포함하지 않습니다. 설명은 `deductionPresentation()`에서 제공합니다.
- 음수·0원 공제액을 보존하며 `cardDeductionTotal()`은 CARD/CARD_RULE 행만 합산합니다. 소득공제·세액공제·감면을 하나의 금액으로 섞어 더하지 않습니다.

`src/api/services.js`의 `taxService.calculate()`가 현재 체험 어댑터입니다. 실제 API 연동 시 이 경계를 비동기 서버 호출로 바꾸고, `App.calculate()`에서 응답을 상태로 보관하여 각 화면에 동일 결과를 전달하세요. 현재는 동일 입력의 체험 함수를 화면에서 호출합니다. 단순히 함수 이름만 비동기로 바꾸면 안 되며 로딩·오류·결과 상태 연결이 필요합니다.

`Dashboard`는 `result`와 `isDemo`를 독립된 prop으로 받습니다. 서버의 JSON만 `result`에 전달하고 실제 서버 응답일 때 `isDemo={false}`를 사용합니다. `dashboardModel(data, rows, result)`, `groupComparison(data, result)`도 결과를 받을 수 있습니다. 비교 화면은 `br`, `sr`, 챗봇 페이지는 `r`의 새 필드를 사용합니다. 실제 AI 연동 시 `aiService.reply`/`dashboardReply`의 체험 응답을 교체하고 새 결과를 상담 요청에 연결해야 합니다. AI가 세액을 다시 계산하게 하지 마세요.

체험 `taxableIncome`만 미산출 `null`을 허용합니다(`allowPending: true`). 실제 응답 파서는 해당 값에 숫자를 요구합니다. 사용자 피드백의 예시 숫자를 법정 검증값으로 사용하지 않습니다.

## 입력과 귀속 연도

`src/utils/tax-year.js`: 한국 시간 1~3월 전년도/4~12월 해당 연도라는 서비스 기본 선택 정책. 저장된 `taxYear` 또는 선택 연도가 있으면 유지합니다. 입력·상단·거래 집계·계산·시뮬레이션·사용자 통계 비교에 이를 전달합니다. 통계 원본의 귀속 연도 2024는 바꾸지 않습니다.

`TaxInfoForm`에서 독립 상태로 관리하는 `nationalPension`, `healthEmploymentInsurance`는 프론트 필드입니다. `erd-contract.insuranceInput()`에서 구분하여 받되 v3.9 컬럼·필수값 확인 후 서버 매핑을 구현해야 합니다. 기존 SOCIAL_INSURANCE에 두 값을 임의로 합산해서 저장하지 않습니다. `incomeDTO()`는 이 보험료 부분을 운영 DTO로 확정하지 않았습니다.

`qualificationDTO.HOMELESS_HEAD_YN`, `incomeDTO.SME_REDUCTION_YN`: Y/N/null을 구분합니다. null을 N으로 치환하지 마세요. 서버 저장 요건이 Y/N 필수라면 입력 요청 오류로 처리하거나 팀이 정한 미입력 처리 규칙을 구현해야 합니다.

`MONTHLY_RENT`는 월 금액 그대로입니다. 연간 계산용 금액은 월 금액 × 12로 체험 계산합니다. 실제 납부 개월·계약 검증은 서버가 담당합니다. 과거 연간 입력은 재입력을 요청하고 원본을 별도 보존합니다.

## 업로드·분류·회원 격리

`expense-service.js`: `parseUploadFile()` → CSV/XLSX 공통 변환 → 기존 예시 상호명 자동 분류 → 파일별 관계·중복 확인 → `uploadTotals(rows, taxYear)`. 다른 연도 거래를 삭제하지 않습니다. 실제 입력의 카드·현금 금액은 업로드에서만 집계하며 가상 추가 소비는 별도입니다.

`erd-contract.expenseDTO(row, categoryIdByCode, uploadIdByClientId)`는 서버에서 조회한 분류코드→숫자 CATEGORY_ID, 로컬 파일 ID→서버 발급 UPLOAD_ID 매핑이 준비되어야 객체를 생성합니다. 결제수단은 CREDIT/CHECK/CASH를 검증하며 임의 번호·알 수 없는 결제수단을 보내지 않습니다. 기존 예시 목록 LIST_ID는 운영 외래키가 아니므로 null로 내보내며 서버가 실제 목록 대조 결과로 확정해야 합니다.

회원번호는 요청 객체에서 제외합니다. 서버가 로그인 인증정보로 MEMBER_ID를 결정하고 업로드 소유권을 검증하며 거래 조회·삭제에도 동일한 회원 조건을 적용해야 합니다. 브라우저 저장 키 분리는 운영 인증이 아닙니다. 분류 결과의 CATEGORY_CODE는 UI/분류 경계 값으로 CATEGORY_ID와 다릅니다. 사용자 소비 유형 직접 수정 기능은 추가하지 않았습니다.

## 회원·동의

`account-service.js`, `AccountForms.jsx`: 가입·로그인·중복 검사·이메일 체험 인증·권한·잠금·탈퇴를 서버로 교체합니다. 현재 체험 등록은 브라우저 저장입니다.

`src/config/consent-versions.js`의 환경변수는 팀의 운영 동의서 버전 설정입니다. 미확정이면 로컬 체험만 가능합니다. `consentDTO()`는 누락·빈 문자열·미확정 체험 버전을 차단합니다. 최종 시각·버전은 서버가 검증하고 기록하세요. 클라이언트가 보낸 동의 시각을 신뢰하지 않습니다.

## 통계

`GROUP_STAT`의 실제 열만 `src/data/statistics/group-stat-2024.json`에 유지했습니다. `group-stat-metadata.json`의 POPULATION/원본 합계 등은 출처 재현용 보조 메타데이터로 DB 컬럼이 아닙니다. `STAT_FILE`의 FILE_ID 관계와 파일 경로는 `stat-file.json`에 있습니다.

`group-model.js`는 GENDER_AGE와 SALARY 행을 독립적으로 조회합니다. `GroupStats.jsx`는 AVG_DECIDED_TAX/AVG_REFUND_TAX만 비교하며 중앙값·순위·백분위를 생성하지 않습니다. DB 연동 시 실재하는 필드와 TAX_YEAR 기준으로 조회하고 없는 항목은 생성하지 마세요. 정적 파일의 메타데이터는 DB 응답의 필수 열로 가정하지 않습니다.

## 그 밖의 연결 위치

- `prototype-records.js`: 문의 WAITING/CHECKING/ANSWERED, 관리 기준값·접근 로그·예측 기록. 서버 관리자 권한 확인 필요.
- `ChatPanel.jsx`, `services.aiService`: 상담방/메시지 Oracle 저장, Gemma3·RAG 호출. 현재 고정 응답.
- `App.jsx`, `userService`: 입력·계산 이력·시나리오 조회/저장을 서버로 교체. 원본과 가상 입력은 분리 유지.

## 소비 유형 표 복구 후 표시 경계

대시보드의 소비 유형별 표는 업로드 거래에서만 집계합니다. `details`를 소비 유형으로 재분류하거나 지출액으로 사용하지 않습니다. 별도 `DeductionDetails`는 기본 접힌 표이며, 계산 API 미연동 시 숫자를 확정값으로 표시하지 않습니다. 연결 여부는 응답 JSON과 분리된 `calculationConnected` prop으로 전달합니다. Dashboard는 기존 `isDemo`의 반대 값을 전달합니다. 실제 응답일 때만 0원과 음수 조정액도 그대로 표시하고 카드 합계에 반영합니다. 향후 시뮬레이션 API 연결 시에도 해당 컴포넌트에 실제 연결 상태를 전달해야 합니다.
