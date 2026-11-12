# 1차 기능 통합 검증 — 2026-11-12

> 후속 변경: 질문 정책 보완 후 기존 40건을 다시 실행해 모두 통과했다. 당시 미구현이던 문맥 연결은 현재 최근 사용자 발화 최대 2개에 한해 제한적으로 지원한다. 신규 정책·원문 기록은 [question_policy_validation.md](question_policy_validation.md)를 참고한다. 아래 기록은 1차 검증 당시 결과다.

## 판정

내부 FastAPI의 명시적 회원별 계산 질문·최초 단일 메시지·안전한 근거 부족 응답은 검증 범위에서 완료했다. 제품 전체의 Spring Boot→Oracle 저장→채팅 복원 E2E 및 문맥의 지시어 해석까지 완료한 것은 아니다. PDF RAG 개발은 시작할 수 있으나 아래 경계·계약을 먼저 확정해야 한다.

## 환경·방법

- 실제 로컬 Ollama http://127.0.0.1:11434, gemma3:4b(ID 68ceab7e468a), temperature=0, 기존 OllamaService/ChatOllama를 사용했다.
- FastAPI TestClient를 사용한 프로세스 내부 HTTP 계층 검증이며 별도로 배포된 Uvicorn/Spring Boot에 보낸 E2E 요청은 아니다. 내부 인증 토큰은 실행 프로세스에서만 임시 생성하고 원문 기록에 포함하지 않았다.
- 같은 모델 인스턴스·프로세스에서 4종 회원을 매 단계 번갈아 요청했다. 각 회원의 최초 AI 메시지와 후속 문답을 history로 전달했다. 최근 6개 메시지를 사용하며 마지막 오염 테스트에서는 타 회원 스냅샷과 거짓 환급액 987654321원을 이력에 넣었다.
- 최종 40요청, 실제 모델 호출 12회(최초 4 + 공제 방식 4 + 카드 방식 4), 모델 미호출 28회다. 금액·원본 입력·근거 부족 응답을 모델 생성 결과라고 표시하지 않는다.
- UnavailableRetriever를 그대로 사용했다. 모든 결과가 HTTP 200으로 완료되어 이 경로들이 검색을 필요로 하지 않음을 확인했다. PDF 전처리·Elasticsearch를 구현하거나 호출하지 않았다.
- 재현: chatbot에서 `.venv/Scripts/python.exe tests/validate_phase1.py --output <임시 JSON 경로>`를 실행한다. 테스트 전용 더미만 사용하며 pytest 기본 수집에서는 실모델을 호출하지 않는다.

## 단계별 결과

| 단계 | 회원 수 | 통과 | 검증 기준 |
|---|---:|---:|---|
| 최초 단일 메시지·추천 | 4 | 4 | recommendations 1건, 후보 개수 1/0/2/1, 정상 적용 항목 재확인 제외, 자신의 세액·환급액 |
| 결과 요약 | 4 | 4 | 자신의 기납부·결정세액·환급 부호 및 금액 |
| 실제 공제 적용액 | 4 | 4 | 국민연금 1,200,000 / 연금계좌 300,000 / 월세 0 / SME 1,000,000원 |
| 해당 공제 계산 방식 | 4 | 4 | 해당 규칙 JSON의 모든 설명 단계와 자신의 적용액, 모델 전달 상세가 현재 스냅샷에 포함됨 |
| 원본 납입·신청 입력 | 4 | 4 | 국민연금 1,200,000 / 연금저축 2,000,000 / 월 월세 500,000원 / 감면 신청 Y |
| 미제공 의료비 적용액 | 4 | 4 | 의료비 금액 생성 없이 INSUFFICIENT_EVIDENCE, 모델 미호출 |
| 법적 자격 확정 | 4 | 4 | 법적 자격 확정 없이 INSUFFICIENT_EVIDENCE, 모델 미호출 |
| 개인 결과 없는 카드 계산 방식 | 4 | 4 | CARD 규칙 단계만 설명, 실제 회원 카드액·공제율·한도 금액을 추정하지 않음 |
| 타 회원 이력·지시문 오염 | 4 | 4 | 현재 요청 결과 유지, 타 회원 고유 환급액·주입 금액 미반영 |
| 항목 생략 후속 질문 | 4 | 4 | 그건 얼마인지 추측하지 않고 항목명 요청, 모델 미호출 |

## 모델 원문과 최종 답변의 평가

- 최초 메시지 4회: 후보가 없는 회원에도 일반 안내를 생성하거나 조건부 납입 계획 설명을 생략하고, 월세 후보에 연금계좌 설명을 배치했다. 서버가 확정한 후보별 문장 검증에서 거부하고 검증된 기본 설명으로 대체했다. 새로운 추천·절세액·자격은 최종 답변에 추가되지 않았다.
- 공제 방식 4회: 연금계좌·SME 설명은 규칙 원문과 일치해 수용됐다. 국민연금은 의미가 비슷해도 문장 원문과 달라 보수적으로 대체됐고, 월세는 도입문 및 숫자 표현 때문에 대체됐다. 월세 0원의 원인은 특정하지 않는다.
- 카드 방식 4회: 설명 순서는 규칙과 일치했으나 도입문과 숫자 표현 때문에 보수적으로 대체됐다. 최종 답변은 원문 규칙의 문턱액 차감→공제율 적용→한도 조정 순서를 유지한다. 카드 상세가 없는 샘플이므로 개인 카드액은 안내하지 않는다.
- 총 12개 모델 출력 중 10개는 기본 설명으로 대체됐고 2개는 수용됐다. 대체 10건이 모두 사실 오류라는 뜻은 아니다. 현재의 엄격한 문장 검사와 모델의 형식·후보 선택 지시 준수 부족이 함께 작용한다. 따라서 실제 모델이 자유롭게 정확한 설명을 생성한다고 판정할 수는 없다.
- 실제 연도별 Oracle 기준값·법률 정확성은 검증하지 않았다. 테스트는 제공된 입력·부분 상세 결과 및 Calc 설명 JSON과의 일치성 검증이다.

## 발견한 문제와 수정

- 수정 전 원본 입력액 질문에서 연금저축 2,000,000원 대신 적용액 300,000원, 월 월세 500,000원 대신 적용액 0원을 반환했다. SME 신청 Y 질문은 근거 부족으로 처리했다. 국민연금은 입력액과 적용액이 우연히 같아 숫자만 검사하면 문제가 드러나지 않았다.
- TaxResultService에서 명시적 입력 조회를 적용액 조회와 분리했다. 입력이 없을 때는 결과 기준액이나 이력으로 메우지 않고 근거 부족으로 반환한다. API 필드 변경이나 세액 재계산은 없다.
- 검증 도구 초안은 프롬프트의 첫 줄 다음이 JSON이라고 가정해 중단됐고 마지막 줄의 JSON으로 읽도록 고쳤다. 타 회원 환급액 800,000원을 본인의 기납부세액 1,800,000원의 부분 문자열로 잘못 검출한 검증 도구 오류도 금액 시작 경계 검사로 수정했다. 최종 코드로 40건 전체를 다시 실행해 종료코드 0을 확인했다.
- Ruff check/format --check 통과(46개 파일), pytest -v 136개 통과(2.03초). pytest는 Mock 회귀 검사이며 실제 모델 40요청 실행과 별개다. 기존 모델 오류·잘못된 금액·0원 원인·법령 생성 차단 검사도 유지했다.

## 2차 PDF RAG 전에 확정할 사항

1. Spring Boot가 대화방·계산 결과의 소유권을 확인하고 같은 predictionId의 계산 당시 입력·결과를 전달하며 최초 content를 한 AI 메시지로 저장하는 E2E를 확인한다. FastAPI는 잘못 전달된 타 회원의 완전한 스냅샷을 인증된 요청과 구분할 수 없다.
2. 모호한 그건/그 공제 등의 후속 발화를 계속 항목명 확인으로 처리할지, 회원에 바인딩된 명시적 대화 주제를 도입할지 정한다. 현재 history는 계산 사실의 근거로 사용하지 않으므로 문맥 지시어 해석 기능은 미구현이다.
3. Calc 규칙과 법령 자료를 분리하고 PDF 출처·페이지·버전·귀속연도·적용시점 및 검색 근거 부족 정책을 먼저 정한다. 기존 GENERAL 생성 경로는 자유 생성이므로 Calc의 고정 문장 검사를 그대로 법령 검증의 보장으로 사용할 수 없다. 검색 결과의 지시문 무시와 생성 주장·출처 대응 검증이 필요하다.
4. 실모델의 후보 선택·조건 보존 정확도와 높은 기본 문장 대체 비율을 개선·평가한다. 모델 원문을 검증 없이 출력하지 않는다. 실제 저장 데이터 스냅샷·연도별 기준으로 더미보다 넓은 회귀 자료를 준비한다.
5. 실환경 지연·동시성·시간초과·재시도 및 출처 영구 저장은 별도 검증한다. 이번 검사는 순차 요청이며 다중 워커·부하·추론 취소를 보장하지 않는다.

## 입력 자료 식별

- `data/rules/희망환급_Calc_계산설명규칙.json` SHA-256 `a8a745c8a9584a4ac074b2dcbdd12b5f7933a0569536468170000a1047bac8d9`
- `tests/fixtures/member_additional_payment.json` SHA-256 `ebf8891ea9e63e3338ad3ce0dbecf107b9f65e7c58319fba83223b6eae255015`
- `tests/fixtures/member_refund.json` SHA-256 `752a3b1ed6b79dd87dfc1845dcaa3ce61d72e715e8be2d45c0d760d73bbf48de`
- `tests/fixtures/member_sme_reduction.json` SHA-256 `9ac3639b6777c2ad3df03f79b65618267ced34386614bbd5e1fb939453deab49`
- `tests/fixtures/member_unapplied_deduction.json` SHA-256 `861959877b9ec2d4781c622678407b237a1db99b9960955a437e5b3d40a41187`

## 최종 40요청 원문 기록

모든 자료는 테스트 전용 합성 회원이다. 실제 모델 원문과 최종 API JSON을 구분한다. 원문이 없는 요청은 모델을 호출하지 않았다.

### 1. member_additional_payment.json / 최초 단일 메시지·추천

- predictionId: 1001, HTTP 200, 1.31초, 판정 통과.
- 질문: 최초 안내
- 검사: http_200, one_message, expected_recommendation_count, no_applied_item_recheck, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

```text
```json
{"explanations": ["연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다."]
}
```
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "recommendations": [
    {
      "typeCode": null,
      "content": "예상 추가 납부액은 117,000원입니다. 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 10,000,000원; 기본공제 1,500,000원; 국민연금보험료 소득공제 1,200,000원; 근로소득세액공제 460,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
      "model": "gemma3:4b",
      "sources": []
    }
  ]
}
```

### 2. member_refund.json / 최초 단일 메시지·추천

- predictionId: 1002, HTTP 200, 0.56초, 판정 통과.
- 질문: 최초 안내
- 검사: http_200, one_message, expected_recommendation_count, no_applied_item_recheck, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

```text
```json
{"explanations": ["연말정산 준비를 위한 첫 단계입니다. 소득공제 및 세액공제 적용 가능 항목을 확인하고, 관련 서류를 준비해주세요."]
}
```
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "recommendations": [
    {
      "typeCode": null,
      "content": "예상 환급액은 450,000원입니다. 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 11,500,000원; 기본공제 3,000,000원; 국민연금보험료 소득공제 1,450,000원; 연금계좌 세액공제 300,000원.\n\n현재 입력과 결과에서 추가 검토할 사유를 확인하지 못해 임의 추천은 하지 않습니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
      "model": "gemma3:4b",
      "sources": []
    }
  ]
}
```

### 3. member_unapplied_deduction.json / 최초 단일 메시지·추천

- predictionId: 1003, HTTP 200, 1.84초, 판정 통과.
- 질문: 최초 안내
- 검사: http_200, one_message, expected_recommendation_count, no_applied_item_recheck, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

```text
```json
{"explanations": ["향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다.", "연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다."]}
```
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "recommendations": [
    {
      "typeCode": null,
      "content": "예상 환급액은 80,000원입니다. 기납부세액은 900,000원, 결정세액은 820,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,000,000원; 기본공제 1,500,000원; 표준세액공제 130,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 월 월세 입력액은 500,000원입니다. 월세 세액공제: 계산 기준액 6,000,000원, 실제 적용액 0원. 월세 납부 자료와 무주택 세대주 입력값을 확인해 주세요. 무주택 세대주 입력은 N입니다. 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 미적용이나 상세행 누락의 구체적인 원인은 현재 결과만으로 확정할 수 없습니다.\n\n2. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
      "model": "gemma3:4b",
      "sources": []
    }
  ]
}
```

### 4. member_sme_reduction.json / 최초 단일 메시지·추천

- predictionId: 1004, HTTP 200, 0.95초, 판정 통과.
- 질문: 최초 안내
- 검사: http_200, one_message, expected_recommendation_count, no_applied_item_recheck, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

```text
```json
{"explanations": ["연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다."]
}
```
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "recommendations": [
    {
      "typeCode": null,
      "content": "예상 환급액은 800,000원입니다. 기납부세액은 1,200,000원, 결정세액은 400,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,500,000원; 기본공제 1,500,000원; 중소기업 취업자 소득세 감면 1,000,000원; 근로소득세액공제 100,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
      "model": "gemma3:4b",
      "sources": []
    }
  ]
}
```

### 5. member_additional_payment.json / 결과 요약

- predictionId: 1001, HTTP 200, 0.02초, 판정 통과.
- 질문: 환급액과 추가 납부 결과를 설명해주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다. 예상 추가 납부액은 117,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 10,000,000원\n- [소득공제] 기본공제: 1,500,000원\n- [소득공제] 국민연금보험료 소득공제: 1,200,000원\n- [세액공제] 근로소득세액공제: 460,000원",
  "model": null,
  "sources": []
}
```

### 6. member_refund.json / 결과 요약

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 환급액과 추가 납부 결과를 설명해주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다. 예상 환급액은 450,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 11,500,000원\n- [소득공제] 기본공제: 3,000,000원\n- [소득공제] 국민연금보험료 소득공제: 1,450,000원\n- [세액공제] 연금계좌 세액공제: 300,000원",
  "model": null,
  "sources": []
}
```

### 7. member_unapplied_deduction.json / 결과 요약

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 환급액과 추가 납부 결과를 설명해주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 900,000원, 결정세액은 820,000원입니다. 예상 환급액은 80,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 9,000,000원\n- [소득공제] 기본공제: 1,500,000원\n- [세액공제] 월세액 세액공제: 0원\n- [세액공제] 표준세액공제: 130,000원",
  "model": null,
  "sources": []
}
```

### 8. member_sme_reduction.json / 결과 요약

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 환급액과 추가 납부 결과를 설명해주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,200,000원, 결정세액은 400,000원입니다. 예상 환급액은 800,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 9,500,000원\n- [소득공제] 기본공제: 1,500,000원\n- [세액감면] 중소기업 취업자 소득세 감면: 1,000,000원\n- [세액공제] 근로소득세액공제: 100,000원",
  "model": null,
  "sources": []
}
```

### 9. member_additional_payment.json / 실제 공제 적용액

- predictionId: 1001, HTTP 200, 0.02초, 판정 통과.
- 질문: 국민연금 공제 금액은 얼마인가요?
- 검사: http_200, own_applied_amount, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 관련 적용액입니다.\n- [소득공제] 국민연금보험료 소득공제: 1,200,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
  "model": null,
  "sources": []
}
```

### 10. member_refund.json / 실제 공제 적용액

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 연금저축 공제 금액은 얼마인가요?
- 검사: http_200, own_applied_amount, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 연금계좌 세액공제: 300,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
  "model": null,
  "sources": []
}
```

### 11. member_unapplied_deduction.json / 실제 공제 적용액

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 월세 공제 금액은 얼마인가요?
- 검사: http_200, own_applied_amount, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 월세액 세액공제: 0원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
  "model": null,
  "sources": []
}
```

### 12. member_sme_reduction.json / 실제 공제 적용액

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 중소기업 감면 공제 금액은 얼마인가요?
- 검사: http_200, own_applied_amount, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 관련 적용액입니다.\n- [세액감면] 중소기업 취업자 소득세 감면: 1,000,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
  "model": null,
  "sources": []
}
```

### 13. member_additional_payment.json / 해당 공제 계산 방식

- predictionId: 1001, HTTP 200, 0.41초, 판정 통과.
- 질문: 국민연금 공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
국민연금 공제는 입력된 국민연금보험료에 DB의 공제율을 적용합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 국민연금보험료 소득공제 1,200,000원 적용액을 기준으로 설명합니다. Calc 구현 규칙에 따르면 입력된 국민연금보험료에 DB의 공제율을 적용합니다. 개인별 실제 적용액은 Calc 결과에 표시된 값입니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 14. member_refund.json / 해당 공제 계산 방식

- predictionId: 1002, HTTP 200, 0.91초, 판정 통과.
- 질문: 연금저축 공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 연금계좌 세액공제 300,000원 적용액을 기준으로 설명합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 15. member_unapplied_deduction.json / 해당 공제 계산 방식

- predictionId: 1003, HTTP 200, 1.28초, 판정 통과.
- 질문: 월세 공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
월세 공제는 다음과 같이 계산됩니다.
총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다.
연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다.
건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 월세액 세액공제 0원 적용액을 기준으로 설명합니다. Calc 구현 규칙에 따르면 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 제공된 결과만으로는 해당 적용액의 구체적인 원인을 특정할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 16. member_sme_reduction.json / 해당 공제 계산 방식

- predictionId: 1004, HTTP 200, 0.89초, 판정 통과.
- 질문: 중소기업 감면 공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
Spring Boot가 별도 혜택 진단 결과를 바탕으로 감면 신청값을 정리해 Calc에 전달합니다. 감면 기준 행이 있고 신청값이 Y이면 산출세액 × DB 감면율과 DB 한도 중 작은 금액을 계산합니다. 산출세액에서 아직 남아 있는 세액 이하로 실제 감면액을 제한합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과의 중소기업 취업자 소득세 감면 1,000,000원 적용액을 기준으로 설명합니다. Spring Boot가 별도 혜택 진단 결과를 바탕으로 감면 신청값을 정리해 Calc에 전달합니다. 감면 기준 행이 있고 신청값이 Y이면 산출세액 × DB 감면율과 DB 한도 중 작은 금액을 계산합니다. 산출세액에서 아직 남아 있는 세액 이하로 실제 감면액을 제한합니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 17. member_additional_payment.json / 원본 납입·신청 입력

- predictionId: 1001, HTTP 200, 0.02초, 판정 통과.
- 질문: 국민연금 납입 입력액은 얼마인가요?
- 검사: http_200, own_original_input, input_answered, input_label, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "전달된 원본 입력값입니다. 공제·감면 적용액과 구분해 안내합니다.\n- 국민연금 납입액: 1,200,000원",
  "model": null,
  "sources": []
}
```

### 18. member_refund.json / 원본 납입·신청 입력

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 연금저축 납입 입력액은 얼마인가요?
- 검사: http_200, own_original_input, input_answered, input_label, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "전달된 원본 입력값입니다. 공제·감면 적용액과 구분해 안내합니다.\n- 연금저축 납입액: 2,000,000원",
  "model": null,
  "sources": []
}
```

### 19. member_unapplied_deduction.json / 원본 납입·신청 입력

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 월 월세 입력액은 얼마인가요?
- 검사: http_200, own_original_input, input_answered, input_label, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "전달된 원본 입력값입니다. 공제·감면 적용액과 구분해 안내합니다.\n- 월 월세액: 500,000원",
  "model": null,
  "sources": []
}
```

### 20. member_sme_reduction.json / 원본 납입·신청 입력

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 중소기업 감면 신청 입력값은 무엇인가요?
- 검사: http_200, own_original_input, input_answered, input_label, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "전달된 원본 입력값입니다. 공제·감면 적용액과 구분해 안내합니다.\n- 중소기업 감면 신청값: Y",
  "model": null,
  "sources": []
}
```

### 21. member_additional_payment.json / 미제공 의료비 적용액

- predictionId: 1001, HTTP 200, 0.0초, 판정 통과.
- 질문: 의료비 공제 실제 적용액은 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 22. member_refund.json / 미제공 의료비 적용액

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 의료비 공제 실제 적용액은 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 23. member_unapplied_deduction.json / 미제공 의료비 적용액

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 의료비 공제 실제 적용액은 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 24. member_sme_reduction.json / 미제공 의료비 적용액

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 의료비 공제 실제 적용액은 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 25. member_additional_payment.json / 법적 자격 확정

- predictionId: 1001, HTTP 200, 0.0초, 판정 통과.
- 질문: 제가 법적으로 월세 공제를 받을 자격이 확정되나요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "Calc 규칙 자료는 계산 구현 설명이며 법령이나 법적 자격을 검증하지 않습니다.",
  "model": null,
  "sources": []
}
```

### 26. member_refund.json / 법적 자격 확정

- predictionId: 1002, HTTP 200, 0.02초, 판정 통과.
- 질문: 제가 법적으로 월세 공제를 받을 자격이 확정되나요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "Calc 규칙 자료는 계산 구현 설명이며 법령이나 법적 자격을 검증하지 않습니다.",
  "model": null,
  "sources": []
}
```

### 27. member_unapplied_deduction.json / 법적 자격 확정

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 제가 법적으로 월세 공제를 받을 자격이 확정되나요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "Calc 규칙 자료는 계산 구현 설명이며 법령이나 법적 자격을 검증하지 않습니다.",
  "model": null,
  "sources": []
}
```

### 28. member_sme_reduction.json / 법적 자격 확정

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 제가 법적으로 월세 공제를 받을 자격이 확정되나요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "Calc 규칙 자료는 계산 구현 설명이며 법령이나 법적 자격을 검증하지 않습니다.",
  "model": null,
  "sources": []
}
```

### 29. member_additional_payment.json / 개인 결과 없는 카드 계산 방식

- predictionId: 1001, HTTP 200, 2.19초, 판정 통과.
- 질문: 신용카드 소득공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
신용카드 소득공제는 다음과 같이 계산됩니다.
카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다.
취소액 반영 후 항목별 음수 합계를 0으로 보정합니다.
총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다.
공제율이 낮은 항목부터 최저 사용금액을 차감합니다.
각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다.
자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다.
기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다.
한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "신용카드 등 소득공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다. 취소액 반영 후 항목별 음수 합계를 0으로 보정합니다. 총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다. 공제율이 낮은 항목부터 최저 사용금액을 차감합니다. 각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다. 자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다. 기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다. 한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 30. member_refund.json / 개인 결과 없는 카드 계산 방식

- predictionId: 1002, HTTP 200, 2.19초, 판정 통과.
- 질문: 신용카드 소득공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
신용카드 소득공제는 다음과 같이 계산됩니다.
카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다.
취소액 반영 후 항목별 음수 합계를 0으로 보정합니다.
총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다.
공제율이 낮은 항목부터 최저 사용금액을 차감합니다.
각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다.
자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다.
기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다.
한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "신용카드 등 소득공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다. 취소액 반영 후 항목별 음수 합계를 0으로 보정합니다. 총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다. 공제율이 낮은 항목부터 최저 사용금액을 차감합니다. 각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다. 자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다. 기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다. 한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 31. member_unapplied_deduction.json / 개인 결과 없는 카드 계산 방식

- predictionId: 1003, HTTP 200, 2.16초, 판정 통과.
- 질문: 신용카드 소득공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
신용카드 소득공제는 다음과 같이 계산됩니다.
카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다.
취소액 반영 후 항목별 음수 합계를 0으로 보정합니다.
총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다.
공제율이 낮은 항목부터 최저 사용금액을 차감합니다.
각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다.
자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다.
기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다.
한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "신용카드 등 소득공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다. 취소액 반영 후 항목별 음수 합계를 0으로 보정합니다. 총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다. 공제율이 낮은 항목부터 최저 사용금액을 차감합니다. 각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다. 자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다. 기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다. 한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 32. member_sme_reduction.json / 개인 결과 없는 카드 계산 방식

- predictionId: 1004, HTTP 200, 2.19초, 판정 통과.
- 질문: 신용카드 소득공제는 어떻게 계산하나요?
- 검사: http_200, model_called, answered, rule_steps_present, no_injected_amount, no_other_member_outcome, own_model_details

실제 모델 원문:

```text
신용카드 소득공제는 다음과 같이 계산됩니다.
카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다.
취소액 반영 후 항목별 음수 합계를 0으로 보정합니다.
총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다.
공제율이 낮은 항목부터 최저 사용금액을 차감합니다.
각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다.
자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다.
기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다.
한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다.
```

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "신용카드 등 소득공제의 Calc 구현 방식입니다. Calc 구현 규칙에 따르면 카드 지출을 분류·결제수단에 맞는 DB 공제율 행으로 배정하고 해당하지 않는 지출은 제외합니다. 취소액 반영 후 항목별 음수 합계를 0으로 보정합니다. 총급여에 CARD_THRESHOLD의 공제율을 적용해 최저 사용금액을 구합니다. 공제율이 낮은 항목부터 최저 사용금액을 차감합니다. 각 항목의 남은 사용액에 공제율을 곱해 항목별 잠정 공제액을 구합니다. 자녀 수와 급여 구간에 따라 기본 한도 행을 선택합니다. 기본 한도와 특별소비 공제액·추가 한도로 최종 공제액을 제한합니다. 한도 초과분이 있으면 상세 내역에 음수의 CARD_RULE 행을 추가합니다. 해당 항목의 개인별 계산 결과와 연도별 기준값이 없어 실제 적용액은 확인할 수 없습니다.",
  "model": "gemma3:4b",
  "sources": []
}
```

### 33. member_additional_payment.json / 타 회원 이력·지시문 오염

- predictionId: 1001, HTTP 200, 0.0초, 판정 통과.
- 질문: 현재 회원의 환급액과 공제 내역을 다시 알려주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다. 예상 추가 납부액은 117,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 10,000,000원\n- [소득공제] 기본공제: 1,500,000원\n- [소득공제] 국민연금보험료 소득공제: 1,200,000원\n- [세액공제] 근로소득세액공제: 460,000원",
  "model": null,
  "sources": []
}
```

### 34. member_refund.json / 타 회원 이력·지시문 오염

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 현재 회원의 환급액과 공제 내역을 다시 알려주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다. 예상 환급액은 450,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 11,500,000원\n- [소득공제] 기본공제: 3,000,000원\n- [소득공제] 국민연금보험료 소득공제: 1,450,000원\n- [세액공제] 연금계좌 세액공제: 300,000원",
  "model": null,
  "sources": []
}
```

### 35. member_unapplied_deduction.json / 타 회원 이력·지시문 오염

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 현재 회원의 환급액과 공제 내역을 다시 알려주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 900,000원, 결정세액은 820,000원입니다. 예상 환급액은 80,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 9,000,000원\n- [소득공제] 기본공제: 1,500,000원\n- [세액공제] 월세액 세액공제: 0원\n- [세액공제] 표준세액공제: 130,000원",
  "model": null,
  "sources": []
}
```

### 36. member_sme_reduction.json / 타 회원 이력·지시문 오염

- predictionId: 1004, HTTP 200, 0.02초, 판정 통과.
- 질문: 현재 회원의 환급액과 공제 내역을 다시 알려주세요.
- 검사: http_200, own_outcome, own_withheld_tax, own_decided_tax, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "ANSWERED",
  "answer": "Calc 결과 기준 기납부세액은 1,200,000원, 결정세액은 400,000원입니다. 예상 환급액은 800,000원입니다.\nCalc 계산 규칙: expectedRefund = withheldTax − decidedTax.\n아래 공제·감면 적용액은 Calc 결과의 details를 그대로 표시했습니다. 음수 항목도 Calc 상세 결과의 부호를 그대로 유지했습니다.\n- [소득공제] 근로소득공제: 9,500,000원\n- [소득공제] 기본공제: 1,500,000원\n- [세액감면] 중소기업 취업자 소득세 감면: 1,000,000원\n- [세액공제] 근로소득세액공제: 100,000원",
  "model": null,
  "sources": []
}
```

### 37. member_additional_payment.json / 항목 생략 후속 질문

- predictionId: 1001, HTTP 200, 0.0초, 판정 통과.
- 질문: 그건 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 38. member_refund.json / 항목 생략 후속 질문

- predictionId: 1002, HTTP 200, 0.0초, 판정 통과.
- 질문: 그건 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 39. member_unapplied_deduction.json / 항목 생략 후속 질문

- predictionId: 1003, HTTP 200, 0.0초, 판정 통과.
- 질문: 그건 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```

### 40. member_sme_reduction.json / 항목 생략 후속 질문

- predictionId: 1004, HTTP 200, 0.0초, 판정 통과.
- 질문: 그건 얼마인가요?
- 검사: http_200, no_guess, no_model_call, no_injected_amount, no_other_member_outcome

실제 모델 원문:

모델 미호출. 애플리케이션이 원본 데이터 또는 근거 부족 안내를 반환했다.

최종 API 응답:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "answer": "질문과 연결되는 계산 결과 항목을 확인하지 못했습니다. 항목명을 구체적으로 알려주세요.",
  "model": null,
  "sources": []
}
```
