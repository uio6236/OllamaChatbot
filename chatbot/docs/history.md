### [2026-11-09] ChatOllama와 로컬 Gemma 3 4B 최소 연결
- **작업 내용**: `app/core/config.py`와 패키지 초기화 파일에 OS 환경변수 설정을 추가하고, `app/llm/ollama.py`와 패키지 초기화 파일에 ChatOllama 호출 및 오류 분류를 구현했다. `tests/test_ollama.py`에 Mock 테스트 18개를 추가했다. `requirements.txt`에 검증한 의존성을 기록하고 `.env.example`, `README.md`를 갱신했다. 기존 `app/main.py`, Health 라우터와 Health 테스트는 변경하지 않았다.
- **변경 사유**: RAG나 외부 API 계약을 추가하기 전에 로컬 모델 호출과 실패 처리를 독립적으로 검증하기 위함이다. 외부 추적은 호출 구간에서 비활성화하고 원본 질문·응답 및 서버 오류 내용을 로그에 남기지 않는다.
- **검증 결과**: Python 3.11.9, `langchain-ollama==1.1.0`(패키지 Python 요구사항 >=3.10,<4), `ollama==0.6.3`, `httpx==0.28.1`, `langsmith==0.14.17`, `langchain-core==1.7.6` 환경에서 검증했다. `chatbot/`의 `.venv/Scripts/python.exe`로 `-m ruff check .` 통과, `-m ruff format --check .` 통과, `-m pytest -v` 19개 통과, `-m pip check` 충돌 없음. Mock 검증은 환경변수 전달·빈 질문·연결 실패·연결/읽기 시간초과·모델 없음·서버 오류·잘못된 응답·외부 추적 비활성화를 포함한다. `ollama list`에서 `gemma3:4b`를 확인했고 `OllamaService().generate('Reply with just OK.')` 실제 호출 결과 `OK`를 확인했다.
- **실행 환경**: 검증용 `chatbot/.venv`를 생성했다(Git 제외). 최초 패키지 다운로드는 네트워크 제한으로 실패했고, 승인된 재시도에서 설치했다. `.env` 자동 로딩은 추가하지 않았으며 OS 환경변수를 사용한다. 모델 연결은 서비스 생성 시 준비하고 FastAPI 시작 시 호출하지 않는다.
- **미해결 사항**: HTTP 읽기 제한 60초는 전체 생성 시간 상한이 아니다. 실제 장애·동시성·성능, 세법 답변 품질, 내부 서비스 인증은 미검증이다. 서버 오류 404는 모델 없음으로 분류하므로 잘못된 Ollama 기본 경로도 설정 확인이 필요하다. API·RAG·Elasticsearch·Oracle 통합은 미구현이며 이번 범위에 포함하지 않는다.
- **다음 작업**: 내부 API 경로·DTO·인증 헤더·오류 매핑·시간제한 계약을 문서화한 뒤 별도 승인 범위에서 구현한다. RAG 및 Backend/Frontend 통합은 후속 단계로 진행한다.
- **Git**: 커밋·Push를 수행하지 않았다. 작업 전부터 있던 AGENTS 및 docs/prompts 변경은 보존했다.
