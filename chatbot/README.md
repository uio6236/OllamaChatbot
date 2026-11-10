# 희망환급 (Hope Refund) — Chatbot

희망환급 프로젝트의 **Python FastAPI 기반 AI 챗봇 서버**입니다.

연말정산 및 청년 세제 혜택에 관한 질문에 답변하고, RAG(Retrieval-Augmented Generation)를 이용해 관련 참고 자료를 검색하여 AI 답변을 생성하도록 설계합니다.

> **현재 상태:** Health·ChatOllama·내부 API/인증 골격 구현. RAG 미구현으로 실제 상담·추천 POST는 정상 인증 후 `503 RAG_NOT_READY`. Spring Boot 연동은 예정.

## 1. 개발 환경

| 구분 | 기술 |
|---|---|
| Language | Python 3.11.9 |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| LLM | Ollama + Gemma3 (연동 예정) |
| RAG | 문서 검색 기반 답변 생성 (구현 예정) |
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
      ├── 질문 처리
      ├── RAG 참고 자료 검색
      └── Ollama / Gemma3 답변 생성
```

Frontend는 Spring Boot API를 호출합니다.

Spring Boot는 회원 인증, 대화 기록 관리 및 DB 저장을 담당합니다.

Python Chatbot은 전달받은 질문과 필요한 문맥을 기반으로 참고 자료를 검색하고 AI 답변을 생성합니다.

현재는 목표 아키텍처이며, 실제 서버 간 HTTP 연동은 아직 구현되지 않았습니다.

## 8. 현재 구현 상태

### 구성 완료

- Python 3.11.9 가상환경
- FastAPI 기본 애플리케이션
- `/health` API
- pytest 테스트
- Ruff 코드 검사 및 포맷 설정
- 기본 패키지 의존성 파일
- 환경변수 예시 파일

### 추후 구현 및 검증 예정

- Ollama 설치 및 Gemma3 실행
- 연말정산 RAG 참고 자료 정리
- PDF 문서 텍스트 추출 및 전처리
- 문서 청크 분할 및 임베딩
- 벡터 검색 및 근거 문서 활용
- AI 질문 처리 API
- Spring Boot와 내부 HTTP 연동
- 내부 인증 토큰 검증
- 대화 문맥 전달 및 답변 반환
- AI 답변 품질 및 예외 상황 테스트

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

## 10. 첫 구현: 로컬 모델 연결 (2026-11-09)

위 초기 구축 기록 중 Gemma3 연동 예정 항목은 이 절의 상태로 갱신합니다.
`app/core/config.py`는 OS 환경변수를 검증하고 `app/llm/ollama.py`의
`OllamaService.generate()`는 `ChatOllama.invoke()`로 텍스트를 생성합니다.
새 HTTP API는 추가하지 않았으며 `/health`는 모델 상태를 검사하지 않습니다.

Python 3.11.9에서 검증한 `langchain-ollama==1.1.0`을 사용합니다.
`httpx`, `ollama`는 호출 오류 분류에, `langsmith`는 호출 구간의 외부 추적을
명시적으로 비활성화하는 데 사용합니다. 질문과 답변을 기록하지 않습니다.
연결 제한은 3초, HTTP 읽기 대기 제한은 60초입니다. 이는 전체 생성 시간의
절대 상한은 아니며 스트림 데이터 사이의 대기 제한입니다.

다음은 `chatbot/`에서 실행하는 수동 통합 검증입니다. 모델은 미리 설치되어 있어야 합니다.

```powershell
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'gemma3:4b'
.\.venv\Scripts\python.exe -c "from app.llm.ollama import OllamaService; print(OllamaService().generate('Reply with just OK.'))"
```

`.env.example`을 복사하는 것만으로 설정이 로딩되지는 않습니다.
연결 불가, 시간초과, 모델 없음, 서버 오류·잘못된 응답은 별도 내부 예외로 구분합니다.
질문이 비어 있으면 모델을 호출하지 않습니다. 오류에서 원본 서버 메시지를 노출하지 않습니다.

단위 테스트는 모델 생성자를 Mock으로 대체하므로 실제 Ollama 없이 실행합니다.
기존 Health 테스트를 포함해 19개 통과했으며, 실제 `gemma3:4b` 호출은 별도로 `OK`를 확인했습니다.
RAG·세법 정확성·동시성·서버 간 인증은 이번에 구현하거나 검증하지 않았습니다.

## 11. 내부 API와 현재 동작 범위

`POST /internal/chat-responses`, `POST /internal/recommendations`는 내부 DTO와
`X-Chatbot-Token` 인증을 적용합니다. 공통 응답 봉투와 `errorId`는 적용하지 않습니다.
camelCase·엄격한 금액 타입·질문/이력 상한을 검증합니다. 계약과 보류 사항은
`docs/03_API_계약_초안.md` 상단을 확인하세요. 위 10절의 인증 미검증 기록은 첫 구현 당시 기록입니다.

```powershell
# 실제 비밀값은 OS 환경에서 관리하고 저장소에 기록하지 않습니다.
$env:CHATBOT_API_TOKEN = '<로컬에서만 설정할 비밀값>'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

서버 토큰 미설정·빈 값이면 시작 시 오류 로그를 남기고 내부 POST는 503
`AUTH_NOT_CONFIGURED`로 차단합니다. 서버는 시작하며 `/health`는 유지됩니다.
헤더 누락·불일치는 401 `INTERNAL_UNAUTHORIZED`, 유효하지 않은 DTO는 422
`VALIDATION`입니다. 정상 인증·유효 입력도 현재는 503 `RAG_NOT_READY`입니다.
실제 요청에서 가상 답변을 반환하는 설정은 없습니다. 검색·모델 정상 생성 테스트는
의존성 대체로만 수행하며 운영 설정에서 활성화하지 않습니다.

초기 모델/서비스 대기 제한은 45/50초입니다. 실제 시간값의 적절성·전체 HTTP 처리
시간·추론 취소는 미검증입니다. 동기 호출은 제한 응답 후에도 계속될 수 있고,
실제 작업 종료까지 프로세스별 모델 슬롯을 점유합니다. 세법·생성 숫자 검증,
Oracle 저장·출처 영구 보존·추천 작업 상태 관리는 아직 구현하지 않았습니다.

## 12. PDF 8개 오프라인 전처리

Python 3.11.9에서 `chatbot/`를 작업 디렉터리로 사용합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-preprocess.txt
.\.venv\Scripts\python.exe scripts/preprocess_documents.py --input-dir app/data/raw --verify-reproducibility
# 같은 입력/설정의 완료된 결과를 해시 검증 후 다시 사용
.\.venv\Scripts\python.exe scripts/preprocess_documents.py --input-dir app/data/raw --reuse
```

기본 입력 기대 수는 8개입니다. `--input-dir`로 지정한 원본은 읽기만 하며 출력은
`chatbot/data/processed/<입력·설정 버전 해시>/`에 분리합니다. 기존 출력은 기본 거부하며
미완료 결과를 자동 덮어쓰거나 삭제하지 않습니다. 새 설정/파이프라인 버전은 다른 경로를 사용합니다.

`manifest.json`, `report.json`, 문서별 pages/chunks/excluded/review 자료를 생성합니다.
재현성 검증은 원본을 두 번 처리하여 청크·품질 보고서를 비교합니다. 메타데이터·원문·좌표를 보존하며
빈 페이지·실패·의심 중복·표 대응은 보고합니다. 모든 청크는 수동 검수 대기 상태로 생성되고
검색 사용 가능으로 자동 승격되지 않습니다. 적용 귀속연도는 미검증 null/false입니다.
`--max-chars`는 항/호 단위 추가 분할의 후보 상한이며 실제 검색 성능으로 확정된 값이 아닙니다.

PyMuPDF 1.26.7을 사용하며 OCR/임베딩/검색은 추가하지 않았습니다. 기존 FastAPI는
전처리 모듈을 import하지 않으며 상담·추천의 `RAG_NOT_READY` 동작은 유지됩니다.
AGENTS.md의 원본 수 변경은 별도 승인 전 수정하지 않습니다.
