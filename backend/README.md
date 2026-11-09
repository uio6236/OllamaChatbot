# 희망환급 (Hope Refund) — Backend

희망환급은 청년 근로자의 연말정산 예상 환급액 계산과 AI 절세 상담을 지원하는 웹 서비스입니다.

본 프로젝트는 **Spring Boot 기반 백엔드 API 서버**로, React 프론트엔드의 요청 처리, Oracle Database 조회·저장, Python 계산 서버 및 AI 챗봇 서버 연동을 담당합니다.

> **현재 상태:** 공통 초기 프로젝트 구축 및 기본 검증 완료 / 기능별 API 개발 예정

## 1. 개발 환경

| 구분 | 기술 |
|---|---|
| Language | Java 17 |
| Framework | Spring Boot 4.1.2 |
| Build Tool | Maven Wrapper |
| Web | Spring Web MVC |
| Database | Oracle Database 21c XE |
| Persistence | MyBatis Starter 4.0.1 |
| Testing | JUnit 5, MockMvc |
| Code Quality | Spotless, SpotBugs, Find Security Bugs |
| IDE | Spring Tools for Eclipse (STS) |

개발 규칙, 기능별 패키지 구조 및 코드 작성 기준은 [`AGENTS.md`](AGENTS.md)를 참고합니다.

## 2. 프로젝트 구성

```text
two-trillion/
├── frontend/       # React + Vite
├── backend/        # Spring Boot + MyBatis
├── calc/           # Python 계산 서버 (예정)
└── chatbot/        # Python AI 챗봇 서버 (예정)
```

현재 Backend 공통 초기 프로젝트의 주요 구성은 다음과 같습니다.

```text
backend/
├── pom.xml
├── mvnw
├── mvnw.cmd
├── .mvn/
├── README.md
├── AGENTS.md
│
└── src/
    ├── main/
    │   ├── java/com/hoperefund/
    │   │   ├── HopeRefundBackendApplication.java
    │   │   └── common/
    │   │       ├── config/
    │   │       │   └── CorsConfig.java
    │   │       ├── controller/
    │   │       │   └── HealthController.java
    │   │       ├── dto/
    │   │       │   └── ErrorResponseDTO.java
    │   │       └── exception/
    │   │           └── GlobalExceptionHandler.java
    │   │
    │   └── resources/
    │       └── application.yml
    │
    └── test/java/com/hoperefund/
        └── common/
```

회원, 소득, 지출, 계산 결과, AI 상담 등 기능별 패키지는 담당자가 개발 과정에서 추가합니다.

최종 패키지 구조 및 역할 구분은 `AGENTS.md`를 기준으로 합니다.

## 3. 프로젝트 가져오기

### 3.1 사전 준비

다음 환경이 필요합니다.

- JDK 17
- STS 또는 Java 개발이 가능한 IDE
- Git
- Oracle DB 접속 정보

Maven은 프로젝트에 포함된 Maven Wrapper를 사용하므로 별도로 설치할 필요가 없습니다.

### 3.2 STS에서 프로젝트 Import

1. GitHub에서 `two-trillion` 저장소를 Clone합니다.
2. STS를 실행합니다.
3. `File → Import → Maven → Existing Maven Projects`를 선택합니다.
4. Root Directory에 `two-trillion/backend` 경로를 지정합니다.
5. `pom.xml`을 선택하고 `Finish`를 누릅니다.
6. 프로젝트 우클릭 → `Maven → Update Project`를 실행합니다.

STS Workspace는 Git 저장소와 별도의 폴더로 지정하는 것을 권장합니다.

## 4. 환경변수 설정

Spring Boot의 공통 설정은 다음 파일에서 관리합니다.

```text
src/main/resources/application.yml
```

실제 비밀번호와 인증 토큰은 소스 코드에 작성하지 않고 환경변수로 전달합니다.

### 4.1 필수 환경변수

| 환경변수 | 설명 |
|---|---|
| `DB_URL` | Oracle JDBC 접속 주소 |
| `DB_USERNAME` | Oracle DB 사용자 계정 |
| `DB_PASSWORD` | Oracle DB 비밀번호 |

Oracle 접속 주소는 팀 DB 담당자가 제공한 정보를 사용합니다.

### 4.2 추가 환경변수

| 환경변수 | 설명 | 기본값 |
|---|---|---|
| `SERVER_PORT` | Spring Boot 실행 포트 | `8080` |
| `CALC_BASE_URL` | Python 계산 서버 주소 | `http://localhost:8000` |
| `CALC_API_TOKEN` | 계산 서버 내부 인증 토큰 | 없음 |
| `CHATBOT_BASE_URL` | Python 챗봇 서버 주소 | `http://localhost:8001` |
| `CHATBOT_API_TOKEN` | 챗봇 서버 내부 인증 토큰 | 없음 |

Python Calc 및 Chatbot 서버와의 실제 통신은 아직 구현되지 않았습니다.

챗봇 서버의 포트 및 인증 방식은 추후 확정이 필요합니다.

### 4.3 STS 환경변수 등록 방법

1. `Run → Run Configurations...`를 선택합니다.
2. `Spring Boot App`에서 Backend 프로젝트를 선택합니다.
3. `Environment` 탭으로 이동합니다.
4. `DB_URL`, `DB_USERNAME`, `DB_PASSWORD`를 추가합니다.
5. `Apply → Run`을 선택합니다.

> **주의:** DB 비밀번호, API 토큰 등 민감정보는 GitHub에 업로드하거나 화면 캡처에 노출하지 않습니다.

## 5. 서버 실행

### 5.1 STS에서 실행

`HopeRefundBackendApplication.java`를 우클릭한 후 다음을 선택합니다.

```text
Run As → Spring Boot App
```

### 5.2 CMD에서 실행

`backend` 디렉터리에서 실행합니다.

```cmd
mvnw spring-boot:run
```

CMD에서도 DB 환경변수가 설정되어 있어야 합니다. STS에 등록한 실행 환경변수는 CMD에 자동으로 전달되지 않습니다.

### 5.3 정상 실행 확인

서버 실행 후 다음 주소로 접속합니다.

```http
GET http://localhost:8080/api/health
```

정상 응답:

```text
OK
```

해당 API는 Spring Boot의 기본 HTTP 응답 확인용입니다. Oracle DB나 Python 서버 전체의 상태까지 검사하지는 않습니다.

## 6. 테스트 및 빌드

모든 명령어는 `backend` 폴더에서 실행합니다.

### JUnit 테스트

```cmd
mvnw test
```

### 코드 형식 자동 정리

```cmd
mvnw spotless:apply
```

### 코드 형식 검사

```cmd
mvnw spotless:check
```

### SpotBugs 정적 분석

```cmd
mvnw compile spotbugs:spotbugs
```

### 전체 빌드 검증

```cmd
mvnw -B verify
```

공통 초기 프로젝트에서 다음 검증을 완료했습니다.

- Health API 테스트 1개 통과
- CORS 테스트 2개 통과
- 공통 예외 처리 테스트 3개 통과
- Spotless 검사 성공
- SpotBugs 정적 분석 실행 성공
- Maven `verify` 성공

정적 분석에서 발견된 경고의 개별 검토는 별도 작업으로 진행합니다.

최종 작업 완료 조건은 `AGENTS.md`를 따릅니다.

## 7. 현재 구현 상태

### 구현 완료

- Spring Boot 기본 프로젝트 및 Maven 환경
- Oracle DB 연결 설정 및 실행 확인
- MyBatis 기본 설정
- 환경변수 기반 공통 설정
- React 개발 서버 CORS 설정
- Health API
- 공통 오류 응답 DTO
- 기본 공통 예외 처리
- JUnit 자동 테스트 및 코드 품질 검사 환경

### 추후 구현 예정

- Spring Security 인증·권한 처리
- 기능별 Controller·Service·Mapper·DTO
- 회원·소득·지출·계산 결과·관리자 API
- Python 계산 서버 HTTP 통신
- Python AI 챗봇 서버 HTTP 통신
- 공통 오류 처리 확장
- API 및 DB 통합 테스트

## 8. 관련 문서

| 문서 | 용도 |
|---|---|
| `AGENTS.md` | 개발 규칙, 패키지 구조, API·DB·보안·협업 규칙 |
| `docs/api-rules.md` | API 주소 및 요청·응답 공통 규칙 |
| `docs/setup/` | 개발환경 및 도구 설정 절차 |
| `docs/history.md` | 작업 변경 이력 |
| `docs/decisions/` | 주요 결정 사항 |
| `docs/tasks.md` | 작업 현황 및 예정 작업 |

기능 요구사항은 [희망환급 기능명세서 v1.13](https://docs.google.com/spreadsheets/d/1qW5xjOhPqrWkCn9KLUUbylKfsFJCacfOAgBiXm27v9w/edit)를 참고합니다.

ERD는 팀에서 공유한 v4.1을 기준으로 합니다.

일부 개발 문서는 초기 프로젝트 공유 이후 추가될 예정입니다.