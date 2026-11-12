# 로컬 개발 채팅 화면 검증 — 2026-11-12

## 구성

- `python -m devtools.server`로 별도 루프백 서버를 실행하고 브라우저는 `/dev/*`만 요청한다. 개발 서버가 기존 FastAPI 앱의 `/internal/recommendations`, `/internal/chat-responses`를 ASGI HTTP 경계로 호출한다. 별도 운영 서버·Spring Boot를 경유하는 E2E는 아니다.
- 기존 토큰은 서버 환경에서만 읽는다. 미설정 시 CLI가 해당 프로세스에만 임시 토큰을 만들고 브라우저에는 보내지 않는다. 내부 API의 인증·DTO·오류 처리·실제 Ollama 연결을 그대로 사용한다.
- 개발 모드와 명시적 활성화가 모두 없으면 비활성화한다. 활성화해도 클라이언트 IP·Host 루프백 확인, POST Origin 동일 출처 확인, cross-site 차단·JSON 제한을 적용한다. 운영 앱에는 개발 라우터를 추가하지 않았다.
- 더미 회원은 서버 고정 허용 목록으로만 로드한다. 선택·질문 엔드포인트는 운영 API의 새 계약이 아닌 별도 개발 경로다. HTML은 외부 자산·대규모 프론트 의존성 없이 동작한다.

## 검증 결과

- Ruff check 통과, Ruff format --check 통과(53개 파일), pytest -v 222개 통과(2.11초). 기존 202개와 개발 경계·인증·API 경유·오류 등 신규 20개를 포함한다. pytest의 모델은 Mock이며 아래 실제 브라우저 검사와 구분한다.
- 실제 실행한 로컬 개발 서버(http://127.0.0.1:8002)와 Ollama gemma3:4b 환경에 Edge 헤드리스 브라우저를 연결했다. tests/validate_dev_ui_browser.cjs는 Node 24 내장 WebSocket/CDP만 사용했으며 npm/Playwright 의존성을 추가하지 않았다.
- 더미 4종 각각 최초 브리핑 1건→적용액 후속 질문→계산 방식 후속 질문 12건 모두 내부 API HTTP 200을 확인했다. 처음 후속 요청 history는 해당 회원의 최초 브리핑 1개이고 다음은 3개이며 predictionId가 현재 회원과 같음을 확인했다.
- 6회 추가 후속 질문으로 최근 10개 메시지 제한을 확인했다. 회원 변경 후 기존 대화가 지워지고 최초 브리핑 1건만 남는다. 선택 해제 후 입력 비활성화·이력 0개도 확인했다.
- 브라우저 요청에 X-Chatbot-Token 헤더와 /internal/ 직접 호출이 없음을 확인했다. 예외 UI·개발자 JSON에도 토큰이 포함되지 않는 검사는 pytest에서 고정 테스트 토큰으로 확인했다.
- 직접 Gemma 호출 계측은 추가하지 않았다. 화면은 직접 호출 확인 불가와 API 응답 model 값을 별도 표시한다. fallback이나 응답 메타데이터를 호출 여부라고 추측하지 않는다. 실제 브라우저 실행은 Mock 주입 없이 기본 Ollama 의존성을 사용했지만 요청별 호출 수·원문은 이 도구에서 계측하지 않는다.
- 브라우저 네트워크 오프라인을 CDP로 재현해 한국어 서버 연결 실패 안내와 입력 복구를 확인했다. HTML 형태의 질문을 입력해도 텍스트로만 표시되고 img 요소·이벤트 코드가 실행되지 않음을 확인했다. JavaScript 미처리 예외는 0개다.
- 별도 TestClient 실행에서 OLLAMA_BASE_URL=http://127.0.0.1:1로 실제 접속 거부를 유도해 503 OLLAMA_UNAVAILABLE과 안전한 한국어 오류 반환을 확인했다. 실제 실행 중인 Ollama 프로세스를 중지한 검사는 아니다. 대기 초과는 pytest의 ReadTimeout Mock 검사이며 45/50/55/65초 경과 및 5초 UI 지연 문구의 실제 시간 실측은 하지 않았다.
- 최초 렌더 확인 중 긴 브리핑의 마지막 부분부터 표시되는 문제와 hidden label 표시를 보완해 최초 메시지는 맨 위부터 보이게 했고 최종 브라우저 검사를 재실행했다.

## 남은 제한

- 로컬 개발 도구이며 운영 사용자 인증·Oracle 저장·Spring Boot 실연동은 없다. 개발 플래그가 켜진 기기의 로컬 사용자/프로세스 접근은 허용한다. 공용 프록시·터널에 노출하는 용도가 아니다.
- 대화는 브라우저 메모리만 사용하고 새로고침 시 삭제한다. 실패 문답은 다음 이력에 넣지 않으며 4,000자를 넘는 단일 메시지도 이력 전송에서 제외한다.
- 회원 변경·브라우저 중단은 이전 모델 추론을 강제로 끝내지 못한다. 이전 추론의 MODEL_BUSY가 나면 잠시 기다렸다가 브리핑을 다시 생성한다. 순차 브라우저 검증이며 실행 중 회원을 바꾸는 경합·다중 탭 부하의 실모델 검증은 하지 않았다. 화면은 세대 번호 검사와 AbortController로 늦은 응답이 새 회원에 추가되지 않게 처리한다.
- 직접 모델 호출을 정확히 표시하려면 향후 요청별 서버 추론 계측이 필요하다. 현재는 명시적으로 확인 불가를 표시한다.

## 실제 브라우저 API 기록

### additional

#### briefing

- 내부 HTTP 200, 처리 1390ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/recommendations",
    "body": {
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1001,
        "withheldTax": 1523000,
        "decidedTax": 1640000,
        "expectedRefund": -117000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 36000000,
            "deductionAmount": 10000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1200000,
            "deductionAmount": 1200000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2100000,
            "deductionAmount": 460000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 36000000,
          "nationalPension": 1200000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      }
    }
  },
  "response": {
    "status": "ANSWERED",
    "recommendations": [
      {
        "typeCode": null,
        "content": "예상 추가 납부액은 117,000원입니다. 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 10,000,000원; 기본공제 1,500,000원; 국민연금보험료 소득공제 1,200,000원; 근로소득세액공제 460,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
        "model": "gemma3:4b",
        "sources": []
      }
    ]
  },
  "elapsedMs": 1390,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### first

- 내부 HTTP 200, 처리 0ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "국민연금 공제 금액은 얼마인가요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1001,
        "withheldTax": 1523000,
        "decidedTax": 1640000,
        "expectedRefund": -117000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 36000000,
            "deductionAmount": 10000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1200000,
            "deductionAmount": 1200000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2100000,
            "deductionAmount": 460000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 36000000,
          "nationalPension": 1200000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 추가 납부액은 117,000원입니다. 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 10,000,000원; 기본공제 1,500,000원; 국민연금보험료 소득공제 1,200,000원; 근로소득세액공제 460,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 관련 적용액입니다.\n- [소득공제] 국민연금보험료 소득공제: 1,200,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
    "model": null,
    "sources": []
  },
  "elapsedMs": 0,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### method

- 내부 HTTP 200, 처리 797ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "국민연금 공제는 어떻게 계산하나요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1001,
        "withheldTax": 1523000,
        "decidedTax": 1640000,
        "expectedRefund": -117000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 36000000,
            "deductionAmount": 10000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1200000,
            "deductionAmount": 1200000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2100000,
            "deductionAmount": 460000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 36000000,
          "nationalPension": 1200000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 추가 납부액은 117,000원입니다. 기납부세액은 1,523,000원, 결정세액은 1,640,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 10,000,000원; 기본공제 1,500,000원; 국민연금보험료 소득공제 1,200,000원; 근로소득세액공제 460,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        },
        {
          "role": "user",
          "content": "국민연금 공제 금액은 얼마인가요?"
        },
        {
          "role": "assistant",
          "content": "Calc 결과의 관련 적용액입니다.\n- [소득공제] 국민연금보험료 소득공제: 1,200,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 국민연금보험료 소득공제 1,200,000원 적용액을 기준으로 설명합니다. Calc 구현 규칙에 따르면 입력된 국민연금보험료에 DB의 공제율을 적용합니다. 개인별 실제 적용액은 Calc 결과에 표시된 값입니다.",
    "model": "gemma3:4b",
    "sources": []
  },
  "elapsedMs": 797,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

### refund

#### briefing

- 내부 HTTP 200, 처리 937ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/recommendations",
    "body": {
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1002,
        "withheldTax": 1800000,
        "decidedTax": 1350000,
        "expectedRefund": 450000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 40000000,
            "deductionAmount": 11500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 3000000,
            "deductionAmount": 3000000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1450000,
            "deductionAmount": 1450000,
            "sourceNote": null
          },
          {
            "typeCode": "PENSION",
            "typeName": "연금계좌 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2000000,
            "deductionAmount": 300000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 40000000,
          "nationalPension": 1450000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 2000000,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      }
    }
  },
  "response": {
    "status": "ANSWERED",
    "recommendations": [
      {
        "typeCode": null,
        "content": "예상 환급액은 450,000원입니다. 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 11,500,000원; 기본공제 3,000,000원; 국민연금보험료 소득공제 1,450,000원; 연금계좌 세액공제 300,000원.\n\n현재 입력과 결과에서 추가 검토할 사유를 확인하지 못해 임의 추천은 하지 않습니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
        "model": "gemma3:4b",
        "sources": []
      }
    ]
  },
  "elapsedMs": 937,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### first

- 내부 HTTP 200, 처리 0ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "연금저축 공제 금액은 얼마인가요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1002,
        "withheldTax": 1800000,
        "decidedTax": 1350000,
        "expectedRefund": 450000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 40000000,
            "deductionAmount": 11500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 3000000,
            "deductionAmount": 3000000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1450000,
            "deductionAmount": 1450000,
            "sourceNote": null
          },
          {
            "typeCode": "PENSION",
            "typeName": "연금계좌 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2000000,
            "deductionAmount": 300000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 40000000,
          "nationalPension": 1450000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 2000000,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 450,000원입니다. 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 11,500,000원; 기본공제 3,000,000원; 국민연금보험료 소득공제 1,450,000원; 연금계좌 세액공제 300,000원.\n\n현재 입력과 결과에서 추가 검토할 사유를 확인하지 못해 임의 추천은 하지 않습니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 연금계좌 세액공제: 300,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
    "model": null,
    "sources": []
  },
  "elapsedMs": 0,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### method

- 내부 HTTP 200, 처리 1282ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "연금저축 공제는 어떻게 계산하나요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1002,
        "withheldTax": 1800000,
        "decidedTax": 1350000,
        "expectedRefund": 450000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 40000000,
            "deductionAmount": 11500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 3000000,
            "deductionAmount": 3000000,
            "sourceNote": null
          },
          {
            "typeCode": "NATIONAL_PENSION",
            "typeName": "국민연금보험료 소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1450000,
            "deductionAmount": 1450000,
            "sourceNote": null
          },
          {
            "typeCode": "PENSION",
            "typeName": "연금계좌 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 2000000,
            "deductionAmount": 300000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 40000000,
          "nationalPension": 1450000,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 2000000,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 450,000원입니다. 기납부세액은 1,800,000원, 결정세액은 1,350,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 11,500,000원; 기본공제 3,000,000원; 국민연금보험료 소득공제 1,450,000원; 연금계좌 세액공제 300,000원.\n\n현재 입력과 결과에서 추가 검토할 사유를 확인하지 못해 임의 추천은 하지 않습니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        },
        {
          "role": "user",
          "content": "연금저축 공제 금액은 얼마인가요?"
        },
        {
          "role": "assistant",
          "content": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 연금계좌 세액공제: 300,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 연금계좌 세액공제 300,000원 적용액을 기준으로 설명합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.",
    "model": "gemma3:4b",
    "sources": []
  },
  "elapsedMs": 1282,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

### rent

#### briefing

- 내부 HTTP 200, 처리 2078ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/recommendations",
    "body": {
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1003,
        "withheldTax": 900000,
        "decidedTax": 820000,
        "expectedRefund": 80000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 30000000,
            "deductionAmount": 9000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "RENT",
            "typeName": "월세액 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 6000000,
            "deductionAmount": 0,
            "sourceNote": null
          },
          {
            "typeCode": "STANDARD_CREDIT",
            "typeName": "표준세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 0,
            "deductionAmount": 130000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 30000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 500000,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      }
    }
  },
  "response": {
    "status": "ANSWERED",
    "recommendations": [
      {
        "typeCode": null,
        "content": "예상 환급액은 80,000원입니다. 기납부세액은 900,000원, 결정세액은 820,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,000,000원; 기본공제 1,500,000원; 표준세액공제 130,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 월 월세 입력액은 500,000원입니다. 월세 세액공제: 계산 기준액 6,000,000원, 실제 적용액 0원. 월세 납부 자료와 무주택 세대주 입력값을 확인해 주세요. 무주택 세대주 입력은 N입니다. 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 미적용이나 상세행 누락의 구체적인 원인은 현재 결과만으로 확정할 수 없습니다.\n\n2. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
        "model": "gemma3:4b",
        "sources": []
      }
    ]
  },
  "elapsedMs": 2078,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### first

- 내부 HTTP 200, 처리 0ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "월세 공제 금액은 얼마인가요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1003,
        "withheldTax": 900000,
        "decidedTax": 820000,
        "expectedRefund": 80000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 30000000,
            "deductionAmount": 9000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "RENT",
            "typeName": "월세액 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 6000000,
            "deductionAmount": 0,
            "sourceNote": null
          },
          {
            "typeCode": "STANDARD_CREDIT",
            "typeName": "표준세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 0,
            "deductionAmount": 130000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 30000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 500000,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 80,000원입니다. 기납부세액은 900,000원, 결정세액은 820,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,000,000원; 기본공제 1,500,000원; 표준세액공제 130,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 월 월세 입력액은 500,000원입니다. 월세 세액공제: 계산 기준액 6,000,000원, 실제 적용액 0원. 월세 납부 자료와 무주택 세대주 입력값을 확인해 주세요. 무주택 세대주 입력은 N입니다. 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 미적용이나 상세행 누락의 구체적인 원인은 현재 결과만으로 확정할 수 없습니다.\n\n2. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 월세액 세액공제: 0원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
    "model": null,
    "sources": []
  },
  "elapsedMs": 0,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### method

- 내부 HTTP 200, 처리 2531ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "월세 공제는 어떻게 계산하나요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1003,
        "withheldTax": 900000,
        "decidedTax": 820000,
        "expectedRefund": 80000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 30000000,
            "deductionAmount": 9000000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "RENT",
            "typeName": "월세액 세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 6000000,
            "deductionAmount": 0,
            "sourceNote": null
          },
          {
            "typeCode": "STANDARD_CREDIT",
            "typeName": "표준세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 0,
            "deductionAmount": 130000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 30000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 500000,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "N",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 80,000원입니다. 기납부세액은 900,000원, 결정세액은 820,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,000,000원; 기본공제 1,500,000원; 표준세액공제 130,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 월 월세 입력액은 500,000원입니다. 월세 세액공제: 계산 기준액 6,000,000원, 실제 적용액 0원. 월세 납부 자료와 무주택 세대주 입력값을 확인해 주세요. 무주택 세대주 입력은 N입니다. 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 미적용이나 상세행 누락의 구체적인 원인은 현재 결과만으로 확정할 수 없습니다.\n\n2. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        },
        {
          "role": "user",
          "content": "월세 공제 금액은 얼마인가요?"
        },
        {
          "role": "assistant",
          "content": "Calc 결과의 관련 적용액입니다.\n- [세액공제] 월세액 세액공제: 0원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 월세액 세액공제 0원 적용액을 기준으로 설명합니다. Calc 구현 규칙에 따르면 총급여 구간에 맞는 월세 기준 행과 무주택 세대주 조건을 확인합니다. 연간 월세액(월 월세 × 12)과 DB 공제 대상 한도 중 작은 금액에 DB 공제율을 적용합니다. 건강·고용보험료 소득공제+월세 세액공제를 사용하는 방안과 표준세액공제 방안을 비교해 결정세액이 작은 쪽을 택합니다. 제공된 결과만으로는 해당 적용액의 구체적인 원인을 특정할 수 없습니다.",
    "model": "gemma3:4b",
    "sources": []
  },
  "elapsedMs": 2531,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

### sme

#### briefing

- 내부 HTTP 200, 처리 1375ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/recommendations",
    "body": {
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1004,
        "withheldTax": 1200000,
        "decidedTax": 400000,
        "expectedRefund": 800000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 32000000,
            "deductionAmount": 9500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "SME_YOUTH",
            "typeName": "중소기업 취업자 소득세 감면",
            "kind": "TAX_REDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1000000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 1500000,
            "deductionAmount": 100000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 32000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "Y",
          "homelessHeadYn": "N"
        }
      }
    }
  },
  "response": {
    "status": "ANSWERED",
    "recommendations": [
      {
        "typeCode": null,
        "content": "예상 환급액은 800,000원입니다. 기납부세액은 1,200,000원, 결정세액은 400,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,500,000원; 기본공제 1,500,000원; 중소기업 취업자 소득세 감면 1,000,000원; 근로소득세액공제 100,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다.",
        "model": "gemma3:4b",
        "sources": []
      }
    ]
  },
  "elapsedMs": 1375,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### first

- 내부 HTTP 200, 처리 0ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "중소기업 감면 공제 금액은 얼마인가요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1004,
        "withheldTax": 1200000,
        "decidedTax": 400000,
        "expectedRefund": 800000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 32000000,
            "deductionAmount": 9500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "SME_YOUTH",
            "typeName": "중소기업 취업자 소득세 감면",
            "kind": "TAX_REDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1000000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 1500000,
            "deductionAmount": 100000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 32000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "Y",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 800,000원입니다. 기납부세액은 1,200,000원, 결정세액은 400,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,500,000원; 기본공제 1,500,000원; 중소기업 취업자 소득세 감면 1,000,000원; 근로소득세액공제 100,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 관련 적용액입니다.\n- [세액감면] 중소기업 취업자 소득세 감면: 1,000,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다.",
    "model": null,
    "sources": []
  },
  "elapsedMs": 0,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```

#### method

- 내부 HTTP 200, 처리 1328ms. 직접 모델 호출 확인: 불가.

```json
{
  "ok": true,
  "httpStatus": 200,
  "request": {
    "path": "/internal/chat-responses",
    "body": {
      "questionType": "TAX_RESULT",
      "message": "중소기업 감면 공제는 어떻게 계산하나요?",
      "taxYear": 2026,
      "taxResult": {
        "predictionId": 1004,
        "withheldTax": 1200000,
        "decidedTax": 400000,
        "expectedRefund": 800000,
        "details": [
          {
            "typeCode": "EARNED_DEDUCTION",
            "typeName": "근로소득공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 32000000,
            "deductionAmount": 9500000,
            "sourceNote": null
          },
          {
            "typeCode": "PERSON_BASIC",
            "typeName": "기본공제",
            "kind": "INCOME_DEDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1500000,
            "sourceNote": null
          },
          {
            "typeCode": "SME_YOUTH",
            "typeName": "중소기업 취업자 소득세 감면",
            "kind": "TAX_REDUCTION",
            "baseAmount": 1500000,
            "deductionAmount": 1000000,
            "sourceNote": null
          },
          {
            "typeCode": "EARNED_CREDIT",
            "typeName": "근로소득세액공제",
            "kind": "TAX_CREDIT",
            "baseAmount": 1500000,
            "deductionAmount": 100000,
            "sourceNote": null
          }
        ],
        "inputs": {
          "totalSalary": 32000000,
          "nationalPension": 0,
          "healthInsurance": 0,
          "monthlyRent": 0,
          "housingSaving": 0,
          "pensionSaving": 0,
          "irpSaving": 0,
          "smeReductionYn": "Y",
          "homelessHeadYn": "N"
        }
      },
      "history": [
        {
          "role": "assistant",
          "content": "예상 환급액은 800,000원입니다. 기납부세액은 1,200,000원, 결정세액은 400,000원입니다.\n\n전달된 공제·감면 적용 내역: 근로소득공제 9,500,000원; 기본공제 1,500,000원; 중소기업 취업자 소득세 감면 1,000,000원; 근로소득세액공제 100,000원.\n\n공제·감면 자료에서 확인해 볼 사항입니다.\n\n1. 연금저축·IRP 납입 입력은 각각 0원이며 결정세액이 남아 있습니다. 향후 연금계좌 납입 계획이 있다면 연금저축과 IRP의 별도·합산 한도 및 적용 조건을 검토할 수 있습니다. 현재 추가 납입이나 가입을 권유하는 것은 아니며, 자금 계획과 실제 적용 여부를 먼저 확인해야 합니다. 연금저축 납입액에 단독 한도를 먼저 적용합니다. 해당 연금저축액과 IRP 납입액 합계에 연금계좌 전체 한도를 적용합니다. DB 공제율을 적용한 세액공제 후보를 구합니다. 남아 있는 산출세액을 넘지 않도록 적용합니다.\n\n계산 기준액은 원래 입력 전체를 뜻하지 않습니다. 결과에 없는 항목은 미신청이나 부적격으로 판단하지 않았습니다. 추가 절세 가능 금액과 자격은 확인되지 않아 안내하지 않습니다."
        },
        {
          "role": "user",
          "content": "중소기업 감면 공제 금액은 얼마인가요?"
        },
        {
          "role": "assistant",
          "content": "Calc 결과의 관련 적용액입니다.\n- [세액감면] 중소기업 취업자 소득세 감면: 1,000,000원\n전달된 details의 deductionAmount를 그대로 표시했으며 재계산하지 않았습니다."
        }
      ]
    }
  },
  "response": {
    "status": "ANSWERED",
    "answer": "Calc 결과의 중소기업 취업자 소득세 감면 1,000,000원 적용액을 기준으로 설명합니다. Spring Boot가 별도 혜택 진단 결과를 바탕으로 감면 신청값을 정리해 Calc에 전달합니다. 감면 기준 행이 있고 신청값이 Y이면 산출세액 × DB 감면율과 DB 한도 중 작은 금액을 계산합니다. 산출세액에서 아직 남아 있는 세액 이하로 실제 감면액을 제한합니다.",
    "model": "gemma3:4b",
    "sources": []
  },
  "elapsedMs": 1328,
  "modelCall": {
    "verified": false,
    "message": "직접 모델 호출 여부는 확인 불가합니다. 응답의 model 값만 표시합니다."
  }
}
```
