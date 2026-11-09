# 희망환급 (Hope Refund) — Calc

희망환급 프로젝트의 **Python FastAPI 계산 서버**입니다.

연말정산 예상 세액 계산, 청년 혜택 진단, 카드·홈택스 파일 처리 및 지출 분류를 담당합니다.

> **현재 상태:** 공통 초기 프로젝트 구축 완료 / 계산·분류 기능 개발 예정

## 1. 개발 환경

| 구분 | 기술 |
|---|---|
| Language | Python 3.11.9 |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Database | Oracle Database 21c XE |
| Dependency Management | pip, requirements.txt |
| Testing | pytest |
| Code Quality | Ruff |
| IDE | VS Code 권장 |

세부 개발 규칙과 최종 디렉터리 구조는 `AGENTS.md`를 참고합니다.

## 2. 프로젝트 구조

```text
calc/
├── AGENTS.md
├── README.md
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── api/
│       ├── __init__.py
│       └── health.py
└── tests/
    └── test_health.py
```

계산 로직, 카드 처리, DB 연결 및 Repository 등은 기능 담당자가 개발하면서 추가합니다.

## 3. 개발환경 준비

### 3.1 프로젝트 폴더 이동

Windows CMD에서 실행합니다.

```cmd
cd /d C:\workspace\two-trillion\calc
```

### 3.2 Python 가상환경 생성

```cmd
py -3.11 -m venv .venv
```

### 3.3 가상환경 활성화

```cmd
.venv\Scripts\activate
```

정상적으로 활성화되면 CMD 앞에 `(.venv)`가 표시됩니다.

### 3.4 패키지 설치

```cmd
python -m pip install -r requirements-dev.txt
```

`requirements.txt`는 서버 실행에 필요한 패키지를, `requirements-dev.txt`는 개발·테스트 도구까지 포함합니다.

## 4. 환경변수 설정

`.env.example`에 필요한 환경변수 이름이 정의되어 있습니다.

| 환경변수 | 설명 |
|---|---|
| `DB_URL` | Oracle DB 접속 주소 |
| `DB_USERNAME` | Oracle DB 계정 |
| `DB_PASSWORD` | Oracle DB 비밀번호 |
| `CALC_API_TOKEN` | Spring Boot와 Calc 서버 간 인증 토큰 |
| `CALC_HOST` | FastAPI 실행 주소 |
| `CALC_PORT` | FastAPI 실행 포트 |

실제 DB 연결 및 인증 기능은 아직 구현되지 않았습니다.

`.env.example`은 설정 항목 안내용이며, 현재 애플리케이션이 자동으로 읽지는 않습니다.

실제 비밀번호와 토큰은 GitHub에 올리지 않습니다.

## 5. 서버 실행

가상환경을 활성화한 상태에서 실행합니다.

```cmd
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

정상 실행 후 다음 주소에 접속합니다.

**Health API**

```text
http://127.0.0.1:8000/health
```

정상 응답:

```json
{
  "status": "OK"
}
```

**FastAPI 자동 API 문서**

```text
http://127.0.0.1:8000/docs
```

서버 종료는 `Ctrl + C`로 진행합니다.

## 6. 테스트 및 코드 검사

모든 명령은 `calc` 디렉터리에서 실행합니다.

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

### Ruff 자동 정리

```cmd
python -m ruff format .
```

초기 프로젝트에서 FastAPI 서버 실행, `/health` 200 응답, pytest 테스트 1개 및 Ruff lint 통과를 확인했습니다.

## 7. 현재 구현 상태

**구현 및 검증 완료**

- Python 3.11.9 가상환경
- FastAPI 기본 애플리케이션
- Health API
- pytest 테스트 1개
- Ruff lint 설정 및 검사
- Ruff formatter 설정

**추후 개발 예정**

- `POST /calculate` 예상 세액 계산
- `POST /benefit` 청년 혜택 진단
- 카드·홈택스 파일 파싱
- 지출 자동 분류
- Oracle DB 기준값 읽기 전용 조회
- `X-Calc-Token` 인증 검증
- Spring Boot 연동 테스트

## 8. 참고 문서

- `AGENTS.md`: Calc 서버 개발 규칙 및 담당 영역
- `docs/setup/`: 개발환경 설정 절차 (추가 예정)
- 희망환급 기능명세서 v1.13
- ERD v4.1
- 팀 API 공통 규칙

각 기능의 실제 요청·응답 규격은 공식 API 명세서를 기준으로 구현합니다.