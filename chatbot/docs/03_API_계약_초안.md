# 03. API 계약 — 2026-11-09 팀 합의 반영

## 최신 확정 정책 및 이번 구현 (2026-11-09 사용자 승인)

이 절이 아래의 초기 설계안보다 우선한다. 사용자용 정책과 내부 API 구현 상태를 구분한다.

### 확정 정책
- 내부 API는 `POST /internal/chat-responses`, `POST /internal/recommendations`. 성공 HTTP 200의 단순 JSON DTO이며 공통 봉투와 `errorId`를 사용하지 않는다. `/health`는 기존 `200 {"status":"OK"}`이며 인증·RAG 준비 상태를 보증하지 않는다.
- `CHATBOT_API_TOKEN` OS 환경변수와 `X-Chatbot-Token`을 검증한다. 서버 토큰 누락·빈 값·공백이면 503 `AUTH_NOT_CONFIGURED`, 클라이언트 누락·불일치면 401 `INTERNAL_UNAUTHORIZED`. 시작 시 서버 토큰 미설정을 값 없이 오류 로그로 알리며 Health를 위해 서버 자체는 시작한다. `.env` 자동 로딩은 없다.
- RAG 검색은 미구현이다. 기본 의존성은 정상 인증·유효 입력에 503 `RAG_NOT_READY`를 반환하고 Ollama를 호출하지 않는다. Mock 검색기·모델은 테스트에서만 주입한다. 실제 법령 근거가 있는 것처럼 답변하지 않는다.
- 사용자용 장애·시간초과는 후속 Spring에서 503 `CHATBOT_UNAVAILABLE`로 변환한다. 공통 `GlobalExceptionHandler`가 봉투와 `errorId`를 생성한다. 이번에는 Spring을 수정하지 않았다.
- AI 생성 성공 시에만 USER와 AI를 한 짧은 Oracle 트랜잭션으로 저장한다. AI 대기 중 DB 트랜잭션을 유지하지 않는다. 이번 FastAPI에는 DB 접근이 없다.
- 계산 결과와 입력·상세를 먼저 커밋하고 별도 흐름에서 최초 안내를 생성한다. 실패해도 계산을 롤백하지 않는다. 추천 조회 GET은 조회만 한다. 검증된 절세액이 없으면 `SAVING_AMOUNT=NULL`; 내부 추천 응답에는 절세액 필드가 없다.

### 구현한 내부 DTO
JSON은 camelCase만 허용하고 알 수 없는 필드·문자열/불리언/실수 금액을 거부한다.

```json
{"questionType":"GENERAL","message":"공제의 개념을 설명해주세요.","taxYear":2026,"taxResult":null,"history":[]}
```

- 상담 요청: `questionType` GENERAL/TAX_RESULT, `message` 1~1000자(공백 제거 후), `taxYear` 정수 2000~2100, `taxResult`, `history` 필수. GENERAL에는 계산 결과 금지, TAX_RESULT에는 필수.
- `taxResult`: 양의 `predictionId`, 0 이상 정수 `withheldTax`·`decidedTax`, 부호 있는 정수 `expectedRefund`, 최대 100개 `details`. 금액은 NUMBER(12) 범위로 제한한다. 존재·소유권은 Spring에서 확인하며 FastAPI가 확인한 것으로 표시하지 않는다.
- `details[]`: `typeCode`(30자), `typeName`(50자), `kind`(INCOME_DEDUCTION/TAX_CREDIT/TAX_REDUCTION/CARD/CARD_RULE), `baseAmount`, `deductionAmount`, nullable `sourceNote`(200자). 음수 공제 조정액을 보존한다.
- `history[]`: `role` user/assistant, `content` 1~4000자. 최근 최대 10개, 총 12000자. Spring이 MESSAGE_ID 오름차순으로 구성하며 현재 질문은 중복 포함하지 않는다.
- 추천 요청: `taxYear`, 필수 `taxResult`. 응답은 `status`, `recommendations[]`. 최초 버전은 일반 안내 한 건으로 `typeCode:null`, `content`, `model`, `sources`를 반환하도록 구성한다. 모델이 TYPE_ID·절세액을 선택하지 않는다.
- 상담 응답: `status`, `answer`, `model`, `sources`. status는 ANSWERED/INSUFFICIENT_EVIDENCE. 정상 검색 결과가 비거나 귀속연도 검증 자료가 없으면 모델을 호출하지 않고 제한 안내를 반환한다. 상담 model=null, 추천 recommendations=[]이다. 기본 RAG 미구현과 검색 성공 후 근거 부족은 다르다.
- `sources[]`: `chunkId`, `documentVersion`, `documentTitle`, nullable `article`, `sourceFile`(절대경로 금지), nullable `sourceUrl`, `pageStart`, `pageEnd`(1부터), nullable `effectiveDate`, nullable `applicableTaxYear`, `applicabilityVerified`. 검색기 메타데이터에서만 구성한다. 실제 Elasticsearch 결과 연결은 미검증이며 현재 테스트 자료는 가상 자료다.

### 내부 오류와 시간제한
오류는 `{"code":"RAG_NOT_READY","message":"법령 검색 기능이 준비되지 않아 답변을 생성할 수 없습니다."}`처럼 두 필드만 사용한다. 요청 검증 실패는 422 VALIDATION이며 입력값·기본 Pydantic 상세를 노출하지 않는다. 모델/검색 오류는 503 OLLAMA_UNAVAILABLE, OLLAMA_MODEL_NOT_FOUND, OLLAMA_INVALID_RESPONSE, OLLAMA_TIMEOUT, RAG_UNAVAILABLE, RAG_TIMEOUT 등으로 분류한다. 전체 처리 대기는 503 REQUEST_TIMEOUT, 처리 중 모델 슬롯은 MODEL_BUSY이다. 예상 밖 오류는 500 SERVER_ERROR로 안전하게 반환한다. FastAPI가 사용자용 errorId를 만들지 않는다.

모델 대기 45초 < FastAPI 서비스 처리 대기 50초 < 기존 Spring 대기 60초는 초기 제안값이다. 서비스는 짧은 Mock 작업으로 대기 제한 동작을 검증한다. 50초는 요청 본문 업로드·검증·응답 직렬화까지 포함한 네트워크 전체 제한이 아니다. 실제 45/50초 벽시계 검증·성능·Ollama 추론 취소·Spring 연동은 미검증이다. 기존 ChatOllama의 HTTP 연결 3초/읽기 60초는 변경하지 않았다.

동기 모델 호출은 별도 스레드에서 대기한다. 시간초과 응답 후에도 실제 호출은 계속될 수 있다. 실제 작업이 끝날 때까지 프로세스별 모델 슬롯 1개를 점유하여 추가 추론을 차단한다. 여러 서버 워커 전체의 동시성 제한·추론 강제 종료는 구현하지 않았다. 프롬프트는 재계산을 금지하지만 생성 문장의 모든 숫자·법률 해석을 자동 검증하는 기능은 아직 없다.

### 충돌·보류: 승인 없이 적용하지 않음
1. 사용자 결정은 타인 데이터 접근 403 FORBIDDEN이나 최신 PDF는 404 NOT_FOUND이다. 팀 합의/개정 전 Backend 공통 권한 코드는 변경하지 않는다.
2. 최신 PDF는 성공 200 통일, 문의 답변 PUT, 남의 데이터 404로 정리되었다. 아래 초기 문서의 204 예외·PATCH 불일치·403 접근 설명은 구시점 기록이며 현행 PDF 규칙으로 사용하지 않는다.
3. 출처는 대화와 추천에 영구 보존한다. 최소 ERD 변경안으로 CHAT_MESSAGE 및 RECOMMENDATION 각각에 JSON CLOB 컬럼을 추가하는 방식을 우선 제안한다. `schemaVersion`과 sources 배열을 스냅샷으로 저장한다. 문서명·조문·페이지·원본 해시 버전·적용 귀속연도·검증 여부를 보존한다. 원문 재현에는 원본 버전 보관 또는 인용문 스냅샷도 필요하다. 별도 출처 테이블은 FK/출처별 검색·통계에 유리하나 변경 범위가 더 크다. CONTENT에 JSON을 섞는 방식은 기존 본문 계약을 깨므로 권장하지 않는다. DDL·DB·ERD 변경은 별도 승인 대상이며 이번에 구현하지 않았다.
4. 추천 생성 작업은 계산 결과별 유일 작업키와 PENDING/RUNNING/COMPLETED/FAILED 상태·시도 횟수·처리 기한·실패 코드·작업 버전을 가진 영구 상태 구조를 제안한다. 짧은 트랜잭션으로 선점하고 AI 호출은 밖에서 수행한다. 추천 저장과 COMPLETED 전환을 함께 커밋하며 재시도 전 작업 버전을 검사한다. 저장 직전 부모 계산 행 잠금/기존 추천 재확인으로 중복을 방지하는 안이다. 새 테이블/컬럼과 사용자용 상태 조회 계약은 별도 합의가 필요하며 이번에는 구현하지 않았다.
5. 사용자용 sources 필드 확장·영구 요청키·안전한 재시도·최초 안내 작업 재시작 복구는 후속 Backend/DB 작업이다. 실패 시 임의 추천이나 0원 절세액을 저장하지 않는다.
6. 기능명세서 로컬 PDF의 F-05-01을 확인했다. 해당 PDF 본문에 v1.13 표시는 없어 정확한 버전 동일성은 미확인이다. 내부 API는 계산 결과 보유 여부를 DB로 확인하지 않는다.

---

## 초기 설계 기록 (위 최신 확정 정책과 충돌 시 적용하지 않음)

> 기준: `희망환급_API_공통_규칙.pdf` 7쪽, 변경 이력 2026-11-09. **사용자용 응답 봉투·오류 코드·500/503 errorId는 팀 합의 사항**. 내부 FastAPI 경로·DTO·토큰 헤더는 기능 담당자 설계 제안으로 구분한다. 실제 구현 여부는 현 브랜치 코드를 확인한다.

## 1. React ↔ Spring Boot 사용자용 API: 팀 공식 규칙

- URI `/api/`로 시작, 소문자 복수형 명사, 여러 단어는 `-`, 사용자 회원번호를 URI/본문에 넣지 않는다. Spring Security 인증정보로 회원을 식별한다. 인증 구현 전 `X-Member-Id`는 **임시 개발용**이며 정식 인증 후 제거한다.
- JSON camelCase; 금액은 원 단위 정수; 날짜 `YYYY-MM-DD`, 일시 `YYYY-MM-DDTHH:mm:ss`; 저장용 Y/N은 문자열.
- GET 조회, POST 새 결과 생성, PUT 전체 저장, DELETE 삭제. PATCH는 일반 규칙상 미사용이나 공식 PDF 6쪽 관리자 문의 답변에는 PATCH 예시가 있어 **팀 공통 문서 불일치**로 남긴다.
- **성공·실패 응답 모두 공통 봉투**: `success`, `data`, `meta`, `error`. 본문 없는 HTTP 204 예외는 팀 구현 확인 필요.

성공 단건 (`data` 내부는 예시):
```json
{"success":true,"data":{"messageId":15,"sender":"AI","content":"안내...","createdAt":"2026-11-09T15:00:00"},"meta":null,"error":null}
```
성공 목록(페이지 정보는 **실제 페이지네이션 사용 시**):
```json
{"success":true,"data":[],"meta":{"page":1,"size":20,"total":0,"totalPages":0},"error":null}
```
실패 403:
```json
{"success":false,"data":null,"meta":null,"error":{"code":"FORBIDDEN","message":"접근 권한이 없습니다."}}
```
실패 503(서버 오류 추적 ID 포함):
```json
{"success":false,"data":null,"meta":null,"error":{"code":"CHATBOT_UNAVAILABLE","message":"AI 상담 서비스에 잠시 연결할 수 없습니다.","errorId":"a3f9c2d1"}}
```
위 errorId는 **설명용 예시**. 실제 값은 팀 `GlobalExceptionHandler`가 오류마다 생성하고 서버 로그에 동일 번호를 남긴다. 오류가 아닌 성공 응답과 400/401/403/404/405/409/415 오류에는 errorId를 붙이지 않는다. PDF에 504의 errorId 정책은 정의되지 않았으므로 **별도 합의 전 임의 적용 금지**.

### 사용자용 챗봇 URI (팀 PDF 4~5쪽)
| Method | URI | 입력 | `data` 페이로드 (공통 봉투 안쪽) |
|---|---|---|---|
| POST | `/api/chat-sessions` | `{ "predictionId": 15 }` | `{sessionId,predictionId,createdAt}` |
| GET | `/api/chat-sessions` | 없음 | `[{sessionId,predictionId,createdAt}]` |
| GET | `/api/chat-sessions/{sessionId}/messages` | 경로 sessionId | `[{messageId,sender,content,createdAt}]` |
| POST | `/api/chat-sessions/{sessionId}/messages` | `{ "content": "..." }` | `{messageId,sender,content,createdAt}` |
| GET | `/api/recommendations/{predictionId}` | 경로 predictionId | 추천 내역 배열 |

- 팀 PDF는 위 응답의 **`data` 내부 필드**를 나열한 것이며 봉투를 생략한 반환을 허용하는 뜻이 아니다.
- POST 메시지 반환 시 AI 메시지 1건인지, 사용자+AI 묶음인지 명확한 결정 필요; 팀 PDF는 `messageId,sender,content,createdAt`만 명시한다. 프론트에 제공할 `sources`·세션 제목·페이지네이션은 별도 승인 후 확장.
- 기능명세 F-05-01에 따라 최초 AI 가이드 `RECOMMENDATION` 생성, `CHAT_SESSION`·`CHAT_MESSAGE` 저장, 상담 기록 복원을 구현. F-05-02 별도 카드 UI는 신규 생성하지 않고 챗봇의 근거 설명에 통합한다(사용자 결정; 팀 문서에 기록 필요).

### HTTP 상태 및 팀 error.code (PDF 3쪽)
| 상태 | code | 정책 |
|---|---|---|
| 400 | `VALIDATION` | 입력·업무 규칙 오류 |
| 401 | `UNAUTHORIZED` | 로그인 정보 없음 |
| 403 | `FORBIDDEN` | 타인 소유 세션/계산 결과 접근 거부 |
| 404 | `NOT_FOUND` | 자원 없음 |
| 405 | `METHOD_NOT_ALLOWED` | 잘못된 메서드 |
| 409 | `CONFLICT` | 저장 충돌 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | 지원하지 않는 본문 형식 |
| 500 | `SERVER_ERROR` | 처리 실패, `errorId` 포함 |
| 503 | `○○_UNAVAILABLE` | 외부 서비스 이용 불가, `errorId` 포함. 챗봇은 `CHATBOT_UNAVAILABLE` 제안 |

**Spring Boot 오류 처리:** 서비스/클라이언트는 예외를 던지고 `GlobalExceptionHandler`가 공통 봉투를 만든다. 필요 시 `ChatbotUnavailableException` 등 503 처리기를 공통 파일에 팀 리뷰 후 추가. 각 Controller의 임의 `try/catch`로 응답 JSON을 직접 만들지 않는다. HTTP 상태는 응답 봉투의 `success`와 별도로 정확히 반환해야 한다.

`errorId`는 예: `UUID.randomUUID()` 결과의 앞 8자리(16진수)를 사용하는 팀 PDF 방식. 해당 요청의 **응답과 서버 로그에 동일 ID**. 화면에는 짧은 메시지와 오류번호만; SQL·DB 주소·스택·토큰·금액·카드번호·민감 질문 내용은 표시/로그하지 않는다. `errorId` 생성은 공통 예외 처리기의 책임.

**Frontend:** 팀 PDF는 `frontend/src/api/api-client.js`의 `apiRequest()`가 응답 봉투를 풀어주는 것으로 안내한다. 현재 브랜치에서 실제 존재/동작을 검증한 뒤 챗봇 화면에서 `response.data.data`를 **이중 적용하지 않는다**. 오류는 `error.code`, 사용자 문구는 `error.message`, 500/503의 `error.errorId`를 표시한다.

## 2. Spring Boot ↔ Chatbot FastAPI: 봉투 없는 내부 API (PDF 3쪽 명시)

- 팀 문서에 **내부 API는 패키징하지 않는다**고 명시. 성공은 아래 DTO의 순수 JSON. 사용자용 `{success,data,meta,error}`를 FastAPI 응답에 덧씌우지 않는다.
- base URL: 기존 Backend `chatbot.base-url` 설정 검증, 개발 기본 `http://127.0.0.1:8001`.
- 제안 내부 헤더: `X-Chatbot-Token: <secret>`, Spring과 Python 환경변수 `CHATBOT_API_TOKEN` 동일 값(팀 문서에 내부 헤더 상세는 아직 없음).
- 제안 경로: `POST /internal/chat-responses` (일반 상담), `POST /internal/recommendations` (첫 절세 안내). 기존 `GET /health` 유지.
- 전송 데이터 최소화. 회원 식별/권한/조회는 Spring, 검색과 자연어 생성은 FastAPI. 계산은 Calc와 Spring의 저장 결과만 사용.

### 내부 상담 요청 — 제안 형식(가상 수치 예시)
```json
{
  "message":"왜 환급액이 이렇게 나왔나요?",
  "taxYear":2026,
  "taxResult":{
    "predictionId":15,"withheldTax":1523000,"decidedTax":1100000,"expectedRefund":423000,
    "details":[{"typeCode":"RENT_CREDIT","typeName":"월세액 세액공제","deductionAmount":420000,"sourceNote":"DB의 검증된 안내 근거"}]
  },
  "history":[{"role":"user","content":"월세 공제란?"}]
}
```
- 일반 법령 질문에는 `taxResult:null` 허용 여부를 내부 DTO로 정하되, 사용자용 상담방 생성의 계산 결과 필수 여부는 기능명세와 일치시킬 것.
- `withheldTax`는 `PREDICTION_INPUT.WITHHELD_TAX`에서 조회한다. typeCode·법령 예시는 실제 DB/법령으로 검증 필요.

### 내부 상담 응답 — 제안 형식
```json
{"answer":"검색 근거를 바탕으로 설명...","model":"gemma3:4b","sources":[{"documentTitle":"소득세법","article":"제00조(예시)","sourceFile":"income_tax.pdf","page":null,"effectiveDate":null,"taxYear":null}]}
```
- 출처는 실제 Elasticsearch 검색 히트의 메타데이터로 반환. 모델이 출처를 임의 생성하지 않음. `CHAT_MESSAGE`에는 sources 컬럼이 없으므로 과거 대화 출처 보존 방식은 미결정.

### 내부 최초 추천 — 제안 형식
요청:
```json
{"taxYear":2026,"taxResult":{"predictionId":15,"expectedRefund":423000,"details":[]}}
```
응답:
```json
{"recommendations":[{"typeCode":null,"content":"적용 공제 설명...","model":"gemma3:4b","sources":[]}]}
```
- `RECOMMENDATION.SAVING_AMOUNT`와 `TYPE_ID`는 Spring/Calc의 검증된 규칙만 사용, LLM의 임의 수치 사용 금지. 추천 생성 실패가 계산 결과 저장을 롤백하지 않도록 설계.

### 내부 오류·성능 처리 — **팀 공식 규칙과 구분되는 제안**
- FastAPI: 토큰 누락/오류 401, Pydantic 검증 실패 422, 모델·RAG 장애 시 내부 503 등. 내부 오류 JSON은 별도 DTO로 확정; 외부 공통 봉투 불필요.
- Spring: 내부 오류를 해석하여 팀 오류 `VALIDATION`(400), `CHATBOT_UNAVAILABLE`(503, errorId 포함) 등으로 변환. 시간 초과에 대해 외부 503 또는 504 적용 여부는 **팀 PDF가 504를 정의하지 않았으므로 협의**.
- 기존 Backend 설정 `chatbot.connect-timeout:3s`, `chatbot.read-timeout:60s`는 현재 코드와 실측 확인 후 적용. ChatOllama 연결 모듈 자체는 이 응답 정책 변경으로 수정할 필요가 없다.
- LLM 대기 중 DB 트랜잭션 유지하지 않기; 실패 시 AI 답변 미저장, 사용자 메시지 저장 정책은 명시 필요. 재시도 시 중복 추천/답변 저장 방지.

## 3. 계약 확정 전 체크
1. 팀 개인 저장소와 팀 최신 통합 브랜치에 `ApiResponse`, `PageMeta`, `GlobalExceptionHandler`, `apiRequest()`가 실제로 어떻게 구현됐는지 확인하고 중복 생성 금지.
2. POST 질문 응답에서 AI 메시지 1건만 반환할지, `sources` 제공과 영구 보존 방식은 어떻게 할지.
3. 최초 안내 생성 시점·재시도 중복 정책, 세션 생성의 predictionId 필수 여부.
4. 인증 전 임시 `X-Member-Id` 제거 시점 및 403 접근 기록 정책.
5. 504 타임아웃의 상태·errorId·오류 코드 규칙(팀 PDF 미정).
6. `204 No Content`에서 공통 봉투 생략 예외 적용 방식.
7. PDF는 PATCH 금지라고 하면서 관리자 문의 응답에 PATCH를 기재하고 있어 팀 문서 정정 필요(챗봇 직접 영향 없음).

## 공식 자료와 참고 코드의 우선순위
- 팀 결정: **2026-11-09 수정 PDF 2~5쪽** > 이전 11-03 PDF의 원시 JSON 응답 규칙.
- 구현 참고: `https://github.com/sjlimiei26/final_project_sample/tree/main`의 `ApiResponse.java`, `PageMeta.java`, `GlobalExceptionHandler.java`, `MlClient.java`, `front/src/api/client.js`는 **패턴 참고**. 희망환급의 실제 경로(`/api/**`), 오류 코드, 컴포넌트/패키지·공통 설정을 그대로 덮어쓰지 않는다.
