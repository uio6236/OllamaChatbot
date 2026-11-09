# AGENTS.md

이 파일은 이 저장소에서 일하는 AI 코딩 에이전트(Claude Code, Codex, Cursor 등)를 위한 온보딩 문서다. 작업 전에 반드시 읽는다.

## 프로젝트 개요

희망환급: 청년 근로자가 소득·카드 내역을 넣으면 연말정산 예상 환급액을 계산하고, 절세 방법을 비교·안내받는 웹 서비스의 **API 서버(Spring Boot)** 저장소다. 회원 · 소득 · 카드 업로드 · 결과 저장 · 문의 · 관리자 기능과 DB 저장을 맡는다.

- 통신 흐름: 화면(React) → **이 저장소 API** → Oracle DB. 계산이 필요하면 이 저장소가 계산 서버(Python FastAPI)를 호출하고 결과를 DB에 저장한다.
- 화면은 이 저장소 API로만 데이터를 주고받는다. DB 저장은 이 저장소만 한다 (계산 서버는 DB를 읽기만 함).
- 이 저장소가 확인하는 구간: API 요청·응답 · DB 저장·조회 · 계산 서버 연동 · 챗봇 LLM(Ollama Gemma) 연동
- 범위 밖: 결제 · 카드 내역 직접 입력(파일 업로드만) · 실명 수집 · 세액 계산 자체(계산 서버 담당 · LLM 사용 안 함)

## 명령어

빌드 도구는 **Maven**(`./mvnw`)만 사용한다. Java 17 · Spring Boot 4.1.0 · MyBatis 스타터 4.0.1.
(Windows 명령 프롬프트(cmd)에서는 `./mvnw` 대신 `mvnw`로 쓴다. PowerShell·Git Bash는 `./mvnw` 그대로)

```bash
./mvnw spring-boot:run   # 서버 실행
./mvnw test              # 테스트 (JUnit)
./mvnw package           # 빌드
./mvnw spotless:apply    # 코드 모양 자동 정리
./mvnw spotless:check    # 코드 모양 검사
./mvnw -Psast compile spotbugs:spotbugs   # 정적 분석 (SpotBugs + Find Security Bugs)
```

## 기술 스택

Java 17 · Spring Boot 4.1.2 · Maven · MyBatis 4.0.1 · Oracle 21c XE(교육원 공용 DB 21.3) · Spotless(코드 모양) · JUnit 5(테스트) · SpotBugs(정적 분석)

## 폴더 구조

```text
src/main/java/com/hoperefund/
├── member/       # MEMBER · PASSWORD_RESET
├── income/       # INCOME
├── expense/      # CARD_UPLOAD · EXPENSE · SPEND_CATEGORY (계산 서버가 정리·분류한 결과 저장)
├── prediction/   # PREDICTION · PREDICTION_INPUT · PREDICTION_DETAIL (계산 서버 호출 → 결과 · 입력값 · 항목별 내역을 한 트랜잭션으로 저장)
├── statistics/   # GROUP_STAT · STAT_FILE
├── chat/         # CHAT_SESSION · CHAT_MESSAGE · RECOMMENDATION (대화 저장)
├── inquiry/      # INQUIRY
├── admin/        # DEDUCTION_TYPE · TAX_BRACKET · BENEFIT_CONDITION 수정
└── common/       # ACCESS_LOG · 보안 · 예외 처리
    (각 폴더 안: controller / service / mapper / dto)
src/main/resources/mapper/   # MyBatis SQL (기능별 폴더)
```

## 규칙

- controller에는 요청·응답 처리만 두고, 주요 비즈니스 로직은 service에서 처리한다. mapper는 DB 조회·저장만 한다.
- SQL은 MyBatis mapper(XML)로 작성하고 값은 `#{}`로만 넣는다 (`${}` 금지 · SQL 삽입 방지). ORM(JPA)은 쓰지 않는다.
- `MEMBER_ID` 칸이 있는 회원 데이터 테이블을 조회·수정·삭제할 때는 로그인한 회원번호 조건을 넣는다. 자식 테이블(예: `PREDICTION_DETAIL`)은 부모 테이블(`PREDICTION`)과 연결해 본인 데이터인지 확인한다.
- 기준값 · 목록 테이블(`DEDUCTION_TYPE` · `TAX_BRACKET` · `MERCHANT_LIST` 등)처럼 `MEMBER_ID`가 없는 테이블에는 칸을 추가하지 않는다.
- 관리자 API는 `ROLE = 'ADMIN'`을 확인한다. 회원정보 수정에서 `ROLE` · `STATUS`는 바꾸지 않는다.
- 기준값(`DEDUCTION_TYPE`)은 번호(`TYPE_ID`)가 아니라 `TAX_YEAR` + `TYPE_CODE`(+ 총급여 구간)로 찾는다. 공용 DB와 새 계정의 번호가 다르다.
- 기본값이 있는 칸은 INSERT에서 빼고 넣는다 (NULL을 넣으면 오류).
- DB 이름 규칙: 테이블·칸은 대문자 SNAKE_CASE(예: `CARD_UPLOAD`, `MEMBER_ID`) · PK는 `테이블명_ID` 또는 `테이블명_NO` · Oracle 예약어 금지. 테이블·칸은 ERD v4.1(ERDCloud)이 기준이다: https://www.erdcloud.com/d/mL4eEnZLQ3QjgbWF4
- 금액은 원 단위 정수(`long`)로 다룬다.
- DTO 이름: 화면에서 받는 값은 `…RequestDTO`, 화면에 돌려주는 값은 `…ResponseDTO` (예: `IncomeRequestDTO` · `IncomeResponseDTO`). 받는 DTO에는 화면이 넣어야 하는 칸만 둔다 (번호·작성일 같은 칸을 요청으로 바꿀 수 없게).
- 새 기능에는 `src/test/java`에 같은 패키지로 `*Test.java`를 함께 작성한다.
- 사용자에게 보이는 문구는 한글로 쓴다.
- 코드 모양: 들여쓰기 4칸 · 변수·메서드명 camelCase · 문자열은 큰따옴표 `"` · 주석은 한글

## API 규칙

`docs/api-rules.md`를 따른다. 요약:

- 주소는 `/api/복수형명사/...` · 회원번호는 주소에 넣지 않는다 (로그인 정보로 회원을 정함 · 개발 중에만 `X-Member-Id` 헤더)
- 조회 GET · 생성·실행 POST · 한 건 전체 저장 PUT · 삭제 DELETE
- 오류 응답은 `GlobalExceptionHandler`에서 `{"error": "코드", "message": "화면 문구"}` 하나로 보낸다. DB 오류 코드는 기능명세서 「7_오류 메시지」 시트 문구로 바꾼다.
- 화면 문구와 서버 로그를 나눈다: 응답에는 짧은 안내만, 원인(예외 · 상태 코드 · 회원번호 · 연도)은 `log.warn` / `log.error`로. 로그에도 금액 · 생년월일 · 비밀번호 · 토큰은 넣지 않는다.

## 계산 서버 연동

- `prediction/`의 `CalcClient`가 계산 서버의 `POST /calculate` · `POST /benefit`을 부른다 (`X-Calc-Token` 헤더 · 연결 3초 · 응답 10초 제한).
- 계산 서버 연결 불가 → 503 `CALC_UNAVAILABLE` · 입력 거부 → 400 `CALC_REJECTED` · 기준값 없는 연도 → 400 `NO_CRITERIA`
- 계산 서버 호출은 트랜잭션 밖에서 하고, 저장(`PredictionSaveService`)만 트랜잭션으로 묶는다.

## 도메인 용어 사전

| 용어 | API · DTO 이름 | DB 칸 | 설명 |
| --- | --- | --- | --- |
| 총급여 | `totalSalary` | `INCOME.TOTAL_SALARY` | 비과세 제외 연간 급여 합계 |
| 기납부세액 | `withheldTax` | `INCOME.WITHHELD_TAX` | 원천징수로 이미 낸 세금 |
| 과세표준 | `taxableIncome` | `PREDICTION.TAXABLE_INCOME` | 근로소득금액 - 소득공제 |
| 산출세액 | `calculatedTax` | `PREDICTION.CALCULATED_TAX` | 과세표준 × 세율 |
| 결정세액 | `decidedTax` | `PREDICTION.DECIDED_TAX` | 산출세액 - 세액감면 - 세액공제 |
| 환급액 | `expectedRefund` | `PREDICTION.EXPECTED_REFUND` | 기납부세액 - 결정세액 (음수면 추가 납부) |
| 항목별 공제 내역 | `details[]` (`typeCode` · `baseAmount` · `deductionAmount`) | `PREDICTION_DETAIL` (`TYPE_ID` · `BASE_AMOUNT` · `DEDUCTION_AMOUNT`) | 근로소득공제(`EARNED_DEDUCTION`) · 근로소득세액공제(`EARNED_CREDIT`) 등 공제 항목별 금액 |
| 공제 종류 | `details[].kind` | `DEDUCTION_TYPE.DEDUCTION_KIND` | `INCOME_DEDUCTION` 소득공제 · `TAX_CREDIT` 세액공제 · `TAX_REDUCTION` 세액감면 · `CARD` · `CARD_RULE` |

## 기능명세서

- 기능 사양은 기능명세서(구글 시트)를 기준으로 한다: https://docs.google.com/spreadsheets/d/1qW5xjOhPqrWkCn9KLUUbylKfsFJCacfOAgBiXm27v9w/edit
- 기능명세서 · ERD · 노션 링크는 로그인이 필요해 열리지 않을 수 있다. 열 수 없으면 내용을 추측하지 말고, 사용자에게 필요한 부분(복사본 · 캡처)을 요청한다.
- ERD와 코드가 다르면 임의로 판단하지 말고 차이를 알린다. DB 변경이 필요하면 노션 「요청·전달」에 DB 변경 요청을 남긴다.

## Git

- 기능 개발은 각 담당자의 개인 브랜치에서 진행한다.
- 개발이 완료된 기능은 해당 `feature/기능명` 브랜치에 반영한다.
- `feature/기능명` 브랜치의 기능 구현 및 검증이 완료되면 `develop` 브랜치로 PR하여 통합한다.
- `develop`은 기능 통합 및 최종 검증을 위한 브랜치로 사용한다.
- `main`은 최종 안정 버전만 반영하는 브랜치로 사용한다.
- 공통 브랜치나 다른 담당자의 개인·기능 브랜치에 직접 커밋하지 않는다.
- 커밋은 의미 있는 기능 구현·수정 단위로 한다.
- 커밋 메시지는 종류: `무엇을 했는지` 형식으로 작성하고 설명은 한글로 작성한다.
- `커밋 종류`는 feat, fix, chore, docs, test, refactor, ci 등을 사용한다.
- 사용자 확인 없이 git push, 브랜치 삭제, 강제 푸시(git push -f)를 수행하지 않는다.

## 보안

- DB 비밀번호 · 계산 서버 토큰(`CALC_API_TOKEN`) · JWT Secret · 이메일 인증 Secret은 코드에 쓰지 않는다. `.env`에만 쓰고 `.env.example`에는 이름만 적는다.
- 오류 응답에 SQL · 스택 트레이스 · DB 주소를 넣지 않는다 (`application.yml`의 `include-stacktrace: never` 유지).

## 작업 방식

- 처음 맡은 작업이나 큰 변경은 먼저 분석한다: 기존 패키지 구조 · 데이터 흐름(API → service → mapper → DB · 계산 서버) · 구현된/안 된 기능. 분석 결과를 먼저 보고하고, 이 단계에서는 승인 없이 코드 수정·파일 생성을 하지 않는다.
- 새 파일이 필요하면 파일별 역할과 만드는 이유를 설명하고 승인 후 만든다. 기능 파일과 그 테스트 파일은 함께 적어 한 번에 승인받는다.
- 진행 순서: 요청 확인 → 기능명세서 · ERD 확인 → 기존 코드 분석 → 데이터 흐름 설계 → 필요한 부분만 구현 → 다른 도메인 영향 확인 → 테스트 → 문서 갱신
- 수정 후 보고: 목적·결과 · 수정한 파일과 역할 · 바뀐 동작을 짧게 요약한다. 해당될 때만 API 주소·요청·응답 변경 · 관련 테이블 · 추가 환경변수 · 테스트 결과와 미검증 항목 · 아직 안 된 부분 · 갱신한 문서를 덧붙인다.

## 테스트 기준

- 정상 입력과 예외 입력을 모두 확인한다.
- 해당되는 구간을 확인한다: API 요청·응답(정상 · 오류 코드) · DB 저장·조회(본인 데이터만) · 계산 서버 데이터 전달·결과 반환·연결 실패 · 챗봇 LLM 요청·응답·오류 처리
- `common/`을 고치면 다른 도메인 API가 정상인지 확인한다.
- 테스트하지 않은 항목은 「미검증」으로 적는다. 하지 않은 작업·테스트를 완료했다고 보고하지 않는다.

## 문서 관리

`docs/`에 아래로만 기록한다 (예외: 초기 세팅·검증 절차 `docs/setup/` · API 규칙 `docs/api-rules.md`). 다른 문서 분류를 임의로 추가하지 않는다.

- `docs/history.md`: 작업·변경 내역. 작업을 마칠 때마다 기록하고, 최신 작업이 맨 위에 오도록 쌓는다.
- `docs/decisions/`: 주요 결정과 그 이유
- `docs/tasks.md`: 구현 예정 · 진행 중 · 남은 작업

`docs/history.md` 형식:

```markdown
### [YYYY-MM-DD] 작업 요약 제목
- **작업 내용**: 수정한 파일 및 핵심 변경점
- **변경 사유**: 변경 목적 또는 해결한 문제
- **검증 결과**: 실행/테스트한 명령어 및 결과
```

- 여러 브랜치에서 `docs/history.md`를 같이 고쳐 develop에 합칠 때 충돌이 나면, 두 기록을 모두 남기고 날짜순(최신이 위)으로 둔다.

## 작업 완료 조건

작업을 "끝났다"고 말하기 전에 아래를 실행하고, 모두 통과한 결과를 보여준다.

```bash
./mvnw spotless:check && ./mvnw -B verify
```

## 하지 말 것

- 요청받은 기능의 대상 폴더 외에 다른 기능(도메인) 폴더나 공통 폴더를 임의로 수정하지 않는다. 수정이 필요하면 작업 전에 먼저 확인받는다.
- 작업 대상 도메인 패키지 외의 다른 도메인 코드나 `common/` 설정, DB 테이블·칸 구조를 승인 없이 수정하지 않는다. ERD에 없는 테이블·칸을 임의로 추가하지 않는다.
- DB 테이블·칸과 기존 데이터를 바꾸거나 지우지 않는다.
- 요청받지 않은 기능 추가 · 기존 기능 삭제를 하지 않는다. 요청받지 않은 외부 라이브러리를 설치하지 않는다 (필요하면 이유를 말하고 묻는다).
- `.env*` 파일을 읽거나 내용을 출력·커밋하지 않는다.
- 사용자 확인 없이 `git push`, 브랜치 삭제, 강제 푸시(`git push -f`) 금지. 커밋 이력을 지우지 않는다.
- 안 쓰는 import·변수를 남긴 채 커밋하지 않는다.
- 린터 규칙을 끄거나 주석으로 숨기지 않는다. 꼭 필요하면 이유를 말하고 허락을 받는다.
- `target/` 같은 빌드 산출물을 커밋하지 않는다.
- 기존 프로젝트를 새로 재작성하거나, 정상 기능·기존 파일을 임의로 삭제·이동하지 않는다.

## 참고 문서 (필요할 때만 읽는다)

- 개발 환경 세팅 절차: `docs/setup/` (01-linter → 02-testing → 03-github → 04-github-actions → 05-verification)
- API 규칙: `docs/api-rules.md`
- 작업 이력: `docs/history.md` · 주요 결정: `docs/decisions/` · 남은 작업: `docs/tasks.md`
