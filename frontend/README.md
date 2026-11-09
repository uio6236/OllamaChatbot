# 희망환급 (Hope Refund) — Frontend

희망환급은 근로자의 연말정산 예상 환급액을 계산하고, 청년 맞춤형 절세 혜택과 AI 상담을 제공하는 웹 서비스입니다.

본 프로젝트는 **React 기반 프론트엔드**로, 사용자 화면과 입력 흐름을 담당하고 Spring Boot REST API를 통해 서버와 데이터를 주고받도록 설계되어 있습니다.

> **현재 상태:** React 초기 화면 및 체험 기능 구성 완료 / Spring Boot API 연동 예정

## 1. 개발 환경

| 구분 | 기술 |
|---|---|
| Language | JavaScript (JSX) |
| Framework | React 19 |
| Build Tool | Vite 8 |
| Runtime | Node.js 22.13 이상 |
| Package Manager | npm |
| UI | CSS, Radix UI 등 |
| Charts | Recharts |
| Icons | Lucide React |
| Code Formatting | Prettier |
| Testing | Node.js 기반 기존 테스트 스크립트 |
| IDE | VS Code 권장 |

코드 작성 규칙, 컴포넌트 설계, API 연동 원칙 및 협업 규칙은 [`AGENTS.md`](AGENTS.md)를 참고합니다.

## 2. 프로젝트 구성

전체 프로젝트는 다음과 같이 구성됩니다.

```text
two-trillion/
├── frontend/       # React + Vite
├── backend/        # Spring Boot + MyBatis
├── calc/           # Python 계산 서버
└── chatbot/        # Python AI 챗봇 서버 (추가 예정)
```

Frontend 주요 디렉터리는 다음과 같습니다.

```text
frontend/
├── public/
├── src/
│   ├── api/             # 데이터 서비스·API 연동
│   ├── components/      # 공통 UI·레이아웃
│   ├── pages/           # 화면별 컴포넌트
│   ├── routes/          # 해시 라우팅
│   ├── hooks/
│   ├── utils/
│   ├── config/
│   ├── data/
│   ├── styles/
│   ├── App.jsx
│   └── main.jsx
├── docs/                # 기존 개발·검증 기록
├── .env.example
├── package.json
├── package-lock.json
└── vite.config.js
```

기존 화면의 구조와 라우팅은 유지하며, 새로운 기능은 팀 기능명세서와 API 명세를 기준으로 연동합니다.

## 3. 개발환경 준비

### 3.1 사전 준비

- Node.js 22.13 이상
- npm
- Git
- VS Code 또는 React 개발이 가능한 IDE

### 3.2 프로젝트 가져오기

GitHub에서 공통 초기 프로젝트 브랜치를 Clone합니다.

```bash
git clone -b feature/project-base https://github.com/KH-Team2/two-trillion.git
cd two-trillion/frontend
```

이미 저장소를 Clone한 경우에는 현재 작업 상태를 확인하고 해당 브랜치로 전환합니다.

### 3.3 패키지 설치

```bash
npm install
```

설치 과정에서 `package.json`과 `package-lock.json`을 기준으로 필요한 패키지를 준비합니다.

생성된 `node_modules/` 폴더는 Git에서 관리하지 않습니다.

## 4. 환경변수 설정

환경변수 예시는 다음 파일에 있습니다.

```text
frontend/.env.example
```

현재 정의된 항목은 다음과 같습니다.

| 환경변수 | 설명 |
|---|---|
| `VITE_TERMS_VERSION` | 서비스 이용약관 버전 |
| `VITE_PRIVACY_VERSION` | 개인정보 처리 동의 버전 |
| `VITE_FINANCE_VERSION` | 금융정보 저장 동의 버전 |

필요한 경우 `.env.example`을 복사해 `.env` 파일을 생성하고 팀에서 확정한 버전값을 입력합니다.

미설정 상태에서도 기존 로컬 체험은 가능하지만, 서버 저장용 동의 정보 구성에는 확정된 버전값이 필요할 수 있습니다.

**주의:** `VITE_` 환경변수는 브라우저에 공개될 수 있으므로 비밀번호, API 토큰 등의 민감정보를 저장하지 않습니다.

향후 Spring Boot API 연결에 필요한 서버 주소 및 개발용 회원 식별 설정은 팀의 공통 API 규칙에 맞춰 추가합니다.

## 5. 개발 서버 실행

`frontend` 디렉터리에서 실행합니다.

```bash
npm run dev
```

기본 개발 서버 주소:

```text
http://localhost:5173
```

실제 접속 주소는 터미널에 표시되는 URL을 확인합니다.

서버 종료는 `Ctrl + C`를 사용합니다.

### 배포용 빌드

```bash
npm run build
```

### 빌드 결과 미리보기

```bash
npm run preview
```

## 6. 현재 화면 및 기능

현재 프론트엔드에는 다음 화면과 체험 흐름이 구성되어 있습니다.

| 영역 | 주요 화면 및 기능 |
|---|---|
| 회원 | 로그인, 회원가입, 비밀번호 재설정 |
| 연말정산 정보 입력 | 소득·공제 정보 입력, 파일 업로드 |
| 대시보드 | 예상 계산 결과, 공제·감면 상세 |
| 시뮬레이션 | 조건 변경 및 결과 비교 |
| 청년 혜택 | 혜택 진단 화면 |
| AI 상담 | 챗봇 UI 및 체험 응답 |
| 그룹 통계 | 공식 통계 자료 기반 비교 |
| 마이페이지 | 회원 정보 및 설정 |
| 고객센터 | 문의 작성·조회 |
| 관리자 | 회원·문의 등 관리 화면 |

기존 화면의 라우팅에는 React Router 대신 `src/routes/useHashRouting.js` 기반의 해시 라우팅이 사용됩니다.

### 데이터 및 서버 연동 상태

현재 프론트엔드는 **기존 체험 기능과 서버 연동 대상 기능이 혼재된 상태**입니다.

- `src/api/services.js` 등에서 체험 데이터를 제공합니다.
- 일부 계정·입력·거래·상담 관련 상태는 브라우저 저장소를 사용합니다.
- 예상 세액 계산의 체험 로직은 실제 법정 세액 계산 결과를 보장하지 않습니다.
- 그룹 통계는 프로젝트에 포함된 정적 자료를 사용합니다.
- Spring Boot·Oracle·Python 계산 서버·Gemma3 챗봇과의 실제 연동은 별도로 구현해야 합니다.

브라우저 저장소에 저장된 체험 데이터는 실제 사용자 인증이나 서버 데이터 저장을 대체하지 않습니다.

## 7. 테스트 및 코드 검사

모든 명령은 `frontend` 디렉터리에서 실행합니다.

### Prettier 코드 자동 정리

```bash
npm run format
```

### Prettier 코드 형식 검사

```bash
npm run format:check
```

### 기존 프론트엔드 테스트

```bash
npm test
```

현재 `npm test`는 기존 프로젝트에 포함된 화면·기능 흐름 및 응답 계약 검증 스크립트를 실행합니다.

실제 브라우저 조작, Spring Boot API, Oracle DB, 이메일 전송 및 AI 서버 연동을 검증하는 테스트는 아닙니다.

### 빌드 검증

```bash
npm run build
```

현재 `package.json`에는 ESLint 및 Vitest 실행 스크립트가 등록되어 있지 않습니다. 관련 개발 규칙 및 테스트 환경은 향후 팀 표준에 맞춰 정리해야 합니다.

## 8. 현재 구현 상태

### 구성 완료

- React JSX + Vite 프로젝트
- 기존 페이지 및 공통 레이아웃
- 사용자 입력·대시보드·시뮬레이션 UI
- 카드·홈택스 파일 업로드 체험 기능
- AI 챗봇 UI 및 체험 응답
- 그룹 통계 화면
- 회원·관리자 체험 기능
- Prettier 설정
- 기존 프론트엔드 테스트 스크립트
- 개발용 API 데이터 계약 및 연동 메모

### 추후 구현 및 검증 예정

- Spring Boot REST API 연동
- 서버 기반 회원 인증 및 권한 적용
- 소득·지출·업로드 데이터의 서버 저장·조회
- Python 계산 결과 및 공제 상세 데이터 반영
- AI 챗봇 서버 연결 및 대화 기록 연동
- 실제 이메일 인증
- API 오류·로딩 처리 및 통합 테스트
- 팀 표준 ESLint·Vitest 환경 검토

## 9. 관련 문서

| 문서 | 용도 |
|---|---|
| `AGENTS.md` | 프론트엔드 개발 규칙 및 협업 기준 |
| `docs/API_INTEGRATION.md` | 백엔드 API 연결 참고 |
| `docs/FEEDBACK_REPORT.md` | 기존 수정 사항과 보류 사항 |
| `docs/VERIFICATION.md` | 기존 검증 결과 |
| `docs/EXPORT_VERIFICATION.md` | 원본 추출 검증 기록 |
| `docs/SOURCE_MAP.md` | 기존 소스 구성 및 추출 이력 |

기능 구현은 [희망환급 기능명세서 v1.13](https://docs.google.com/spreadsheets/d/1qW5xjOhPqrWkCn9KLUUbylKfsFJCacfOAgBiXm27v9w/edit)을 기준으로 합니다.

API 요청·응답의 상세 계약은 팀 공식 API 명세서를 따릅니다.

기존 사이트 추출 이력과 세부 수정 기록은 `docs/`의 관련 문서를 참고합니다.