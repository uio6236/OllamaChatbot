# 희망환급 (Hope Refund) — Chatbot

희망환급 프로젝트의 **Python FastAPI 기반 AI 챗봇 서버**입니다.

연말정산 및 청년 세제 혜택에 관한 질문에 답변하고, RAG(Retrieval-Augmented Generation)를 이용해 관련 참고 자료를 검색하여 AI 답변을 생성하도록 설계합니다.

> **현재 상태:** FastAPI 공통 초기 프로젝트 구성 완료 / Gemma3·RAG·Spring Boot 연동 개발 예정

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
| `OLLAMA_BASE_URL` | Ollama 서버 주소 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama에서 사용할 LLM | `gemma3` |

현재 `.env.example`은 설정 항목 안내용입니다.

환경변수 자동 로딩과 실제 인증 토큰 검증은 아직 구현되지 않았습니다.

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