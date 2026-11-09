# 04. LangChain + Ollama + Elasticsearch RAG 설계

## 선택 이유
- 외부 LLM 사업자 API 대신 `Ollama`로 `gemma3:4b` 로컬 실행. **FastAPI는 Ollama 로컬 HTTP API를 호출**한다. '로컬 LLM 모델'과 '로컬 API 호출'은 동시에 맞는 표현.
- LangChain은 `ChatOllama`, `ChatPromptTemplate`, `Document`, 텍스트 분할 도구 등 연결 작업에 선택적으로 도입. 모든 로직을 추상화하거나 agent/tool calling을 초기 도입하지 않는다.
- 공식 세법 전문 검색은 Elasticsearch BM25부터 시작. 필요 시 동의어 사전 → 벡터/하이브리드 검색으로 성능 비교. LangChain에 **임베딩 필수 아님**.
- Oracle에는 회원·계산·대화 저장. 법령 PDF 원본은 별도 보관하고, **조문별 텍스트와 메타데이터**만 Elasticsearch 색인.

## RAG 원본 PDF 7종
1. `소득세법(법률)(제21221호)(20260701).pdf`
2. `소득세법 시행령(대통령령)(제36737호)(20261001).pdf`
3. `소득세법 시행규칙(재정경제부령)(제00033호)(20260701).pdf`
4. `조세특례제한법(법률)(제21467호)(20260918).pdf`
5. `조세특례제한법 시행령(대통령령)(제36587호)(20260918).pdf`
6. `조세특례제한법 시행규칙(기후에너지환경부령)(제00056호)(20260918).pdf`
7. `2025년 원천징수의무자를 위한 연말정산 신고안내.pdf`

파일명에 포함된 시행일이나 문서 표제는 **적용 귀속연도에 대한 법적 확정이 아님**. 특히 2025 귀속 안내서는 2026 귀속의 확정 근거로 사용하지 않는다. 법령의 부칙·적용례를 검토해야 한다.

## PDF 처리 파이프라인
1. 원본/출처/수집일/해시/발행·시행·귀속연도 검증 상태를 manifest에 기록.
2. PyMuPDF 또는 LangChain의 `PyMuPDFLoader`로 텍스트 추출. 표·머리글·각주·페이지 표시 오인 검수.
3. 법령은 **제○조 → 항 → 호** 우선 청킹. 제목/목차/부칙이 본문에 섞이지 않도록 별도 규칙 작성. 국세청 안내는 절·제목·문단 기준.
4. `Document(page_content, metadata)` 구성 후 JSONL로 저장.
5. `tax_law_index` 색인. 기존 카드 가맹점 분류 인덱스에 절대 혼합하지 않음.
6. BM25 검색 테스트: 월세·카드 소득공제·중소기업 취업자 감면.
7. 검색 결과 법령명·조문번호·출처 파일·페이지·시행일·귀속연도 검증 상태 반환.
8. `ChatPromptTemplate`로 질문·검색 원문·계산 결과·설명 규칙을 결합하여 `ChatOllama` 호출.
9. 생성 답변의 수치·법령 인용을 검증. 출처는 검색 메타데이터에서만 사용. 근거 없으면 모르겠다고 답변.

## 인덱스 예시 (데이터 모형, 실제 조문 아님)
```json
{
  "chunkId": "income-tax-law_001_v1",
  "documentTitle": "소득세법",
  "documentType": "LAW",
  "article": "제00조(예시)",
  "content": "검수된 조문 원문을 삽입",
  "sourceFile": "income_tax.pdf",
  "sourceUrl": null,
  "page": null,
  "effectiveDate": null,
  "applicableTaxYear": null,
  "applicabilityVerified": false
}
```
- `applicableTaxYear=null` 또는 검증 실패 상태는 그 연도에 적용되는 확정 근거로 단정하지 않는다.
- JSON/SQL에서 사용한 예시 법령 조문을 실제 근거로 화면에 표시하지 않는다.

## 구현시 모듈 후보 (`chatbot/AGENTS.md`의 목표 구조에 맞춤)
```text
chatbot/app/
  main.py                  (기존)
  api/health.py            (기존)
  api/chat.py              (신규, 내부 chat/recommendation 라우터)
  schemas/chat.py          (신규 Pydantic)
  services/chat_service.py (신규, orchestration)
  llm/ollama.py            (신규 ChatOllama)
  rag/loader.py            (신규 PyMuPDF)
  rag/chunker.py           (신규 조문 분할)
  rag/retriever.py         (신규 Elasticsearch 검색)
  rag/chain.py             (신규 PromptTemplate와 연결)
  core/config.py           (신규 설정·토큰)
chatbot/scripts/index_documents.py
chatbot/data/raw/          (원본; Git 업로드 여부는 팀 정책)
chatbot/data/processed/    (생성물; 버전·검증 기록)
chatbot/tests/
```
- 파일 구조는 제안이며 구현 상황에 따라 **필요한 모듈만 추가**한다. 빈 파일을 대량 생성하지 않는다.

## LangChain의 역할과 경계
- LangChain = 공통 연결 코드 단순화. **정확한 법령 검색·귀속연도 검증·세액 계산을 자동 보증하지 않음**.
- 모델이 세액을 재계산하거나 DB에 직접 쓰지 않음. 권한 판단·최종 법적 효력도 LLM에 맡기지 않음.
- 문서 내 지시문은 프롬프트 인젝션 위험으로 취급. 인증·민감정보 로깅/트레이싱 비활성화 또는 비식별화.

## 품질 지표
- 질문별 '관련 조문 검색 성공 여부', '인용 조문 실제 존재', '귀속연도 오용 여부', '계산값 불변', '시간초과 빈도'를 기록.
- 처음에는 "월세액 세액공제란?"을 실제 검색→출처 표시→모델 답변까지 관통시키고 다른 공제로 확장.
