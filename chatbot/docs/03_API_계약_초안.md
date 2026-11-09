# 03. API 계약: 공통 명세의 확정 부분과 내부 API 설계 제안

> **상태:** 사용자용 API는 2026-11-03 팀 PDF의 **초안**을 따르며 팀의 최신 결정 확인 필요. 내부 API는 챗봇 기능 담당자가 제안·고지 후 채택할 **구현 초안**. 미구현 API를 '구현 완료'라고 주장하지 않는다.

## 1) React → Spring Boot (팀 PDF에 기재된 외부용 API)
| Method | URI | 설명 | 요청 | 성공 응답 (팀 PDF 요약) |
|---|---|---|---|---|
| POST | `/api/chat-sessions` | 새 상담방 | `{predictionId}` | `{sessionId,predictionId,createdAt}` |
| GET | `/api/chat-sessions` | 내 상담방 목록 | 없음 | `[{sessionId,predictionId,createdAt}]` |
| GET | `/api/chat-sessions/{sessionId}/messages` | 해당 방 메시지 | 경로 ID | `[{messageId,sender,content,createdAt}]` |
| POST | `/api/chat-sessions/{sessionId}/messages` | 질문과 AI 답변 생성·저장 | `{content}` | `{messageId,sender,content,createdAt}` (정확한 응답 대상 USER/AI 확인 필요) |
| GET | `/api/recommendations/{predictionId}` | 첫 절세 안내 조회 | 경로 ID | 추천 내역 배열 |

- URL 회원 ID 불포함, camelCase JSON, 금액은 원 정수, 오류 `{error, message}`.
- 다른 회원의 세션·계산 결과 요청은 **403 또는 404** 정책을 통일해 접근 거부. 본인 소유 검사를 매 요청 수행.
- `predictionId`는 `CHAT_SESSION`에서 nullable. 계산 결과가 아직 없는 일반 세법 질문은 Chatbot 내부 서비스에서 `taxResult:null`을 지원할 수 있으나, 사용자 API의 신규 상담방 생성 조건(기능명세서: '계산 결과 1건 이상')은 **임의로 변경하지 않음**.
- POST 응답이 USER 메시지인지 AI 메시지인지, `sources`를 프론트에 전달할지, 세션 title 필드를 언제 제공할지는 기존 PDF에 상세가 없음. 기능 담당자가 확장안 정리하여 팀에 공유.

## 2) Spring Boot → Chatbot FastAPI (채택 제안)
- base URL: `${CHATBOT_BASE_URL:http://localhost:8001}` (기존 Backend application.yml 활용)
- 비밀값: `${CHATBOT_API_TOKEN}` — Backend와 Chatbot 프로세스에 동일 값, Git 비공개.
- 요청 헤더: `X-Chatbot-Token: <secret>` — **추가 제안**, FastAPI가 필수 검증.
- `POST /internal/chat-responses`: 단일 질문·대화 문맥으로 자연어 답변 생성
- `POST /internal/recommendations`: 계산 결과를 이용한 첫 절세 안내 생성
- `GET /health`: 기존 구현, 상태 확인(보안 모델을 어떻게 할지 별도 운영 검토). 내부 POST만 반드시 토큰 검사.

### 2-1. chat 요청 (예시, 숫자와 조문 내용은 체험 값)
```json
{
  "message": "왜 예상 환급액이 이 금액인가요?",
  "taxYear": 2026,
  "taxResult": {
    "predictionId": 15,
    "withheldTax": 1523000,
    "decidedTax": 1100000,
    "expectedRefund": 423000,
    "details": [
      {"typeCode":"RENT_CREDIT","typeName":"월세액 세액공제","deductionAmount":420000,"sourceNote":"검증된 DB 근거"}
    ]
  },
  "history": [{"role":"user","content":"월세 세액공제란?"}]
}
```
**주의:** 위 `typeCode`는 예시 코드이며 팀의 실제 `DEDUCTION_TYPE.TYPE_CODE` 데이터와 검증해야 한다. `withheldTax`는 `PREDICTION` 컬럼이 아니라 **`PREDICTION_INPUT.WITHHELD_TAX`**에서 조회한다. `sourceNote`는 문자열 근거일 뿐 법령 적용의 법적 검증을 대신하지 않는다.

### 2-2. chat 응답 (제안)
```json
{
  "answer": "기납부세액과 결정세액의 차이를 설명하는 문장...",
  "model": "gemma3:4b",
  "sources": [
    {"documentTitle":"소득세법", "article":"제00조(형식 예시)", "effectiveDate":null,"taxYear":null,"sourceFile":"income_tax.pdf","page":null}
  ]
}
```
`sources`는 모델이 쓰는 자유 텍스트에서 추측하지 않고 실제 검색 히트의 메타데이터로 생성. ERD v4.1의 CHAT_MESSAGE에는 `sources` 별도 컬럼이 없음 → 과거 대화 출처를 영구 조회해야 한다면 저장 방식 결정 필요.

### 2-3. recommendation 요청 (제안)
```json
{
  "taxYear": 2026,
  "taxResult": {
    "predictionId": 15,
    "expectedRefund": 423000,
    "details": []
  }
}
```
### 2-4. recommendation 응답 (제안)
```json
{
  "recommendations": [
    {"typeCode":null, "content":"적용 공제에 대한 설명...", "model":"gemma3:4b", "sources":[]}
  ]
}
```
- `RECOMMENDATION.TYPE_ID`·`SAVING_AMOUNT`는 **Spring Boot가 검증된 DB/규칙 결과로만 결정**. AI가 추정한 예상 절세액을 저장하지 않는다.
- 실패 시 해당 AI 안내를 저장하지 않으며 계산 완료 저장을 취소하지 않는다.

## 3) 인증·검증·오류
- 요청: Pydantic 필드 타입·길이(예: 1~1000자), `taxYear`, history 상한(예: 최근 10개) 검증. 상한은 테스트 후 정함.
- FastAPI: 토큰 누락·불일치 401, 유효하지 않은 JSON 422 (외부 Spring 오류 변환 400 `VALIDATION`), 모델·RAG 실패 503, 요청 제한 시간 초과 504 제안.
- Spring Boot 공통 오류: `{ "error": "CHATBOT_UNAVAILABLE", "message": "AI 상담 서비스에 잠시 연결할 수 없습니다." }`, 503. `RAG_UNAVAILABLE`, `CHATBOT_TIMEOUT`도 별도 코드 제안.
- Backend 설정 기존 `chatbot.connect-timeout: 3s`, `read-timeout: 60s`를 시작점으로 사용. 모델 처리시간 실측·재시도 시 중복 저장 방지.
- `CHATBOT_API_TOKEN`은 **서버 간 자격증명**이지 사용자의 로그인 인증이 아님.
- 개인정보·비밀번호·카드번호·전체 카드 원장은 AI 요청에 넣지 않음. 필요 결과만 포함, 예외 메시지/프롬프트에 민감값 로깅 금지.

## 4) 반드시 확인할 계약 갭
1. POST 질문 응답: 생성된 AI 메시지 1건을 반환할지, `{userMessage, aiMessage, sources}`로 확장할지.
2. 최초 안내: 저장 완료 시점과 생성 트리거 및 재시도/중복생성 정책.
3. UI 출처 링크를 과거 대화에서도 제공할지(ERD에 출처 전용 컬럼 부재).
4. `CHAT_SESSION.PREDICTION_ID` nullable vs 계산 결과 필수라는 기능명세의 조건 정합성.
5. Spring Security 미구현 상태에서 개발용 `X-Member-Id`를 언제 제거할지.
6. 양쪽 서버 포트·배포 IP·보안 토큰 갱신/에러 코드를 최종 문서로 전달.
