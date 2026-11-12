# 희망환급 (Hope Refund) — Chatbot

희망환급 프로젝트의 **Python FastAPI 기반 AI 챗봇 서버**입니다.

Spring Boot가 전달한 연말정산 결과와 Calc 계산 설명 규칙을 사용해 회원별 결과를 설명합니다. 법령 자료 검색(RAG)은 별도 후속 범위입니다.

> **현재 상태:** Health·Ollama·내부 API 인증·계산 결과 설명·최초 브리핑/추천·질문 정책을 구현했습니다. Calc 기반 처리와 최초 안내는 RAG 없이 동작합니다. 법령 검색이 필요한 GENERAL 질문은 RAG 미구현으로 처리할 수 없습니다. 로컬 개발용 채팅 화면은 아래 별도 명령으로만 활성화합니다. Spring Boot 실연동은 별도 검증이 필요합니다.

## 1. 개발 환경

| 구분 | 기술 |
|---|---|
| Language | Python 3.11.9 |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| LLM | Ollama + Gemma3 |
| RAG | 미구현 (계산 결과 설명에서는 사용하지 않음) |
| Dependency Management | pip, requirements.txt |
| Testing | pytest |
| Code Quality | Ruff |
| IDE | VS Code 권장 |

세부 개발 규칙, RAG 처리 방식 및 서버 간 역할 구분은 [`AGENTS.md`](AGENTS.md)를 참고합니다.

## 2. 프로젝트 구성

희망환급은 다음과 같은 구조로 개발합니다.

```text
two-trillion/
├── frontend/        # React + Vite
├── backend/         # Spring Boot + MyBatis
├── calc/            # Python 계산 서버
└── chatbot/         # Python AI 챗봇 서버
```

현재 Chatbot 초기 프로젝트의 주요 구조는 다음과 같습니다.

```text
chatbot/
├── .env.example
├── README.md
├── AGENTS.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── api/
│       ├── __init__.py
│       └── health.py
│
└── tests/
    └── test_health.py
```

향후 질문 처리 API, Ollama 연결, RAG 문서 검색, 요청·응답 스키마 등의 모듈을 추가할 예정입니다.

최종 개발 목표 구조는 `AGENTS.md`를 참고합니다.

## 3. 개발환경 준비

### 3.1 사전 준비

- Python 3.11.9
- Git
- VS Code 또는 Python 개발이 가능한 IDE

Ollama 및 Gemma3는 실제 AI 기능 구현 단계에서 별도로 준비합니다.

### 3.2 프로젝트 가져오기

GitHub에서 공통 초기 프로젝트 브랜치를 Clone합니다.

```bash
git clone -b feature/project-base https://github.com/KH-Team2/two-trillion.git
cd two-trillion/chatbot
```

이미 저장소를 Clone한 경우에는 현재 브랜치와 작업 상태를 먼저 확인합니다.

### 3.3 Python 가상환경 생성

Windows CMD에서 실행합니다.

```cmd
py -3.11 -m venv .venv
```

### 3.4 가상환경 활성화

```cmd
.venv\Scripts\activate
```

정상적으로 활성화되면 CMD 앞에 `(.venv)`가 표시됩니다.

가상환경은 개발자별로 생성하며 GitHub에는 업로드하지 않습니다.

### 3.5 패키지 설치

```cmd
python -m pip install -r requirements-dev.txt
```

- `requirements.txt`: 서버 실행에 필요한 패키지
- `requirements-dev.txt`: 개발 및 테스트 도구를 포함한 패키지

Gemma3, 임베딩 및 벡터 검색 관련 의존성은 구현 방식 확정 후 추가합니다.

## 4. 환경변수 설정

환경변수 예시는 다음 파일에 있습니다.

```text
chatbot/.env.example
```

| 환경변수 | 설명 | 초기 기본값 |
|---|---|---|
| `CHATBOT_HOST` | FastAPI 실행 주소 | `127.0.0.1` |
| `CHATBOT_PORT` | FastAPI 실행 포트 | `8001` |
| `CHATBOT_API_TOKEN` | Spring Boot와 챗봇 서버 간 내부 인증 토큰 | 없음 |
| `OLLAMA_BASE_URL` | Ollama 서버 주소 | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Ollama에서 사용할 LLM | `gemma3:4b` |

현재 `.env.example`은 설정 항목 안내용입니다.

Ollama 연결 모듈은 OS 환경변수를 읽습니다. `.env` 파일 자동 로딩과 실제 인증 토큰 검증은 아직 구현되지 않았습니다.

**주의:** 비밀번호 및 인증 토큰은 GitHub에 업로드하지 않습니다. 실제 값을 설정할 경우 `.gitignore`에서 제외되는 로컬 환경변수 파일 또는 실행 환경 설정을 사용합니다.

## 5. FastAPI 서버 실행

가상환경이 활성화된 상태에서 실행합니다.

```cmd
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

정상 실행 후 브라우저에서 다음 주소를 확인합니다.

**Health API**

```text
http://127.0.0.1:8001/health
```

정상 응답:

```json
{
  "status": "OK"
}
```

**FastAPI 자동 API 문서**

```text
http://127.0.0.1:8001/docs
```

현재 Health API는 FastAPI 서버의 기본 HTTP 응답을 확인합니다. Ollama 모델이나 RAG 검색 시스템의 정상 상태까지 검사하는 기능은 아닙니다.

서버 종료는 `Ctrl + C`를 사용합니다.

## 6. 테스트 및 코드 검사

모든 명령은 `chatbot` 디렉터리에서 실행합니다.

### pytest

```cmd
python -m pytest -v
```

### Ruff 코드 검사

```cmd
python -m ruff check .
```

### Ruff 형식 검사

```cmd
python -m ruff format --check .
```

### Ruff 코드 자동 정리

```cmd
python -m ruff format .
```

현재 초기 프로젝트에서 다음 사항을 확인했습니다.

- Python 3.11.9 환경 실행
- FastAPI 서버 정상 실행
- `/health` API 응답 확인
- pytest Health 테스트 1개 통과
- Ruff 코드 검사 통과

Ruff 형식 검사 최종 통과 여부는 자동 정리 후 다시 확인해야 합니다.

## 7. 전체 시스템에서의 역할

```text
React Frontend
      │
      │ 사용자 질문
      ▼
Spring Boot Backend
      │
      ├── 회원 인증 및 권한 확인
      ├── 대화방 소유권 확인
      ├── Oracle DB 대화 기록 조회·저장
      │
      │ 내부 HTTP 요청
      ▼
Python FastAPI Chatbot
      │
      ├── TAX_RESULT: 전달된 결과·로컬 Calc 규칙으로 설명
      ├── Calc 계산 방식 질문: 관련 Calc 규칙을 Gemma3에 전달 (RAG 미사용)
      └── 최초 안내: 결과·규칙 기반 단일 메시지 / GENERAL: RAG 미구현
```

Frontend는 Spring Boot API를 호출합니다.

Spring Boot는 회원 인증, 대화 기록 관리 및 DB 저장을 담당합니다.

Python Chatbot은 `TAX_RESULT` 요청에서 Spring Boot가 전달한 개인별 계산 결과와 Calc 설명 규칙을 사용합니다. 별도 개인 결과 없이도 Calc 구현 방식만 설명할 수 있는 질문은 로컬 규칙 파일을 사용합니다. 이 흐름은 세액을 다시 계산하거나 RAG를 호출하지 않습니다. 회원별 결과와 규칙만으로 답할 수 없는 법령·자격 질문은 근거 부족으로 처리합니다.

회원 인증·Oracle 조회와 저장은 Spring Boot의 책임입니다. 실제 Spring Boot 서버 간 HTTP 연동은 아직 검증하지 않았습니다.

## 8. 현재 구현 상태

### 구성 완료

- Python 3.11.9 가상환경
- FastAPI 기본 애플리케이션
- `/health` API
- 내부 상담 API 및 토큰 인증
- fixture의 `TAX_RESULT` 구조 검증
- 최초 브리핑·적용 내역·최대 3개 개인별 확인 항목을 `/internal/recommendations`의 단일 `content`로 생성 (RAG 미사용, 자격·원인·절세액 추정 금지)
- 환급·추가 납부액 및 공제·감면 적용액 설명
- Calc 계산 규칙 기반 공제 계산 방식 설명 (RAG 없이 처리)
- 확인되지 않은 숫자·법령이 모델 답변에 포함되면 규칙 기반 설명으로 대체
- pytest 테스트
- Ruff 코드 검사 및 포맷 설정
- 기본 패키지 의존성 파일
- 환경변수 예시 파일

### 추후 구현 및 검증 예정

- Spring Boot와 실제 HTTP 연동 및 운영 DTO 확인
- 세법 적용연도·법률 정확성 검증
- RAG 참고 자료 검색
- PDF 문서 텍스트 추출 및 전처리
- 문서 청크 분할 및 임베딩
- 벡터 검색 및 근거 문서 활용
- 원본 입력 전체 및 Spring Boot 저장·표시 흐름을 포함한 최초 안내 통합 검증
- Ollama 실모델 품질·출력 안전성 평가

## 9. 관련 문서

| 문서 | 용도 |
|---|---|
| `AGENTS.md` | AI 챗봇 개발 규칙 및 아키텍처 |
| `.env.example` | 환경변수 예시 |
| `requirements.txt` | 서버 실행 의존성 |
| `requirements-dev.txt` | 개발 및 테스트 의존성 |
| `pyproject.toml` | Ruff·pytest 설정 |

기능 구현은 팀의 [희망환급 기능명세서 v1.13](https://docs.google.com/spreadsheets/d/1qW5xjOhPqrWkCn9KLUUbylKfsFJCacfOAgBiXm27v9w/edit)을 기준으로 합니다.

실제 API 주소와 요청·응답 데이터 구조는 팀 공식 API 명세서 및 Spring Boot 담당 영역과 협의하여 확정합니다.

### 원본 Calc 입력 기반 추천

`taxResult.inputs`는 선택적 원본 입력 스냅샷입니다. 정상 적용 공제는 추천에서 제외하고, 입력했지만 미적용/상세 누락인 항목과 조건부 검토 사항을 최대 3개 안내합니다. 누락/null을 0/N으로 간주하지 않습니다. 필드별 Spring 전달 매핑과 호환성은 `docs/03_API_계약_초안.md`의 최신 절을 참고하세요.

## 로컬 개발용 채팅 테스트 화면

운영 API 앱과 분리된 개발 서버입니다. 브라우저에서 더미 회원을 선택하면 기존 `/internal/recommendations`, 질문을 보내면 `/internal/chat-responses`를 서버 측에서 호출합니다. 같은 프로세스의 ASGI 앱을 경유하므로 별도로 8001 서버를 실행할 필요는 없습니다. 실제 Ollama는 네트워크로 호출하며 Mock 응답을 제공하지 않습니다.

### 실행 (Windows PowerShell)

Ollama를 먼저 실행하고 `ollama list`에서 `gemma3:4b`가 설치되어 있는지 확인하세요. 설치되지 않았다면 로컬 환경에서 모델을 준비해야 합니다. 이 도구는 모델을 자동 다운로드하지 않습니다.

저장소 루트에서:

```powershell
cd chatbot
$env:CHATBOT_ENV = 'development'
$env:CHATBOT_DEV_UI = '1'
.\.venv\Scripts\python.exe -m devtools.server
```

브라우저 접속: **http://127.0.0.1:8002/**

서버는 `127.0.0.1:8002`에만 바인딩하고 프록시 전달 IP를 신뢰하지 않습니다. 종료는 실행 터미널에서 `Ctrl+C`입니다. 이미 해당 포트의 개발 서버가 실행 중이면 기존 화면에 접속하거나 기존 서버를 종료한 뒤 재실행하세요.

- 기존 `CHATBOT_API_TOKEN`이 있으면 그대로 사용하고, 없으면 해당 개발 서버 프로세스에만 임시 토큰을 생성합니다. 토큰을 출력하거나 HTML·JavaScript·브라우저 헤더·개발자 정보로 전달하지 않습니다.
- 이 실행 명령은 `OLLAMA_MODEL=gemma3:4b`를 사용합니다. Ollama 기본 주소는 `http://127.0.0.1:11434`이며 필요한 경우 서버 실행 전 `OLLAMA_BASE_URL`을 설정할 수 있습니다. `.env` 자동 로딩은 없습니다.
- `CHATBOT_ENV=development`와 `CHATBOT_DEV_UI=1`이 모두 있어야 합니다. 기본/production 환경에서는 화면·더미 경로가 비활성화되며, 운영 `app.main:app`에는 개발 경로를 등록하지 않습니다. 환경을 바꾸면 재시작하세요. 공용 호스팅·역방향 프록시·터널에 공개하는 용도가 아닙니다.

### 사용 방법

1. 추가 납부·환급·월세 미적용·중소기업 감면 중 한 회원을 선택합니다. 최초 브리핑이 한 AI 메시지로 표시됩니다.
2. 질문을 입력하고 보내기를 누릅니다. Enter로 전송하고 Shift+Enter로 줄바꿈할 수 있습니다.
3. 성공한 문답과 최초 안내 중 최근 최대 10개 메시지·총 12,000자 이내를 다음 질문에 보냅니다. 단일 메시지가 4,000자를 넘으면 문맥 전송에서 제외합니다. 실패한 문답은 이력에 추가하지 않습니다.
4. 회원 변경·초기화 시 화면과 이력을 지웁니다. 이전 요청이 늦게 완료돼도 새 회원의 대화에 추가하지 않습니다. 추론 도중 회원을 바꾸면 이전 추론이 계속되어 MODEL_BUSY가 날 수 있으며, 잠시 후 브리핑을 다시 생성하면 됩니다.
5. 개발자 정보에서 마지막 내부 API 경로·JSON 요청/응답·HTTP 상태·처리 시간을 확인합니다. `model` 필드는 응답 메타데이터입니다. 이 화면에는 직접 호출 계측이 없으므로 **Gemma 직접 호출 여부는 확인 불가**로 표시합니다. model=null이나 모델 이름만으로 실제 호출 여부를 추측하지 않습니다.

응답이 5초 이상 걸리면 대기 상태를 표시합니다. API의 기존 45/50초 대기 제한을 유지하고 개발 경유 서버는 55초, 브라우저는 65초에서 대기를 제한합니다. 브라우저 중단·회원 변경이 실제 추론의 강제 종료를 보장하지는 않습니다. Ollama 미실행·모델 없음·처리 중·시간초과·법령 검색 미준비·서버 연결 실패는 한국어로 안내합니다.

모든 데이터는 `tests/fixtures`의 합성 회원입니다. 브라우저에는 선택 ID만 입력받고 서버가 고정 허용 목록으로 읽습니다. 운영 API가 더미를 자동 반환하지 않습니다. 대화는 브라우저 메모리에만 있어 새로고침하면 사라집니다. 로컬 OS 접근자에 대한 별도 사용자 인증을 구현한 도구는 아닙니다.

### 검증 도구

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -v
```

선택적 실제 브라우저 검증: 개발 서버와 Ollama를 켠 상태에서 Node 22+ 및 설치된 Edge로 `node tests/validate_dev_ui_browser.cjs`를 실행합니다. 별도 npm 의존성은 없습니다. Edge 경로가 다르면 `BROWSER_EXE`를 설정하세요. 이 스크립트는 pytest에서 자동 실행하지 않으며 임시 폴더에 브라우저 프로필·스크린샷·검증 JSON을 생성합니다. 실행 결과는 `docs/dev_ui_validation.md`에 기록합니다.
