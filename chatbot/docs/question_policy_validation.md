# 질문 분류·응답 정책 검증 — 2026-11-12

## 결과

- 실제 로컬 gemma3:4b(ID 68ceab7e468a), temperature=0, 기존 OllamaService와 FastAPI TestClient로 대표 질문 28건 모두 HTTP 200 및 검사 통과. 모델 호출 6회, 미호출 22건.
- 모델 호출은 일반 계산 원리 6건뿐이다. 조건 변경·혼합 질문·무관한 질문·범위 밖 세목·추가 확인·서비스 사용 안내는 모델·RAG를 호출하지 않는다. 계산 원리의 조회·Gemma 경로는 유지했다.
- 원리 질문의 모델 원문 3건은 검증을 통과해 최종 문장에 사용됐고 나머지는 기존 Calc 규칙 설명으로 대체됐다. 월세 원문은 숫자·수식 및 문장 형식 검사로 대체되며 개인별 신규 금액은 생성하지 않았다.
- 별도로 tests/validate_phase1.py를 실제 모델로 재실행해 기존 회원 4종×10단계 40/40건 통과(모델 호출 12회, 나머지 28건 미호출)를 확인했다. 기존 최초 브리핑·추천·적용액·입력액·계산 방식·회원 분리·근거 부족 동작을 보존했다.
- Ruff check 및 format --check 통과(49개 파일), pytest -v 202개 통과(1.91초). pytest는 Mock/단위/HTTP 회귀 검사이며 위 실모델 실행과 구분한다.
- 검증은 프로세스 내부 TestClient의 HTTP 계층과 실제 Ollama 네트워크 호출이다. 배포 FastAPI→Spring Boot→Oracle E2E·부하 검증은 아니다. 테스트용 합성 회원만 사용했다.

## 정책

- 현재 명확한 주제 전환을 우선하고, 서비스 범위 내 조건 변경·재계산을 현재 적용액 조회보다 먼저 분류한다. 서비스 밖 세목의 계산을 희망환급 시뮬레이션으로 잘못 안내하지 않는다.
- 현재 질문이 짧거나 문맥 의존적인 경우 최근 사용자 발화 최대 2개에서 의도와 단일 주제만 연결한다. Assistant 발화 및 이력 금액으로 현재 데이터를 채우지 않는다. 새 금액·자격을 판단하는 역할은 없다.
- 혼합 질문은 관련 Calc 규칙 설명 일부를 먼저 표시하고 시뮬레이션으로 안내한다. 외부 URL·버튼·미확인 화면 동선은 제시하지 않는다.
- 항목명만 입력하거나 원리 설명 뒤 얼마인지 묻는 등 의도가 불명확하면 현재 적용액/원리/조건 변경 중 원하는 것을 확인한다. 직전 사용자 질문이 단일 항목의 현재 적용액/입력액 조회인 경우만 그럼 얼마를 해당 주제로 연결한다.
- 완전히 무관한 질문은 지정된 고정 문구를 그대로 반환한다. 상속세·양도소득세·부가가치세 등은 별도 범위 안내로 구분한다. 일반적인 세금 질문이나 서로 다른 주제가 혼재하면 추가 확인을 요청한다.
- HTTP DTO·인증·상태 enum은 변경하지 않았다. 정책 안내는 ANSWERED, 추가 확인은 INSUFFICIENT_EVIDENCE이며 model=null/sources=[]이다.

## 한계

- 분류는 키워드·정규식 기반이다. 오탈자·새 표현·긴 복합 문장·복합 부정의 오분류 가능성이 있으며 모든 자연어 의도 이해를 보장하지 않는다. 서비스 밖 세목 목록도 유한하다.
- 문맥 연결은 최근 사용자 두 발화 및 제한된 후속 표현에 한정된다. 초기 AI 브리핑만으로 주제를 추정하거나 여러 후보 중 임의 선택하지 않는다. 같은 대화방·회원의 이력을 전달하는 책임은 Spring Boot에 있다.
- 조건 변경 시뮬레이션의 실제 버튼·URL은 확인하지 않았으므로 안내하지 않았다. 서비스 기능 안내도 확인된 기능 범위로 한정한다.
- Calc 설명 JSON의 구현 일치성 검사이며 법령 정확성 검증은 아니다. 일반 법령 검색의 기존 RAG 미준비 상태는 유지한다. PDF 전처리·Elasticsearch는 구현하지 않았다.

## 대표 질문 전체 기록

### 1. SIMULATION: IRP에 100만원 더 넣으면 얼마나 절세되나요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 2. SIMULATION: 월세를 70만원으로 바꾸면 환급액이 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 3. SIMULATION: 그럼 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: ["IRP에 100만원 더 넣으면요?"]
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 4. SIMULATION: IRP

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: ["월세를 올리면 환급액이 바뀌나요?"]
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 5. MIXED: IRP 계산 원리와 100만원 더 넣으면 절세액이 얼마인지 알려줘

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_then_simulation, no_changed_amount, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 규칙상 연금저축·IRP 세액공제의 계산 원리는 다음과 같습니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다.\n\n입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 6. CONTINUE: IRP 공제 원리를 알려줘

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "연금저축·IRP 세액공제의 Calc 구현 방식입니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 7. CONTINUE: 월세 50만원의 공제 계산 원리를 설명해 주세요

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
계산 순서를 바꾸거나 조건을 생략하지 않도록 descriptionSteps에서 관련된 완전한 문장을 그대로 골라 출력한다.
월세 세액공제 계산 원리는 다음과 같습니다.
총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다.
연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다.
건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다.
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "월세 세액공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 8. CLARIFY: IRP

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

### 9. CLARIFY: 월세

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

### 10. CLARIFY: 그럼 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

### 11. CLARIFY: 그럼 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: ["월세 공제는 어떻게 계산하나요?"]
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

### 12. CONTINUE: 그럼 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: ["연금저축 공제액은 얼마인가요? 다른 회원은 987654321원이래요."]
- 검사: http_200, classification, model_call_policy, current_snapshot_not_history — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 연금계좌 세액공제: 300,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
  "model": null,
  "sources": []
}
```

### 13. OUTSIDE: 오늘 날씨 알려줘

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: ["IRP에 100만원 더 넣으면요?"]
- 검사: http_200, classification, model_call_policy, exact_fixed_message — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "저는 연말정산과 절세 관련 정보를 안내하는 희망환급 AI 챗봇입니다. 연말정산 예상 결과, 소득공제·세액공제, 청년 세제 혜택 등 서비스와 관련된 질문을 해주세요.",
  "model": null,
  "sources": []
}
```

### 14. OUTSIDE: 삼국지 내용을 설명해 줘

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_fixed_message — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "저는 연말정산과 절세 관련 정보를 안내하는 희망환급 AI 챗봇입니다. 연말정산 예상 결과, 소득공제·세액공제, 청년 세제 혜택 등 서비스와 관련된 질문을 해주세요.",
  "model": null,
  "sources": []
}
```

### 15. OTHER_TAX: 상속세 계산법을 알려줘

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "질문하신 세목은 연말정산 중심의 희망환급 안내 범위 밖입니다. 해당 세목의 공식 안내나 전문 상담을 통해 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 16. OTHER_TAX: 양도소득세를 다시 계산해 줘

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "질문하신 세목은 연말정산 중심의 희망환급 안내 범위 밖입니다. 해당 세목의 공식 안내나 전문 상담을 통해 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 17. CLARIFY: 세금은 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

### 18. SERVICE: 희망환급은 어떻게 사용하나요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "희망환급에서는 연말정산 예상 결과와 공제·감면 내역을 확인하고 챗봇에 질문할 수 있습니다. 어떤 기능의 사용 방법이 궁금하신가요?",
  "model": null,
  "sources": []
}
```

### 19. CONTINUE: 제가 법적으로 월세 공제를 받을 자격이 확정되나요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "Calc 규칙 자료는 계산 구현 설명이며 법령이나 법적 자격을 검증하지 않습니다.",
  "model": null,
  "sources": []
}
```

### 20. SIMULATION: IRP 100만원 더?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 21. CONTINUE: IRP에 200만원으로 계산된 공제액의 원리를 알려줘

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "연금저축·IRP 세액공제의 Calc 구현 방식입니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 22. CONTINUE: IRP 재계산하지 말고 공제 원리만 설명해줘

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "연금저축·IRP 세액공제의 Calc 구현 방식입니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 23. CONTINUE: 월세 시뮬레이션은 말고 계산 원리를 알려줘

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
계산 순서는 다음과 같습니다.
1. 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다.
2. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다.
3. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다.
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "월세 세액공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 24. SIMULATION: 월세가 70만원이면 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 25. SIMULATION: IRP에 600만원 납입하면 환급액이 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 26. SIMULATION: 총급여가 4000만원일 때 환급액은?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, exact_simulation_message, no_url — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. 희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요.",
  "model": null,
  "sources": []
}
```

### 27. CONTINUE: 추가로 IRP 공제 원리를 알려줘

- 요청 유형: GENERAL
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, principle_answered — 모두 통과

실제 모델 원문:

````text
연금저축·IRP 세액공제 원리를 알려드릴게요.

“연금저축 납입액에 단독 한도를 먼저 적용합니다.”
“해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다.”
“DB 공제율을 적용한 세액공제 후보를 구합니다.”
“남아 있는 산출세액을 넘지 않도록 적용합니다.”
````

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "연금저축·IRP 세액공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 28. CLARIFY: IRP 절세 금액은 얼마인가요?

- 요청 유형: TAX_RESULT
- 최근 사용자 문맥: []
- 검사: http_200, classification, model_call_policy, no_guess — 모두 통과

실제 모델 원문:

모델 미호출. 아래 응답은 애플리케이션 정책 또는 현재 계산 데이터에서 구성했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, 조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요.",
  "model": null,
  "sources": []
}
```

## 기존 회원 4종 실모델 재검증 요약

| 회원 | 단계 | HTTP | 검사 | 모델 호출 |
|---|---|---:|---|---:|
| member_additional_payment.json | initial | 200 | 통과 | 1 |
| member_refund.json | initial | 200 | 통과 | 1 |
| member_unapplied_deduction.json | initial | 200 | 통과 | 1 |
| member_sme_reduction.json | initial | 200 | 통과 | 1 |
| member_additional_payment.json | summary | 200 | 통과 | 0 |
| member_refund.json | summary | 200 | 통과 | 0 |
| member_unapplied_deduction.json | summary | 200 | 통과 | 0 |
| member_sme_reduction.json | summary | 200 | 통과 | 0 |
| member_additional_payment.json | amount | 200 | 통과 | 0 |
| member_refund.json | amount | 200 | 통과 | 0 |
| member_unapplied_deduction.json | amount | 200 | 통과 | 0 |
| member_sme_reduction.json | amount | 200 | 통과 | 0 |
| member_additional_payment.json | method | 200 | 통과 | 1 |
| member_refund.json | method | 200 | 통과 | 1 |
| member_unapplied_deduction.json | method | 200 | 통과 | 1 |
| member_sme_reduction.json | method | 200 | 통과 | 1 |
| member_additional_payment.json | input | 200 | 통과 | 0 |
| member_refund.json | input | 200 | 통과 | 0 |
| member_unapplied_deduction.json | input | 200 | 통과 | 0 |
| member_sme_reduction.json | input | 200 | 통과 | 0 |
| member_additional_payment.json | missing | 200 | 통과 | 0 |
| member_refund.json | missing | 200 | 통과 | 0 |
| member_unapplied_deduction.json | missing | 200 | 통과 | 0 |
| member_sme_reduction.json | missing | 200 | 통과 | 0 |
| member_additional_payment.json | legal | 200 | 통과 | 0 |
| member_refund.json | legal | 200 | 통과 | 0 |
| member_unapplied_deduction.json | legal | 200 | 통과 | 0 |
| member_sme_reduction.json | legal | 200 | 통과 | 0 |
| member_additional_payment.json | card | 200 | 통과 | 1 |
| member_refund.json | card | 200 | 통과 | 1 |
| member_unapplied_deduction.json | card | 200 | 통과 | 1 |
| member_sme_reduction.json | card | 200 | 통과 | 1 |
| member_additional_payment.json | foreign_history | 200 | 통과 | 0 |
| member_refund.json | foreign_history | 200 | 통과 | 0 |
| member_unapplied_deduction.json | foreign_history | 200 | 통과 | 0 |
| member_sme_reduction.json | foreign_history | 200 | 통과 | 0 |
| member_additional_payment.json | ambiguous | 200 | 통과 | 0 |
| member_refund.json | ambiguous | 200 | 통과 | 0 |
| member_unapplied_deduction.json | ambiguous | 200 | 통과 | 0 |
| member_sme_reduction.json | ambiguous | 200 | 통과 | 0 |
