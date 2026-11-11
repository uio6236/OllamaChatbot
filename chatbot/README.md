# 희망환급 (Hope Refund) — Chatbot

희망환급의 Python FastAPI 기반 AI 챗봇 서버입니다. 연말정산·청년 세제 혜택 안내를 위한 근거 기반 질의응답을 개발합니다.

현재 Health·ChatOllama 연결·내부 상담/추천 API·토큰 인증·PDF 전처리·검수 도구가 구현되어 있습니다. **Elasticsearch 검색과 실제 RAG 답변 연동은 미구현**이며, 정상 인증·유효 입력의 내부 POST도 현재 `503 RAG_NOT_READY`를 반환합니다.

## 1. 현재 구현·검증 상태

아래 검증 결과는 [기존 작업 기록](docs/history.md)에 근거합니다. 이번 문서 정리에서 테스트·모델 호출·전처리·검수 CLI를 재실행하지 않았습니다.

| 항목 | 구현 상태 | 실제 검증 범위와 한계 |
|---|---|---|
| FastAPI·GET /health | 완료 | HTTP 응답 확인·테스트 기록 있음. 모델·RAG 준비 상태 검사는 아님 |
| LangChain ChatOllama·로컬 Gemma 3 4B | 완료 | Mock 테스트와 과거 실제 `OK` 호출 기록 있음. 현재 환경의 가용성은 재확인 필요 |
| 내부 상담·추천 API·인증·DTO·오류 처리 | 완료 | Mock 기반 정상/오류·인증·타입·대기 제한 검증 기록 있음. 실제 Spring 연동은 미검증 |
| PDF 8개 추출·전처리·구조별 청킹 | 완료 | 실제 처리·재현성·무결성 검증 기록 있음. 전체 시각 영역·표 의미·법적 정확성 검수 완료는 아님 |
| 검수 대기열·v3 영역별 승인 게이트·내보내기 | 완료 | Mock 승인/회수·변조 차단·실제 기존 자료 제외 검증 기록 있음. 실제 법령 승인과는 별개 |
| 실제 자료 수동 구조 검수·적용 검증·사용 승인 | 미완료 | 기록상 3,133개 HOLD, 승인 0개. 적용 귀속연도 null/false 유지 |
| Elasticsearch BM25 매핑·색인·검색 | 미구현 | 실제 검색·성능 미검증 |
| 실제 검색 결과 기반 RAG 답변 | 미구현 | 검색·모델 결합 경로는 테스트 의존성 대체로 검증. 실제 세법·답변 품질 미검증 |
| Spring·React 연동, 상담·추천·출처 저장 | 미구현 | 실제 서버 간 HTTP·Oracle·사용자용 응답 봉투/errorId 통합 미검증 |
| 다중 워커 전체 동시성·추론 강제 취소・색인 회수 동기화 | 미구현 | 운영 검증 미수행 |

최신 코드 검증 기록은 2026-11-11 `review-policy-v3` 작업의 **pytest 171개, Ruff check·format --check 통과**입니다. 날짜별 테스트 수와 실행 조건은 history에 보존합니다.

## 2. 시스템 역할과 프로젝트 구조

목표 통신 흐름은 `React → Spring Boot → Chatbot FastAPI → Elasticsearch 검색 / Ollama`입니다. 현재 검색·실제 서버 간 연동은 연결되지 않았습니다.

- React는 Spring Boot 사용자용 API를 호출합니다.
- Spring Boot는 회원 인증·대화방/계산 결과 소유권 확인·요청 제한·Oracle 대화/추천 저장을 담당합니다.
- Chatbot은 내부 인증·입력 검증·참고 자료 검색·답변 생성 및 근거 반환을 담당합니다.
- 세액 계산은 Calc 서버가 수행합니다. Chatbot은 Oracle에 직접 대화 기록을 저장하거나 세액을 재계산하지 않습니다.
- 챗봇 기능 담당 범위는 Python뿐 아니라 관련 Spring Boot·React 연동까지 포함합니다. 상세 규칙은 [AGENTS.md](AGENTS.md)를 따릅니다.

```text
OllamaChatbot/
├── frontend/                  # React + Vite
├── backend/                   # Spring Boot + MyBatis
├── calc/                      # Python 계산 서버
└── chatbot/
    ├── app/
    │   ├── main.py
    │   ├── api/               # Health·내부 상담/추천 API
    │   ├── core/              # 설정·인증·오류 처리
    │   ├── llm/               # ChatOllama 연결
    │   ├── rag/               # 추출·청킹·검수·승인 게이트
    │   ├── schemas/           # 요청·응답 DTO
    │   ├── services/          # 검색/생성 경계와 상담·추천 흐름
    │   └── data/raw/          # 원본 PDF 8개, Git 제외
    ├── scripts/
    │   ├── preprocess_documents.py
    │   ├── build_review_queue.py
    │   └── export_approved_chunks.py
    ├── data/processed/        # 전처리·검수·내보내기 결과, Git 제외
    ├── docs/
    ├── tests/
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── requirements-preprocess.txt
    ├── pyproject.toml
    ├── .env.example
    ├── README.md
    └── AGENTS.md
```

## 3. 개발환경 준비

Python 3.11.9, Git, Python 개발 IDE를 준비합니다. 서버는 FastAPI·Uvicorn·Pydantic, 모델 연결은 LangChain ChatOllama·Ollama의 `gemma3:4b`, 전처리는 PyMuPDF 1.26.7을 사용합니다. 초기 검색 방향은 Elasticsearch BM25이며 아직 구현되지 않았습니다.

### 저장소와 작업 디렉터리

개인 개발 저장소는 팀 저장소의 Fork가 아닌 별도 저장소입니다. 초기 소스 출발점인 팀 `feature/project-base`를 최신 구현 브랜치로 안내하지 않습니다.

```powershell
# 새로 가져오는 경우
git clone https://github.com/uio6236/OllamaChatbot.git
cd OllamaChatbot/chatbot
# 이미 작업 사본이 있으면 현재 브랜치와 변경 내용을 먼저 확인
git status --short
```

현재 로컬 작업 루트는 `C:\workspace\OllamaChatbot`입니다. 개인 저장소와 팀 저장소의 이력은 다르며 팀 통합 시 최신 팀 기준에 챗봇 변경분만 선별 반영합니다. Git 승인·브랜치 규칙은 AGENTS를 참고합니다.

이하 명령은 모두 `chatbot/`에서 실행합니다.

### 가상환경과 의존성

Windows CMD:

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
```

PowerShell에서는 활성화 없이 `.\.venv\Scripts\python.exe`를 직접 사용할 수 있습니다.

- `requirements.txt`: 서버·Ollama 연결 의존성
- `requirements-dev.txt`: 서버 의존성 및 pytest·Ruff 등 개발 도구
- `requirements-preprocess.txt`: 서버 의존성 및 PDF 전처리·검수 도구용 패키지

PDF 전처리·검수 작업 전 별도로 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-preprocess.txt
```

가상환경·캐시·모델 가중치·비밀정보는 커밋하지 않습니다. 원본 PDF와 생성 청크를 포함한 `app/data/raw/`, `data/processed/`는 Git 제외 대상입니다. 별도 취득한 원본의 공개·배포 가능 여부와 출처·라이선스를 확인해야 하며 자동으로 Git에 추가하지 않습니다.

## 4. 환경변수 설정

[.env.example](.env.example)은 항목 안내용입니다. **파일 복사만으로 자동 로딩되지 않으며**, 현재 내부 인증·Ollama 설정은 OS 환경변수를 읽습니다.

| 변수 | 용도 | 기본값 |
|---|---|---|
| `CHATBOT_HOST` | 실행 주소 안내값 | `127.0.0.1` |
| `CHATBOT_PORT` | 실행 포트 안내값 | `8001` |
| `CHATBOT_API_TOKEN` | 내부 공유 토큰 | 없음 |
| `OLLAMA_BASE_URL` | Ollama 주소 | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | 로컬 모델 | `gemma3:4b` |

`CHATBOT_HOST/PORT`는 현재 Uvicorn 실행에 자동 반영되지 않습니다. 다음 실행 명령의 `--host/--port`를 지정합니다. 실제 토큰은 OS 실행 환경에서 관리하고 코드·문서·Git·로그에 기록하지 않습니다.

```powershell
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'gemma3:4b'
# 예시 문자열을 실제 로컬 비밀값으로 바꾸고 저장소에는 기록하지 않습니다.
$env:CHATBOT_API_TOKEN = '<로컬에서만 설정할 비밀값>'
```

## 5. FastAPI 실행과 Health 확인

가상환경이 활성화된 CMD:

```cmd
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

PowerShell에서 가상환경 Python을 직접 사용:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- Health: `http://127.0.0.1:8001/health`
- 자동 API 문서: `http://127.0.0.1:8001/docs`
- 종료: `Ctrl + C`

`GET /health`는 인증 없이 `200 {"status":"OK"}`를 반환합니다. 이는 HTTP 응답 확인이며 Ollama·검색·인증 준비 상태를 보증하지 않습니다. 토큰 미설정이어도 서버와 Health는 시작하고 내부 POST만 차단합니다.

## 6. 내부 API와 현재 동작

| Method | 경로 | 용도 |
|---|---|---|
| GET | `/health` | 기본 HTTP 응답 |
| POST | `/internal/chat-responses` | 상담 응답 DTO |
| POST | `/internal/recommendations` | 최초 안내 응답 DTO |

두 POST는 `X-Chatbot-Token` 인증과 camelCase·엄격한 금액 타입·질문/이력 상한을 적용합니다. FastAPI 내부 응답에는 사용자용 공통 봉투나 `errorId`를 적용하지 않습니다. 사용자용 `{success,data,meta,error}` 변환과 500·503의 `error.errorId` 생성은 Spring 책임이며 실제 연동은 미완료입니다.

| 조건 | 현재 응답 |
|---|---|
| 서버 토큰 미설정·빈 값·공백 | 503 `AUTH_NOT_CONFIGURED`, 시작 로그에 값 없이 알림 |
| 헤더 누락·불일치 | 401 `INTERNAL_UNAUTHORIZED` |
| 인증 통과 후 유효하지 않은 DTO | 422 `VALIDATION` |
| 정상 인증·유효 입력 | 503 `RAG_NOT_READY` |

기본 의존성은 `UnavailableRetriever`이므로 실제 요청에서 Ollama를 호출하거나 가상 답변을 반환하지 않습니다. 검색기·모델 대체는 테스트에서만 수행합니다. 향후 검색 성공 후 검증된 귀속연도 근거가 없으면 `INSUFFICIENT_EVIDENCE`를 반환하도록 서비스 경로가 구현되어 있으며, 현재 기본 검색 미준비 응답과 구분합니다.

모델/서비스 대기 제한은 현재 코드상 45/50초입니다. 기존 Spring 60초와의 배치는 초기 제안값이며 실제 적절성·벽시계 시간·전체 HTTP 처리·추론 취소는 미검증입니다. 50초는 업로드·검증·직렬화까지 포함한 네트워크 전체 제한이 아닙니다. 동기 추론은 제한 응답 이후에도 계속될 수 있고 실제 종료까지 프로세스별 모델 슬롯 1개를 점유합니다. 다중 워커 전체 제한·강제 종료는 미구현입니다.

정확한 DTO·오류·확정 정책과 보류 사항은 [API 계약 문서 상단](docs/03_API_계약_초안.md)을 따릅니다. 아래쪽 초기 설계 기록을 현행 계약과 혼동하지 않습니다.

## 7. Ollama 준비와 수동 연결 확인

Ollama가 설치되어 있어야 합니다. 로컬 서버가 실행 중이 아니라면 별도 터미널에서 실행하고 모델을 준비합니다.

```powershell
ollama serve
```

다른 터미널:

```powershell
ollama pull gemma3:4b
ollama list
# chatbot/에서 실행
.\.venv\Scripts\python.exe -c "from app.llm.ollama import OllamaService; print(OllamaService().generate('Reply with just OK.'))"
```

모델 다운로드는 로컬 준비 작업입니다. 과거 실제 호출에서 `OK`를 확인했지만 이번 문서 정리에서 실행하지 않았습니다.

`OllamaService.generate()`는 `ChatOllama.invoke()`를 호출합니다. 연결 3초·HTTP 읽기 대기 60초이며 전체 생성 시간의 절대 상한은 아닙니다. 빈 질문은 호출하지 않고 연결 불가·시간초과·모델 없음·서버/응답 오류를 분류합니다. 원본 서버 오류·질문·답변을 로그에 남기지 않고 호출 구간의 외부 추적을 비활성화합니다. 이 직접 호출은 세법 정확성이나 실제 RAG 통합을 검증하지 않습니다.

## 8. PDF 8개 오프라인 전처리

원본 위치는 `app/data/raw/`이며 법령 6개, 2025년 귀속 연말정산 안내서, 2026년 개정세법 요약으로 총 8개입니다. 문서 제목·시행일과 실제 적용 귀속연도는 별도로 검증합니다.

```powershell
.\.venv\Scripts\python.exe scripts/preprocess_documents.py --input-dir app/data/raw --verify-reproducibility
# 같은 입력/설정의 완료 결과를 해시 검증 후 재사용
.\.venv\Scripts\python.exe scripts/preprocess_documents.py --input-dir app/data/raw --reuse
```

기본 입력 기대 수는 8개입니다. 원본은 읽기만 하며 출력은 `data/processed/<입력·설정 버전 해시>/`에 분리합니다. 기존 출력은 기본 거부하고 미완료 결과를 자동 덮어쓰기·삭제하지 않습니다. 새 설정·파이프라인 버전은 다른 경로를 사용합니다.

`manifest.json`, `report.json`, 문서별 pages/chunks/excluded/review 자료에 메타데이터·원문·좌표를 보존합니다. 법령·안내서·개정 요약을 구조별로 청킹하고 빈 페이지·실패·의심 중복·표 대응을 보고합니다. 재현성 검증은 두 번 처리한 청크·품질 보고서를 비교합니다.

모든 청크는 수동 검수 대기로 생성되며 자동으로 검색 사용 가능 상태가 되지 않습니다. 적용 귀속연도는 미검증 null/false입니다. `--max-chars`는 항/호 추가 분할 후보 상한으로 검색 성능으로 확정된 값이 아닙니다. OCR·임베딩·검색은 추가하지 않았으며 전처리는 FastAPI 시작 경로와 분리되어 있습니다.

## 9. 검수 대기열과 승인 자료 내보내기

기존 PDF·청크·manifest를 변경하지 않고 별도 검수 자료를 만듭니다. 다음 실행 ID는 기존 전처리 기록의 예시이며 해당 로컬 결과가 있어야 합니다.

```powershell
$processedRun = 'data/processed/8417ec42dc78a0194dbc5edc18dd8aa68ed1f5fd1566f0e5326e57ade0b612f3'
.\.venv\Scripts\python.exe scripts/build_review_queue.py --processed-dir $processedRun --raw-dir app/data/raw

# 검토자가 준비한 실제 v3 작업 원장·공식 근거 폴더 경로로 교체합니다.
$reviewLedger = '검토자가_준비한_v3_작업원장.jsonl'
$evidenceRoot = '공식근거스냅샷폴더'
.\.venv\Scripts\python.exe scripts/export_approved_chunks.py --processed-dir $processedRun --raw-dir app/data/raw --ledger $reviewLedger --evidence-root $evidenceRoot
```

검수 출력은 `data/processed/reviews/`, 내보내기는 `data/processed/exports/`의 해시별 경로에 저장하며 기존 출력을 덮어쓰지 않습니다. 초기 원장은 HOLD이고 승인 0건도 정상입니다. 평가용 `userAnswerAllowed=false` 자료는 사용자 답변 근거로 사용하지 않습니다.

운영 내보내기는 **review-policy-v3**만 허용합니다. 승인 대상별 원문 영역·법령 적용·사용 범위·공식 RULE/APPLICATION 근거·필수 문맥·조건·해시·최신 보류/반려/회수 이력을 검증합니다. v2 원장을 자동 승격하지 않으며 기록상 기존 3,133개 입력은 모두 `POLICY_VERSION_MISMATCH`로 제외되었습니다. 출력은 `approved-context-v3`의 `regions[]`이며 검색 어댑터·Elasticsearch·API 연결은 미구현입니다.

2025 안내서·종전/개정 혼합 요약·좌동은 현재 v3 운영 출력에서 보류합니다. 조건·문맥 목록의 법적 완전성, 공식 자료 취득 진위·이용 조건·개별 공제 자격은 사람 확인이 필요합니다. 검토자 로그인·전자서명·배포 색인/캐시 회수 동기화는 미구현입니다. 실제 VERIFIED/APPROVED 반영은 별도 승인 대상이며 Mock 승인은 실제 자료 승인과 무관합니다.

상세 형식·신뢰 경계는 [현행 v3 승인 게이트](docs/decisions/2026-11-11_승인게이트보완.md), 검수 대기열 배경은 [검수·검색 승인 설계](docs/decisions/2026-11-11_청크검수및검색승인.md)를 참고합니다.

## 10. 테스트와 코드 검사

가상환경 활성화 후 `chatbot/`에서 실행합니다.

```cmd
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

코드 형식을 실제로 변경하는 명령은 다음과 같습니다.

```cmd
python -m ruff format .
```

단위 테스트는 외부 LLM 없이 실행하도록 모델·검색기를 대체합니다. 마지막 기록의 171개 통과는 실제 Elasticsearch·Spring·Oracle·세법 정확성 검증 완료를 뜻하지 않습니다. 이번 문서 작업에서는 위 명령을 재실행하지 않았습니다.

## 11. 남은 작업과 미합의 설계

- 실제 공식 근거 확보, 수동 구조·법령 적용·사용 승인, 복잡한 표·각주·조건·문맥 검수
- 승인 자료를 보존하는 검색 어댑터, Elasticsearch BM25 매핑·색인·검색·평가·회수 동기화
- 실제 RAG 답변·출처·세법 및 생성 숫자 품질 검증
- Spring·React HTTP 연동, 회원 소유권·대화/추천 저장·실패·시간초과 통합 검증

출처 보존용 JSON CLOB 컬럼과 추천 작업 영구 상태·유일 작업키는 **제안 설계**이며 DB·ERD에 구현되거나 합의 완료된 것으로 취급하지 않습니다. 타인 데이터 접근 403/404 충돌은 보류 상태이고 504 정책·사용자용 응답 필드 확장도 임의 확정하지 않습니다. 임베딩 모델·벡터·하이브리드 검색은 BM25 품질 측정 후 별도 결정합니다.

최초 안내와 후속 상담·이력 조회는 구현 대상입니다. 별도 적용 세법 설명 카드를 만들지 않고 F-05-02를 챗봇 질의응답에 통합하는 것은 사용자 결정이며 기능명세서의 팀 협의·변경 기록과 구분합니다.

## 12. 문서 관리와 관련 문서

새 개발 내용은 기존 관련 항목을 갱신합니다. AGENTS·README 끝에 날짜별 절을 계속 추가하지 않고 작업·테스트 이력은 history에 기록합니다. 과거 이력은 현재 상태에 맞춰 고치지 않습니다.

| 문서 | 용도 |
|---|---|
| [AGENTS.md](AGENTS.md) | 현재 유효한 개발·보안·승인·Git 규칙 |
| [history.md](docs/history.md) | 날짜별 작업·변경·검증 기록 |
| [확정사항과 출처](docs/01_확정사항과출처.md) | 결정 출처와 미결정 사항 |
| [API 계약](docs/03_API_계약_초안.md) | 상단의 현행 상세 계약과 보류 사항 |
| [RAG 설계](docs/04_RAG_설계.md) | 상세 전처리·검수 설계 |
| [단계별 작업계획](docs/05_단계별작업계획.md) | 후속 구현 계획 |
| [실행환경 및 검증](docs/06_실행환경_및_검증.md) | 실행환경 참고 |
| [decisions](docs/decisions/) | 기술 결정과 근거 |
| [.env.example](.env.example) | 환경변수 안내 |
| [pyproject.toml](pyproject.toml) | Ruff·pytest 설정 |

기능 기준은 팀 [희망환급 기능명세서 v1.13](https://docs.google.com/spreadsheets/d/1qW5xjOhPqrWkCn9KLUUbylKfsFJCacfOAgBiXm27v9w/edit), ERD v4.1, 팀 공식 API 명세서입니다. 로컬 기능명세 PDF의 정확한 v1.13 동일성은 기존 기록상 미확인입니다. 기존 설계 문서의 초기안과 후속 확정 사항을 구분하고 충돌은 확인 후 해소합니다.
