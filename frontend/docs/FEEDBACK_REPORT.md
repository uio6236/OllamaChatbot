# 계산 담당자 피드백 반영 보고

기준: 동석님 전달 (껍데기 UI 확인 · 계산 결과 값).pdf 최우선, 희망환급 기능명세서.pdf, ERD v3.8. v3.9 전체 ERD는 제공되지 않았으므로 전달 PDF에서 확인한 방향만 반영했습니다.

## 반영 내용

| 요청                     | 실제 변경                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| 보험료 분리              | 국민연금/건강·고용보험료 독립 상태·검증·체험 계산. v3.9 DB 컬럼은 미확정                                       |
| 귀속 연도                | KST 기본 연도 공통 함수, 선택 연도, 입력·상단·업로드·결과·통계 사용자값·시뮬레이션 일치                        |
| 카드 고정 연도           | uploadTotals(rows, taxYear). 다른 연도 거래는 보존하고 해당 계산에서 제외                                      |
| 실제 카드 직접 입력 제거 | CSV/XLSX 업로드 집계 조회로 대체. 가상 소비 유형·결제수단·금액 입력은 유지                                     |
| 미입력 구분              | 예/아니요/확인 필요, 서버 DTO Y/N/null. null을 N으로 변환하지 않음                                             |
| 월세                     | 월 납부액 그대로 관리. 연간은 월액 × 12. 예전 연간 데이터는 재입력 안내                                        |
| 혜택 진단                | SME/월세/주택청약 3개 카드에 입력 기준 상태·이유·확인할 조건 표시. 실제 판정 미연동 안내                       |
| 동의                     | 별도 운영 버전 환경 설정. 미확정은 로컬 가입만 유지하며 서버 DTO 생성 차단. 최종 저장·시각 검증 서버 필요      |
| 지출 DTO                 | CATEGORY_ID 실매핑·서버 UPLOAD_ID 필요, 결제수단 검증. MEMBER_ID 클라이언트 지정 제외. 예시 LIST_ID 전송 안 함 |
| 통계 DTO                 | GROUP_STAT 실재 열과 원본 검증 메타 분리. 독립 두 집단 유지. 순위·백분위·중앙값 생성 없음                      |
| 결과 계약                | decidedTax/withheldTax/expectedRefund/details/calculatedTax 및 추가 필드 반영. 설명은 UI 계층으로 분리         |
| 결과 상세                | 과세표준·산출세액 자리, 항목명/대상액/공제액/종류/근거. 모든 API 행을 동적으로 표시                            |
| 음수·0                   | 음수 한도 조정액 보존·카드 합계 반영·왼쪽 빨간 막대. 0원도 유지. 환급/추가납부/0 표시                          |
| 전파                     | 대시보드·시뮬레이션·통계·AI·마이페이지·관리자 예측 조회에 새 필드 사용. 이전 이력 읽기 호환                    |
| 시연 문구                | 사용자 화면의 시연 계수·임의 공식 제거. 체험용 계산 상태는 명확히 유지                                         |

기존 회원/관리자 체험, 해시 라우팅, CSV/XLSX 다중 파일/목록/삭제/결제수단 확인/중복 처리, 예시 공공 상호명 대조, 소비 분포, 시뮬레이션 원본 분리, 고객센터, 관리자 기능은 유지합니다. 사용자 소비 유형 직접 수정 기능은 추가하지 않았습니다.

## 보류·백엔드 작업

- v3.9 국민연금/건강·고용보험료의 정확한 DB 열·제약 및 관련 시나리오 저장 열 확인. 프론트 변수는 DB 컬럼 확정이 아닙니다.
- 팀이 확정할 약관·개인정보·금융 동의서 버전, 기존 동의자 재동의 정책. 미확정 버전을 임의로 1.0으로 채우지 않음.
- 실제 CATEGORY_ID·LIST_ID 및 UPLOAD_ID의 서버 매핑과 인증 MEMBER_ID, 업로드/거래 소유권 검증.
- Spring Boot 규칙 기반 법정 계산·혜택 진단, 기준값 및 공제 한도/표준세액공제와 대안 항목 선택.
- Oracle 회원·소득·거래·예측·시나리오·상담·문의·접근 로그 저장/조회, 실제 이메일·Gemma3/RAG.
- 원본 통계의 보조 메타데이터는 DB 열로 만들지 않음. 공식 통계 API/DB 조회는 미연동.

## 체험용·한계

체험 엔진의 기존 산식을 유지했습니다. 반환 계약과 표시를 바꾼 것이 법정 계산 구현을 의미하지 않습니다. 체험 과세표준은 원래 계산이 없어 null/미산출로 표시하고, 실제 API의 숫자 과세표준은 표시 가능합니다. 근로소득공제/세액공제·6종 카드·한도/표준세액공제 행은 실제 응답에 있으면 모두 표시합니다. 체험 엔진이 법정 행을 임의 생성하거나 예시 JSON의 숫자를 계산 정답으로 사용하지 않습니다.

일반 카드 기본금액은 0으로 바뀌었으며 기존 수기 카드 합계는 재접속 시 업로드에서 재집계됩니다. 따라서 업로드 없는 초기 체험값은 이전 423,000원과 달라질 수 있습니다. 기존 사이트/localhost의 브라우저 저장소는 별개입니다. 기존 연간 월세·통합 보험료 원본은 보존하면서 재확인을 요청합니다. 다른 연도 거래는 파일 삭제를 선택하지 않는 한 보존됩니다.

서버 프레임워크 배포 설정 대신 Vite 정적 빌드를 사용합니다. 기존 JSX 추출본과 같은 소스를 사이트에도 사용하여 ZIP과 수정 웹사이트의 프론트 코드가 일치하도록 합니다. 운영 백엔드가 새로 연결된 것은 아닙니다.

## 실제 수정 파일 전체 목록

### 기존 파일 수정

- `.env.example`
- `.gitignore`
- `README.md`
- `docs/API_INTEGRATION.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/SOURCE_MAP.md`
- `docs/VERIFICATION.md`
- `docs/source-provenance.json`
- `package-lock.json`
- `package.json`
- `scripts/refresh-group-stat.mjs`
- `src/App.jsx`
- `src/api/account-service.js`
- `src/api/erd-contract.js`
- `src/api/expense-service.js`
- `src/api/prototype-records.js`
- `src/api/services.js`
- `src/components/layout/Topbar.jsx`
- `src/data/statistics/group-stat-2024.json`
- `src/pages/admin/AdminTools.jsx`
- `src/pages/auth/AccountForms.jsx`
- `src/pages/chatbot/ChatPanel.jsx`
- `src/pages/chatbot/ChatbotPage.jsx`
- `src/pages/dashboard/Dashboard.jsx`
- `src/pages/home/HomePage.jsx`
- `src/pages/profile/ProfilePage.jsx`
- `src/pages/simulation/SimulationPage.jsx`
- `src/pages/statistics/GroupStats.jsx`
- `src/pages/support/SupportPage.jsx`
- `src/pages/tax/BenefitsPage.jsx`
- `src/pages/tax/TaxInfoForm.jsx`
- `src/pages/tax/TaxInputPage.jsx`
- `src/styles/globals.css`
- `src/utils/dashboard-model.js`
- `src/utils/group-model.js`
- `tests/prototype-flows.mjs`
- `vite.config.js`

### 신규 파일

- `docs/FEEDBACK_REPORT.md`
- `docs/insurance-input.jpg`
- `src/api/calculation-contract.js`
- `src/components/common/DeductionDetails.jsx`
- `src/config/consent-versions.js`
- `src/data/statistics/group-stat-metadata.json`
- `src/utils/benefit-model.js`
- `src/utils/tax-year.js`
- `tests/feedback-contract.mjs`
- `tests/render-pages.mjs`
