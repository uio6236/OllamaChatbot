# 04. LangChain + Ollama + Elasticsearch RAG 설계

## 선택 이유
- 외부 LLM 사업자 API 대신 `Ollama`로 `gemma3:4b` 로컬 실행. **FastAPI는 Ollama 로컬 HTTP API를 호출**한다. '로컬 LLM 모델'과 '로컬 API 호출'은 동시에 맞는 표현.
- LangChain은 `ChatOllama`, `ChatPromptTemplate`, `Document`, 텍스트 분할 도구 등 연결 작업에 선택적으로 도입. 모든 로직을 추상화하거나 agent/tool calling을 초기 도입하지 않는다.
- 공식 세법 전문 검색은 Elasticsearch BM25부터 시작. 필요 시 동의어 사전 → 벡터/하이브리드 검색으로 성능 비교. LangChain에 **임베딩 필수 아님**.
- Oracle에는 회원·계산·대화 저장. 법령 PDF 원본은 별도 보관하고, **조문별 텍스트와 메타데이터**만 Elasticsearch 색인.

## RAG 원본 PDF 8종
1. `소득세법(법률)(제21221호)(20260701).pdf`
2. `소득세법 시행령(대통령령)(제36737호)(20261001).pdf`
3. `소득세법 시행규칙(재정경제부령)(제00033호)(20260701).pdf`
4. `조세특례제한법(법률)(제21467호)(20260918).pdf`
5. `조세특례제한법 시행령(대통령령)(제36587호)(20260918).pdf`
6. `조세특례제한법 시행규칙(기후에너지환경부령)(제00056호)(20260918).pdf`
7. `2025년 원천징수의무자를 위한 연말정산 신고안내.pdf`
8. `2026년 연말정산 관련 개정세법 요약.pdf`

원본의 실제 위치는 `chatbot/app/data/raw/`이며 파일명을 변경하지 않는다.
개정 요약은 2025 안내서의 대체본이 아닌 보완 자료다. AGENTS.md의 기존 원본 수 표기는
사용자 승인 없이 수정하지 않았으며, 8개로 변경할 것을 제안한다.

## 2026-11-10 오프라인 전처리 구현

- PyMuPDF 1.26.7, Python 3.11.9를 사용한다. `requirements-preprocess.txt`로 의존성을 분리했다.
- `scripts/preprocess_documents.py --input-dir app/data/raw --verify-reproducibility`로 실행한다.
- 입력/설정/Python/PyMuPDF 버전으로 계산한 실행 ID 하위에 `chatbot/data/processed/<runId>/`를 만든다.
  동일 경로가 있으면 기본 거부한다. `--reuse`는 manifest 완료 여부와 모든 생성물의 SHA-256을 확인한 뒤 재사용하며 다시 쓰지 않는다.
  `--verify-reproducibility` 최초 실행은 모든 문서를 두 번 실제 처리해 청크 전체와 품질 보고서가 같은지 비교한다.
- `*.pages.json`에 원본 줄·페이지·좌표·글자 크기·표 행/셀·이미지 존재 여부·추출 오류를 남긴다.
  빈 페이지와 부분 추출 실패도 결과에서 빠지지 않는다. OCR은 하지 않는다.
- 법령은 본문/부칙·장/절/관·조문을 구분하고 조문을 페이지를 넘어 연결한다. 항·호·목 표지는 원문 줄과 함께 보존한다.
  장문은 항/호 경계를 우선하며 원문 줄을 강제 절단하지 않는다. 임계값 초과 구조는 OVERSIZE_STRUCTURE_PRESERVED로 표시한다.
- 안내서는 제목·문단 줄·표 좌표를 보존한다. 같은 제목 아래 인접 페이지 청크는 continuationCandidates로 연결하지만
  계속 표/각주의 의미 연결은 수동 검토 전 확정하지 않는다. 표를 무리하게 합치지 않는다.
- 개정 요약은 좌우 항목을 먼저 나누고 내부 종전/개정 열을 분리한다. 5·12쪽의 원형번호 하위 항목은
  각자의 취지·비교표·적용례로 나눈다. 6쪽 월세 항목은 공통 amendmentGroupId 아래 두 세부 청크로 보존한다.
  같은 개정 내용이라도 소득 유형별·페이지별 출처는 별도로 유지한다.
- 표 셀은 행별 좌표를 사용하여 병합/누락 자리의 null까지 보존한다. 좌동을 풀어 쓰거나 금액·날짜를 보정하지 않는다.
- 확실한 법령 반복 머리글/바닥글·공백만 청킹 대상에서 제외하고 제외 원문과 사유도 `*.excluded.jsonl`에 남긴다.
  목차나 반복 본문은 광범위한 정규식으로 삭제하지 않으며 검토 대상으로 보존한다.

### 메타데이터 및 검수 경계

`chunkId`, `documentTitle`, `documentVersion`, `documentType`, `article`, `sourceFile`, `sourceUrl`,
`pageStart`, `pageEnd`, `effectiveDate`, `applicableTaxYear`, `applicabilityVerified`를 유지한다.
페이지는 PDF 기준 1부터다. sourceSpans에는 실제 페이지/줄 ID/좌표/원문을 남긴다.
documentVersion은 원본 SHA-256이다. ID에는 원본·설정·구조 경로·원본 줄 ID·부분 순서·내용 해시가 포함되고
시각·절대경로·무작위 값은 포함하지 않는다. 파이프라인 로직 변경 시 버전을 갱신해야 한다.

법령 버전 표기 시행일은 documentEffectiveDate로 보존하며 모든 조문의 effectiveDate로 복사하지 않는다.
문서 표제 연도(documentLabelYear), 확인 가능한 발행연도(publicationYear), 자료 귀속연도(declaredTaxYear)를 분리한다.
문서 속 생성 시각을 발행일로 간주하지 않는다. 적용연도와 조문 시행일은 검증 전 null, applicabilityVerified=false다.
확인되지 않은 공식 URL은 null이다. 2025 안내서 값을 2026 기준으로 승격하지 않는다.

개정 자료에는 sectionIncomeType/incomeType, amendmentTitle/subAmendmentTitle/amendmentGroupId,
amendmentPurpose, previousRule/revisedRule, applicationNote, relatedArticles, comparisonRows를 보존한다.
행별 대응은 좌표상 후보이며 병합 셀의 의미나 좌동의 적용 범위는 자동 확정하지 않는다.
원문에 적용례 표제가 없는 항목은 APPLICATION_NOTE_NOT_EXPLICIT로 보류하며 표 본문·원문은 남긴다.

automaticChecksPassed는 입력 줄 추적·페이지 상태·Source DTO 호환성 등의 기계적 검증이다.
사람 검수 통과 또는 법률 정확성 인증이 아니다. 모든 청크의 reviewStatus는 PENDING,
reviewRequired=true로 생성하며 이번 실행에서 humanReviewPassed/retrievalReady는 0이다.
`report.json`은 누락 줄·중복 할당 줄·동일 내용 후보·표·페이지 오류·문서별 청크 수를 구분한다.
LangChain Document 및 기존 Source 변환은 독립 어댑터이고 실제 API 검색기에는 연결하지 않는다.

### 크기 후보 비교

실제 법령 6종의 각 첫 5쪽을 사용하여 항/호 경계 분할 후보를 비교했다.
1500/2500/4000자에서 청크 수는 소득세법 시행규칙 24/24/24, 시행령 21/19/19,
법률 20/19/19, 조특법 시행규칙 16/14/13, 시행령 16/14/13, 법률 15/13/13이었다.
현재 CLI 기본값 2500자는 중간 후보이며 검색 성능 검증으로 확정한 값이 아니다.
겹침은 0이며 상위 조문 정보는 메타데이터로 유지한다. 개정 비교 묶음과 안내서 표는 길이 때문에 강제 분리하지 않는다.

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
