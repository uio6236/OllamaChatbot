# 04. LangChain + Ollama + Elasticsearch RAG 설계

## 서비스 기능 기준의 카드 최소 평가 구성

### 최소 자연어 설명 확장

기존 6개 영역과 선택 정책 focused-card-extractive-v1, 원문 선택 모드는 변경하지 않는다. focused_card.py에 card_facts/natural_prompt/validate_natural, 기존 CLI에 compare_natural 및 --natural을 추가한다. 새 파일·의존성·공개 DTO·승인 정책은 추가하지 않는다. 자연어 모드는 기존 material.json과 두 평가 인덱스를 검증하여 읽기만 수행하며 저장/재색인 없이 결과 JSON을 표준 출력으로 반환한다.

흐름은 기존 검색·원문 조립/스냅샷 확인→6개 자료 일치 확인→CAP 실제 검색 확인→Gemma ID 선택→CAP/DEFINITION 선택 확인→원문 조건 추출→Gemma 도입문 작성→의미·인용 검사→서버 사실 표시다. 기존 GenerationService 슬롯·오류·대기 경계와 ChatOllama를 재사용한다. 적용 미확인 자료를 운영 생성 경로에 넣지 않는다.

card_facts는 해당 법률 조문의 한정된 문법만 해석한다. 총급여 기준 문자열, 무자녀 기본 한도, 같은 소득구간의 자녀 수와 한도, ‘제1호 외’의 반대 소득구간을 연결한다. 값은 코드 상수가 아니라 원문 정규식 캡처다. 각 숫자의 정확성만 보는 것이 아니라 급여 구간·자녀 수와 금액의 결합을 검사한다. 인접 조건·단서·자녀 정의의 모든 요건, 장애 나이 예외, 다른 거주자 기본공제 부정 표현이 없으면 실패한다. 원문·버전·내용 해시·인용 ID와 함께 반환한다. 미지원 형식의 법령을 추측해서 보정하지 않으며 세액이나 환급액을 계산하지 않는다.

법률 원문 숫자를 생성 프롬프트에 다시 모두 전달했을 때 Gemma가 금액을 재작성하며 끊긴 문장과 중복 인용을 만들었다. 최종 생성 단계에는 파싱으로 확인한 관계만 전달한다. 모델은 실제 한 문장을 생성하지만 금액·조건은 서버가 별도로 표시한다. 금액을 포함한 모델 자유문을 숫자 존재만 확인하여 허용하는 기능이 아니다.

허용 관계는 ‘공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라진다’라는 단일 명제로 한정한다. 실제 관찰한 종결형·주어 순서 차이는 같은 의미로 검사한다. 추가 문장, 추가 한도까지 같은 관계로 넓히기, 숫자/날짜, 자격 인정, 미지원 동의 표현 등은 기본 보류한다. 일반 문장의 사실성을 자동 증명하지 않는다. 빈 도입문은 MODEL_WITHHELD, 잘못된 관계는 UNVERIFIED_SEMANTIC_RELATION, 인용 오류는 UNTRACEABLE_NATURAL_CITATION으로 구분한다.

최종 답변은 모델 도입문→서버의 기본 한도 두 구간→자녀 인정 조건 세 항목(나이·장애 예외·중복공제 제한 포함)→기본/추가 한도 구분→미검증 안내 순서다. 모델이 선택한 근거와 강제 연결된 필수 문맥의 출처를 모두 보존한다. F3의 추가한도는 필수 문맥으로만 참조하고 금액·귀속연도는 확정하지 않는다. 정의의 외부 준용 전체와 적용시점은 기존 unresolvedIssues로 남긴다.

selection/naturalGenerated/numbersAndConditions/citations/applicabilityVerified/userDisplayAllowed를 분리한다. NATURAL_EVALUATION이어도 applicabilityVerified와 userDisplayAllowed는 false다. 검사 통과는 제한된 관계 및 서버 원문 기반 표시의 기술 검증이며 전문 검토·독립 정답 라벨·2026년 법적 적용 검증을 대체하지 않는다. 특히 대학생·중복공제 질문에서 도입문 자체는 일반적이므로 질문별 직접 답변 품질은 추가 점검이 필요하다.

평가 질문은 생성 기능 수정 전에 기존 테스트 파일에 개발 8개/최종 점검 4개로 고정했다. 질문 묶음 SHA-256은 bcf2d70dabb6364a355e17965d4ccde4a72d6f865241096fbb2d27530fc779d1이다. 개발 출력의 동등 문장에 대한 검사 수정 후 최종 점검을 처음 실행했으며 그 결과를 보고 다시 튜닝하지 않았다. 작은 자체 작성 세트이므로 독립 전문가 평가나 통계적 일반화 근거가 아니다.

실제 Gemma 최종 결과는 개발3/8·최종2/4가 제한된 검사를 통과했다. 실행된 9문항의 근거 선택은 성공했고, 3문항은 범위 단계에서 모델 미호출이다. 자연어 생성은 6문항이 비어 있지 않은 문장을 반환했고 그중 추가한도 관계를 넓힌 1문항을 차단했다. 운영 표시 가능은 0건이다. 무자녀·나이 질문의 모델 보류, 외동 표현 오차단, 더 직접적인 답변과 조건 문장의 쉬운 표현은 남은 작업이다. 이 결과로 다른 공제를 자동 확대하지 않는다.

### 실제 로컬 지원 범위

이 분류는 현재 checkout의 코드 기준이다. 팀원이 다른 브랜치에서 개발 중인 기능이나 최신 기능명세서 v1.13 원본은 확인하지 못했으므로 완료로 추정하지 않는다. 로컬 `calc/app/main.py`는 Health만 등록하며 계산 라우터는 TODO다. `backend/src/main/java/com/hoperefund/`도 공통 Health·설정·예외 클래스만 있고 계산 DTO·서비스는 없다. 실제 법정 계산까지 완료한 SUPPORTED 항목은 확인되지 않았다.

| 기능 후보 | 로컬 상태 | 확인한 구현과 미구현 부분 |
|---|---|---|
| 총급여·산출·결정·환급·추가납부 | PARTIAL | frontend/src/api/services.js의 taxService.calculate 체험값, calculation-contract.js의 parseCalculationResult·settlementLabel 관련 표시. taxableIncome은 null, 실제 계산/조회 API 미연동 |
| 근로소득공제·근로소득세액공제 | PARTIAL | services.js의 EARNED_DEDUCTION/EARNED_CREDIT 결과 자리는 있으나 값 0의 자리표시이며 법정 산식 없음 |
| 본인·부양가족·자녀 | PARTIAL | TaxInfoForm 입력, validateTaxData의 자녀 수≤부양가족 수 검사, family 체험 계산. 소득·나이·중복 자격 및 자녀별 실제 공제 산식 없음 |
| 카드·체크·현금영수증 | PARTIAL | 결제수단 입력·체험 비율·결과 details. 급여 기준·사용금액·자녀 한도를 적용한 Calc 계산 없음 |
| 시장·교통·문화비 | PARTIAL | services.js categories, dashboardModel의 거래 집계. 법정 공제액은 미계산/0 표시 |
| 사회보험료 | PARTIAL | nationalPension·healthEmploymentInsurance 입력/체험 details, 실제 인정액·산식 없음 |
| 월세·청약 | PARTIAL | rent·housingSaving 입력, Dashboard.jsx의 확인 필요/법정 미연동 안내, 체험 산식만 존재 |
| 연금저축·IRP | PARTIAL | pensionSaving·irp 입력/체험 details, 법정 한도·세액공제율 검증 없음 |
| 중소기업 취업자 감면 | PARTIAL | sme·companySize·employed 입력/체험값, dashboard-model.js youthStatus는 자가 입력 안내만 제공 |
| 군복무·청년 연령 | PARTIAL | militaryMonths 입력·범위 검사. 취업 당시 나이·복무 차감·감면기간 실제 판단 없음 |
| 사업·종교·양도·투자 세무 상담 | OUT_OF_SCOPE | 초기 근로자 연말정산 설명 범위에서 제외. 필요한 정의 준용만 개별 유지 |

따라서 초기 목표는 **일반 제도 원문 설명 평가**이며 검증된 사용자 계산 결과 설명은 아직 PLANNED다. 최신 Calc/Backend 결과 계약을 확보하기 전에는 체험값을 확정 계산 결과로 설명하지 않는다. 카드 자녀 한도만 신규 구성으로 평가하고, 검증 후 월세→청약→연금·사회보험→청년 감면 순으로 별도 확대한다. 근로소득·인적공제·세액 흐름은 실제 계산 계약과 함께 우선순위를 다시 정한다. 모든 공제를 동시에 재구성하지 않는다.

### 재사용·단순화·보존 경계

- 계속 재사용: PyMuPDF 전처리·원문/manifest 해시, v3 영역/증거/조건 기록, Evidence/Source, assemble_evaluation_bundle의 원본·스냅샷 대조, EvaluationStore의 loopback/eval 경계·색인 검증, GenerationService의 호출 제한·오류와 기존 ChatOllama.
- 별도 최소 구성: app/rag/focused_card.py의 항 단위 원문 분리·출처 연결·선택 검증과 scripts/evaluate_focused_card.py의 비교 CLI. 공개 DTO·운영 생성 흐름과 연결하지 않는다.
- 당장은 보관: 전체 3,186개 청크·기존 전처리 CLI·33/67개 선정·기존 비교/정성 생성 평가·광범위 검수 대기열. 삭제·재처리·검수 정책 확장 없음.
- 새 평가에서만 대체: 긴 조문 전체와 공제율·과거 계산식을 한꺼번에 전달하는 방식 → 자녀 한도 질문에 맞는 원문 영역. 기존 파일과 평가 결과는 변경하지 않는다.

### 원문 구성과 구조화 데이터

기존 v3 카드 초안으로 조립·검증한 5개 Evidence에서 6개 영역을 만든다.

| 역할 | 원문 영역 | 유지하는 이유 |
|---|---|---|
| CAP | 조세특례제한법 제126조의2⑩ | 총급여 구간·자녀 수별 한도, 단서와 각 호 전체 |
| DEFINITION | 시행령 제121조의2⑱ | 소득·나이·장애 예외·다른 거주자 기본공제 제한 |
| ADDITIONAL_LIMIT_CONTEXT | 법률 제126조의2⑪ | 기본 한도와 추가한도 구분, 참조 대상의 연도 조건은 단정하지 않음 |
| ELIGIBILITY | 법률 제126조의2① | 근로소득 거주자·제외·기본 사용금액 조건과 정의를 원문 그대로 유지 |
| APPLICATION 2개 | 법률 제21223호·대통령령 제36127호 부칙 제1조 | 각 시행일과 예외를 분리하여 보존 |

각 영역은 원본 chunkId·버전·원문 Evidence ID·부모 내용 해시·부모 내 start/end·선택 내용 해시·페이지·공식 법령 ID/버전·URL·기존 조회일/스냅샷 해시와 연결된다. 부모는 기존 v3 영역이므로 원본까지의 검증 사슬을 재사용한다. 페이지 범위는 부모 출처의 보수적 범위이며 새 PDF 페이지를 만들어낸 값이 아니다.

structuredEvidence는 역할·verbatim·수치 문자열의 원문 오프셋을 보존한다. 수치의 법적 의미나 귀속연도를 자동으로 판정한 테이블이 아니며 derivedExplanation은 null이다. 새 계산 엔진·임의 금액·검수 원장·자동 승인 기능은 없다. 소득세법 시행령 제106조 및 장애인 정의 외부 참조, 연간 공제와 정의 시행일의 연결은 기존 unresolvedIssues를 유지한다. 전체 필수 문맥이 법적으로 완결됐다고 선언하지 않는다.

### 검색·생성·검증 계약

기존 33개 인덱스 검증→기존 질문 범위 판별 및 카드 근거 조립→원문 영역 재구성·재현성 해시→별도 평가 인덱스 6건→BM25에서 CAP 검색 확인→6개 필수 문맥 전달→Gemma 원문 ID 선택→CAP·DEFINITION 동시 선택 검증→원문 무변경 표시 순서다. 새 구성은 자녀/한도 카드 질문에만 적용하며 다른 공제·혼합·게임·대출·추천 질문을 보류한다.

LLM 자유문을 기존 숫자 검증기에서 예외로 통과시키지 않는다. 모델 출력은 status/evidenceIds 두 키만 허용하고 원문에 없는 숫자·인용·설명 필드는 거부한다. 선택된 원문은 서버가 그대로 인용하며 모든 필수 문맥을 별도 requiredContext로 반환한다. 문맥 완전성은 사용자/전문가 검토가 필요하다. 결과는 EXTRACTIVE_EVALUATION 또는 HOLD이며 ANSWERED·VERIFIED·APPROVED가 아니다. 운영 사용은 항상 false다.

### 실서버 비교와 한계

대표 질문은 “애가 둘이면 카드로 쓴 돈의 공제 상한도 달라지나요?”다. 최종 결과는 data/processed/focused-card-evaluations/2d142846b5a5e8733fb7d74143415ecd7c0b8906834f4911722cf325ba3249a7/evaluation.json에 보존했다. 별도 자료는 focused-card-materials/9df21a30d99c02fd895979d5fa86c8d264088db69f0ec185591e8c8ac370b503/material.json이다.

- 기존 자유 생성: MODEL_WITHHELD. 입력 24,228 bytes, 검색·문맥·생성·검증 전체 약 1.951초.
- 최소 원문 선택: SELECTED, F1·F2·F3(한도·정의·추가한도) 선택. 입력 6,355 bytes, 모델 호출 약 0.656초. 검색은 약 0.002초 수준이며 전체 전처리/색인 시간을 포함한 지연 비교가 아니다.
- BM25 CAP 순위는 새 6개 인덱스에서 2위. 문맥 6개를 모두 연결했다. 선택 원문과 재표시 문장의 금액·소득·나이·장애 예외·부정 표현은 일치하고 존재하는 근거만 표시했다. 법적 적용/자격 확정은 하지 않았다.
- 첫 두 시도는 한도만 선택하거나 추가한도를 정의로 잘못 선택하여 HOLD였다. 이를 보존하고 짧은 인용 ID와 한도·정의 우선 배치 후 다시 측정했다. 한 사례로 개발했으므로 독립 성능이나 통계적 개선을 주장하지 않는다.
- 두 방식은 자유 생성과 원문 선택이라는 서로 다른 과제다. 새 결과 1건의 원문 보존 성공을 자연어 설명 정확도 향상률·운영 승인으로 바꾸어 보고하지 않는다. 수치 의미 구조화와 읽기 쉬운 자연어 설명은 아직 남은 작업이다.

새 자료는 동일 원본·설정에서 같은 선택 해시를 만들며 기존 파일은 다른 경우 덮어쓰지 않는다. 새 평가 인덱스만 생성하고 기존 33개 문서는 전체 내용 해시까지 검증했다. 승인 회수·운영 색인 정책은 기존 v3 그대로다. UnavailableRetriever와 RAG_NOT_READY를 유지한다.

## 현재 구현: 로컬 평가 RAG 연결 및 승인 준비 (2026-11-12)

`run_rag_evaluation.py`에서 기존 quality-v2 인덱스 검색 → 지원 기능 확인 → v3 초안이 연결한 필수 영역을 ES _mget으로 조회 → 기존 코퍼스/공식 스냅샷·조건·영역 해시 대조 → Evidence/Source 묶음 → 실제 ChatOllama gemma3:4b 호출을 구현했다. **운영 API 활성화와 안전한 법령 답변 품질 통과는 별개**다. 실제 독립 생성 3건은 모두 수치 검사로 보류됐다. UnavailableRetriever/503 RAG_NOT_READY·실제 승인 자료 0건을 유지한다.

### 파일과 경계

- `app/rag/evidence_bundles.py`: 기존 Evidence·Source를 재사용한 내부 EvidenceBundle. 공개 DTO·승인 게이트를 바꾸지 않는다. 조·항 위치, 조건, 공식 URL/조회일/스냅샷 해시/버전, 부칙·예외 역할과 requiredRegionIds를 보존한다.
- `app/rag/evaluation_rag.py`: EVALUATION_ONLY 전용 검색/원자적 조립/프롬프트/출력 검사. 미승인 초안은 법적 완전성 검증이 아니다. 필수 근거가 검색 순위 밖이면 해당 묶음이 참조하는 선정 문서만 _mget으로 읽고 원문과 대조한다. 필수 RULE의 검색 앵커가 없으면 생성하지 않는다. 여러 공제가 섞인 질문은 별도 묶음 분리가 필요해 보류한다.
- `scripts/run_rag_evaluation.py`: 실제 모델 또는 --no-model 준비 검사를 수행하고 질문·판별·검색 순위·전달 근거·출처·원시 출력·보류 사유를 별도 결과 파일에 저장한다. Mock 답변을 실제 출력으로 제공하는 옵션은 없다.
- `scripts/evaluate_independent_rag.py`, `tests/fixtures/independent_rag_questions.json`: 새 24문항을 검색 실행 전에 고정했다. 질문 집합은 검색 결과나 순위에 맞춰 수정하지 않았다. 독립 평가 중 검색 알고리즘도 보정하지 않았다.

실제 평가 자료를 운영 GenerationService.generate에 직접 전달하면 RAG_NOT_READY로 거부한다. 평가만 별도 generate_prompt 경계를 사용하며 모델 슬롯/대기/오류 처리는 기존 구현을 재사용한다. 실제 운영 Retriver는 등록하지 않았다. 향후 bundle_from_approved_context는 최신 원장으로 기존 approve_chunk를 재실행하는 콜백의 결과가 동일한 경우에만 approved-context-v3를 변환한다. 평가 묶음·회수·변경·귀속연도 불일치는 거부하며 이번에는 Mock 검증만 수행했다.

### 출처 제한과 컨텍스트 보존

제한 위치는 기존 GenerationService.retrieve의 [:10]과 ChatResponse/Recommendation.sources 최대 10개다. [:10]을 제거하고 10개를 넘거나 필수 묶음이 연도/승인 필터로 불완전해지면 전체를 보류한다. 기존 응답 DTO는 그대로다. 향후 운영 경로의 내부 Evidence 수도 보수적으로 10개 이내이며 초과 묶음은 잘라서 반환하지 않는다.

평가에서는 내부 영역 수와 중복 제거한 표시 Source 수를 별도로 센다. 같은 Source에 여러 필수 영역이 있는 경우 내부 근거가 10개를 넘어도 표시 Source가 10개 이내이면 모두 보존할 수 있다. 다른 Source가 11개면 묶음 전체를 보류한다. 모델에 보낼 본문은 수정/요약/절단하지 않는다. 반복되는 조건 문구는 본문 내 정확한 시작·끝 범위로 연결하여 중복 메타데이터만 압축하며 전체 조건 원문은 결과의 modelEvidence에 남긴다.

평가 호출만 num_ctx=32768/num_predict=512를 명시한다. 시스템+입력 UTF-8 바이트 수, 출력 여유 512, 템플릿 여유 512가 예산을 넘으면 CONTEXT_BUDGET_WHOLE_BUNDLE_HELD다. 최종 실제 세 묶음 입력은 약 20,247/24,155/24,401바이트였다. 이는 토크나이저 의존성을 추가하지 않는 보수적 입력 예산이며 실제 prompt_eval_count·정밀 토큰 계수·서버 템플릿 길이는 미측정이다. 한도 검사를 서버의 모든 절단 동작 검증 완료로 보고하지 않는다.

### 프롬프트·모델 출력 검사

기존 Ollama 래퍼의 기본 generate(str)·환경변수·연결 설정은 유지하고, 선택적인 generate_grounded(SystemMessage, HumanMessage)와 평가용 컨텍스트/JSON schema 옵션을 추가했다. 시스템 지시와 미신뢰 질문·법령 JSON을 분리하며 외부 추적은 계속 비활성화한다. 실제 Calc 결과는 제공하지 않았다. 검색 문서의 지시를 실행하지 않으며 금액·공제율·귀속연도·개인 환급액을 생성하도록 허용하지 않는다. 메시지 분리만으로 프롬프트 인젝션 방어가 완성됐다고 보지 않는다.

평가 출력은 JSON 형식·실제 E 인용 ID와 본문 표시의 일치·미검증 숫자/한글 금액을 검사한다. Unicode 숫자도 거부한다. 실패하거나 모델 스스로 보류하면 answer=null이다. rawModelOutput은 평가 기록에서만 확인한다. 자동 검사는 인용 대상 존재/수치 위험을 확인할 뿐 문장과 근거의 의미 일치나 법적 정확성을 증명하지 않는다. 모든 답변에 answerUseAllowed=false를 유지하며 성공한 가상 Mock 답변도 실제 모델 품질로 집계하지 않는다.

실제 첫 출력은 코드블록/키 누락, 후속 출력은 수치·인용 부정합·한글/Unicode 숫자 위험을 보여 보류했다. 평가용 JSON 구조화 옵션을 적용했지만 수치 지시 불이행은 남았다. 원시 출력의 금액을 임의 삭제하거나 승인 정책을 완화해 통과시키지 않았다. 모델 스키마/프롬프트 변경 시도도 각 결과 경로에 별도로 보존했다. 구조화 출력 참고: https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx

### 실제 독립 평가 결과

고정 파일 SHA-256: `2446fa0161a6ba5dc4b4d1945b4cccd6faa4da19437adf70ac5e4ec258baa71e`. 총 24개(공제별 8개), 위치 채점 15개·미확정 6개·범위 밖 3개다. 기존 30문항과 다른 집합이므로 향상률로 비교하지 않는다.

- 검색: Recall@5=0.7333333333, MRR@10=0.5777777778. 월세 Recall 0.8/카드 0.4/청약 1.0.
- 범위: 기대 의도와 일치 20/24=83.33%. 범위 밖 3개는 모두 차단. IR-04(방값), IC-01(체크로), IC-02(영수증 받은 현금), IC-05(교통비)를 잘못 보류했다. 이번 단계에서 규칙을 이 결과에 맞춰 바꾸지 않았다.
- 생성: 미리 지정한 IR-01/IC-03/IH-01의 실제 ES+Gemma 호출 3개, 사용자에게 표시할 답변 통과 0개. 모두 UNVERIFIED_NUMERIC_CLAIM. 원시 출력은 적용시기·금액을 단정하거나 질문과 다른 설명을 포함해 의미 검수도 필요하다. 테스트 성공은 네트워크/문맥/차단 경계 성공이며 답변 품질 통과가 아니다.
- 혼합 IC-08은 묶음을 임의 병합하지 않고 MULTI_TOPIC_REQUIRES_SEPARATE_BUNDLES로 보류한다. 다른 미확정 질문도 법적 정답을 지정하지 않는다.

최종 결과: `data/processed/independent-rag-evaluations/8c106eaeb67977a9b8f5cd66c460c7b0c3d05605a2692c280df93aa6f7baf192/evaluation.json`.
같은 폴더의 manual-review.json에 세 원시 출력의 수치 단정·질문 이탈·납입 한도 혼동 의심을 별도로 기록했다. 이는 전문가 법적 승인이나 정량 의미 점수가 아니다.

```powershell
python scripts/run_rag_evaluation.py --question "월세 공제에서 확인할 조건은?" --no-model
python scripts/run_rag_evaluation.py --question "월세 공제에서 확인할 조건은?"
python scripts/evaluate_independent_rag.py --generate-ids IR-01 IC-03 IH-01
```

이 CLI는 합성 질문·테스트 데이터용이며 실제 개인정보·개인 세액을 평가 파일로 저장하지 않는다. 실제 모델은 로컬 Ollama만 허용한다. 모델/ES 실패 시 다른 인덱스·외부 모델·Mock 답변으로 전환하지 않는다.

### 법령 3건 승인 준비

기존 공식 발췌 16개·추가 청크 53개·v3 초안 3건은 그대로다. 새 자료는 `data/processed/evidence/2026-11-12-approval-preparation/`에만 저장했다. acquisition.json에 공식 URL·조회일·실제 버전·해시·대조 결과가 있고 approval-preparation.json에 세 대상의 정확한 proposedRegionIds/조건/보류 사유가 있다. 실제 원장에는 반영하지 않았다.

국가법령정보센터의 소득세법 시행령 제106조 본문을 확보해 기존 PDF와 비공백 문자 일치를 확인했다. 제107조 링크는 제1항 정의 범위만 제공하므로 기존 전체 조문과 불일치는 범위 차이를 포함한다. 두 자료는 대통령령 제36737호/2026-10-01 시행 버전이다. 현재 버전 확보를 2026년 연초 적용 검증으로 승격하지 않는다. 제106조 초기 UI 포함 추출은 별도 검토 기록으로 남기고 법령 증거에서는 제외했다.

- rent-2026-spouse-cap: 법률 1월 지급 적용례와 시행령 2월 요건 연결, 외부 정의·주택 범위 검토 필요.
- card-2026-child-limit: 제106조 원문 대응은 추가 확인. 제107조의 나머지 범위·외부 정의/증빙·연초 적용은 검토 필요.
- housing-2026-payment: 배우자 확대의 종전 부칙, 합산 한도 참조, 해지/전환 예외와 서식 확인 필요. 이자 비과세는 독립 승인 대상에서 제외.

세 묶음은 기존 필수 영역을 갖춘 검토 후보로만 유지하며 즉시 운영 승인 가능한 묶음은 0개다. 검토자가 미해결 사항을 해소하고 해당 영역·공식 증거·조건을 확인한 후 별도 승인을 받아 새 v3 이력을 작성해야 한다. 기존 VERIFIED/APPROVED를 자동 기록하지 않았다. 운영·Spring/React 연결은 그 이후 별도 단계다.

## 기준선: 검색 품질 개선과 출처 분리 (2026-11-12)

기존 scope.json의 33개 ID·내용·버전은 그대로 사용한다. 범위 재선정·PDF 재전처리·법령 승인·상담 API 연결은 하지 않았다. 기존 baseline 인덱스는 보존하고 같은 33개에 파생 검색 메타데이터를 추가한 `hope-rag-eval-73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642-quality-v2`를 사용한다. 운영 인덱스·v3 승인 조건·AGENTS.md는 변경하지 않는다.

### 최소 구현 선택과 한계

명시적인 기능·질문 목적·지원하지 않는 업무 패턴을 조합하는 규칙 분류를 scope.classify_question에 추가했다. 카드/월세/주택 단어 하나만으로 허용하지 않는다. 집세·집주인에게 보낸 돈·무주택확인서 등 표현도 처리한다. 사업 필요경비·법인카드 매입세액·임대사업자 양도세·카드 발급 등은 OUT_OF_SCOPE다. 기능/목적이 불명확하거나 부정/대조가 섞인 질문은 INSUFFICIENT_EVIDENCE로 보류한다. 거부/보류 시 Elasticsearch를 호출하지 않는다.

검색 점수 단독 판정이나 LLM 분류는 사용하지 않았다. 허용된 질문도 주제 필터·출처 종류 필터를 적용하고 서버 응답의 주제·출처·평가 상태·내용 해시를 다시 검사한다. 검색 결과가 없으면 INSUFFICIENT_EVIDENCE다. 모든 성공 결과도 RETRIEVED_UNVERIFIED/answerUseAllowed=false이며 법적 사용 가능성을 확정하지 않는다. 규칙은 완전한 의미 이해가 아니며 새 표현·다중 의도·복잡한 부정 표현에서 오탐/보류가 남을 수 있다. 점수 임계값만으로 적절한 법적 근거임을 보증하지 않는다.

### 카드 한도 진단과 일반화 가능한 가중치

CARD-05 원문은 ‘자녀 수에 따른 카드 공제한도 규정은?’이다. 기존 1위 개정 요약은 731자/19.972607점, 목표 본문 대표 청크는 609자/6.320615점으로 7위였다. 실제 _analyze 결과 standard는 공제한도를 한 토큰으로, ngram은 공제/공제한/제한/제한도/한도로 나눴다. _explain에서 두 대표 필드 길이는 약 472/440, 평균 1253.9395였다. 따라서 이번 실패를 긴 조문에 의한 점수 희석만으로 설명할 수 없다. 짧은 공통 시행일의 일반 어휘 일치, 요약의 직접적인 질문 어휘, 공제명/조문 제목 부재가 함께 경쟁했다.

검색 필드에 동일 조문 형제 청크에서 확인한 articleTitle, 명시적 기능별 검색 동의어 featureNames를 추가했다. 원문은 수정하지 않는다. weighted 필드는 content, content.ko, articleTitle.ko^2, featureNames^0.5, article^4다. 한도→법률 본문, 정의→시행령, 증빙→시행규칙을 일반적 선호로 +3 가중한다. 적용시기 질문은 부칙 +2, 그 외에는 공통 부칙 점수에 0.25를 곱한다. 부칙 자체를 삭제하지 않는다. 특정 정답 조문 번호·청크 ID·질문 ID를 검색 점수에 사용하지 않는다. 모든 값과 출처 필터는 QUALITY_POLICY 및 평가 결과의 retrievalConfiguration에 기록한다.

### 출처와 버전 경계

33개를 LAW_BODY 11, DECREE_BODY 10, RULE_BODY 3, SUPPLEMENT 3, AMENDMENT_TEXT 1, AMENDMENT_SUMMARY 5로 구분한다. textRole·기존 검수 영역의 APPLICATION 역할·문서 종류를 이용하며 적용연도나 시행일을 추정하지 않는다.

- body: 법률·시행령·시행규칙 본문만
- context: 본문+필수 부칙 (기본 평가 경로)
- comparison: 개정문·개정 요약만, 비교 검토용이며 본문 대체 금지

본문/context 결과에 비교자료가 들어오면 오류로 차단한다. 원문/출처/문서 해시/공식 근거 버전/시행일·검증 상태는 보존한다. 버전이 다른 출처는 variants로 분리하며 자동으로 최신·현행을 결정하지 않는다. 파일 documentVersion 해시 차이와 공식 법령 버전 충돌은 별개 신호로 기록한다. 공식 버전 정보가 없으면 법령 버전 충돌 여부도 완전히 확인할 수 없다. 적용연도 null/applicabilityVerified=false를 유지한다.

### 같은 30문항·정답 기준으로 수행한 실제 비교

기존 질문·정답 해시 `3bad822d938a2e7799511fedfc25f3523defe11fa8bc04419b3ad4f01e2c3cc0`을 고정했다. 미확정 4개는 계속 제외하고 원문 위치를 확인한 23개 조문 그룹으로 채점했다. 이는 법적 정확성 평가가 아니다.

| 비교 | Recall@5 | MRR@10 |
|---|---:|---:|
| 기존 쿼리 재현 | 0.956522 | 0.559834 |
| 가중치만 변경 | 1.000000 | 0.646377 |
| 범위 판별·주제 필터만 | 1.000000 | 0.613768 |
| 개선+본문만 | 0.956522 | 0.891304 |
| 개선+본문/부칙 | 1.000000 | 0.934783 |
| 비교자료만 | 0 | 0 |

비교자료만 검색한 0점은 기존 정답이 본문·부칙 위치이기 때문이며 비교자료 자체의 별도 관련성 정답을 만든 것이 아니다. 이 경로를 본문 질의의 대체 검색으로 사용하지 않는다. 본문만 검색하면 RENT-08의 부칙 정답을 놓친다. context는 기존 성공 문항의 Top5 실패·순위 하락이 없고 23개 채점 문항의 잘못된 차단도 없었다. 공제별 Recall은 모두 1.0, MRR은 월세 1.0/카드 0.9375/청약 0.875다. 카드 한도 목표는 7위→1위다.

범위 밖 3개는 모두 OUT_OF_SCOPE/검색 미호출로 결과 노출 3→0이다. 미확정 CARD-09는 공제명을 주지 않은 ‘개정 자녀 정의’ 질문이므로 보류하며 평가 데이터의 CARD 태그를 분류기에 주입하지 않았다. 다른 미확정 3개는 미검증 문서를 검색할 수 있지만 정답/적용시기를 확정하거나 답변 생성에 사용하지 않는다. context의 개정 비교자료 노출은 30→0이며 파일 해시가 다른 버전 후보는 계속 보존한다.

첫 구현에서 전통시장/대중교통 질문의 ‘규정’ 표현과 ‘무주택확인서’ 질문을 잘못 보류하는 회귀를 발견했다. 일반 목적 어휘/기능 표현을 보완한 최종 버전에서 해결했으며 초도 결과 파일도 덮어쓰지 않았다. 고정 30문항은 개발에 사용한 소규모 평가 세트라 일반화를 입증하지 않는다. 별도의 미사용 질문·전문가 관련성 라벨 평가가 다음 단계에서 필요하다.

최종 결과: `data/processed/bm25-evaluations/930574a69c8e2736286e990897c493215a8cdd1afbb254fc0cee8b33ef80e254/evaluation.json`.
품질 인덱스 검증: `data/processed/evaluation-index-reports/c33d69dc1960b046f6ff8621079d69647219798c0cc1c6f97c19742cea20e1e4/index-report.json`.

chatbot/에서 다음 명령으로 새 프로필을 적재/검증하고 비교한다. 기존 인덱스를 삭제하거나 덮어쓰지 않는다.

```powershell
python scripts/index_evaluation_chunks.py --selection data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json --profile quality-v2 --reuse
python scripts/evaluate_bm25.py --selection data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json --compare-to data/processed/bm25-evaluations/88f22ae215458416dd38d2e193e14521d57e42e9068e71d8d4f845340bc274ce/evaluation.json
```

### 다음 단계의 최소 RAG 연결 계약 (미구현)

기존 ChatRequest(message/questionType/taxYear/taxResult/history) → 지원 범위/문맥 확인 → 운영 v3 승인 출력 검색 → 최신 승인 원장·적용연도·법령 버전·필수 영역/조건 검사 → 기존 Evidence(content, Source) → GenerationService.generate → ChatResponse 흐름을 재사용한다. 평가용 EvaluationStore는 주입하지 않는다. 승인 회수·미확인 버전·미해결 조건·필수 문맥 누락은 답변 보류 사유다.

필수 문맥 묶음은 문서별 출처를 유지한 여러 Evidence로 구성해야 한다. 현재 retrieve의 [:10] 및 sources 최대 10개가 필수 묶음을 잘라내지 않도록 다음 승인 단계에서 원자적으로 제한/보류하는 보완이 필요하다. LLM에는 Backend/Calc의 저장된 금액만 제공하며 새 세액·환급액을 계산하지 않도록 기존 역할을 유지한다. 실제 운영 승인 자료 0건·UnavailableRetriever·503 RAG_NOT_READY는 그대로다.

## 기준선: 서비스 범위 선정과 격리된 BM25 평가 (2026-11-11)

이번 명시적 승인 범위에서만 미승인 자료를 평가 CLI에 사용한다. AGENTS.md 변경 제안은 사용자가 거절하여 수정하지 않았다. 운영 검색·법령 적용 승인 조건은 그대로이며 FastAPI의 UnavailableRetriever/RAG_NOT_READY를 유지한다. 아래 기능은 운영 검색기를 구현한 것이 아니다.

- `app/rag/scope.py`: 문서명+본문 조문, 근로소득 개정 항목명, 기존 v3 초안의 원본 영역/해시 연결을 사용한다. 단순 키워드로 전체 법령을 포함하지 않는다. 두 코퍼스의 manifest·원본 해시를 기존 load_corpus로 확인한다.
- 초기 3,186개 중 33개 선정/3,153개 제외. 기존 본문 14개+개정 요약 5개+추가 공식 발췌 코퍼스 14개다. CARD 14, RENT 10, HOUSING_SAVING 12는 중복 소속을 포함하며 합계가 33보다 크다. 공통 법률 시행일 1개는 세 기능, 시행령 시행일 1개는 월세/카드가 공유한다.
- 확대 후보는 67개로 구분해 저장하지만 색인 CLI가 expanded를 차단한다. 안내서와 사업·종교인·연금소득 구역의 반복 개정 항목은 초기 후보에 포함하지 않는다.
- sourceUrl=null인 원본 값을 임의로 채우지 않는다. 추가 자료 14개에는 실제 v3 공식 증거 URL·버전·조회일·스냅샷 해시 연결을 별도 officialEvidenceLinks로 보존한다. 로컬 HTML 변환 PDF는 공식 배포 PDF와 구분한다.
- 원본 청크 전체를 평가 입력으로 보존하므로 청약 조문의 이자 비과세·개정문 인접 내용도 남아 있다. 선정은 해당 청크 전체의 서비스 지원/법적 승인을 뜻하지 않는다. 필요한 영역·예외·부칙의 법적 완전성은 미검증이며 기존 초안 unresolvedIssues를 함께 남긴다.
- 중복 그룹 8개를 조문 단위로 묶되 출처·버전·다른 하위 청크는 variants로 보존한다. 서로 다른 법문을 하나의 연속 원문으로 합치지 않는다. 운영용 근거 사용 규칙으로 자동 승격하지 않는다.

### 평가 Elasticsearch와 실행

실제로 확인한 로컬 서버는 Elasticsearch 7.10.1(zip)이다. 샌드박스 안에서는 접속 시간이 초과됐으나 승인된 외부 실행에서 연결했다. 서버 설치·설정 변경은 하지 않았다. PATH에서 elasticsearch/docker 명령은 발견하지 못했지만 실행 중인 서버는 별도로 존재했다.

신규 의존성 없이 기존 httpx 0.28.1로 REST API를 호출한다. 7.10+/8/9의 사용 API 범위를 대상으로 구현했으며 실제 검증은 7.10.1, 8/9는 Mock 계약 검사다. BM25 기본값과 standard+2~3글자 ngram 필드를 사용하며 Nori 등 플러그인은 설치하지 않는다. 버전별 공식 REST 문서를 참고했다:

- https://www.elastic.co/guide/en/elasticsearch/reference/7.10/docs-bulk.html
- https://www.elastic.co/guide/en/elasticsearch/reference/7.10/analysis-ngram-tokenizer.html
- https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity

접속 설정은 **평가 전용** `RAG_EVAL_ES_URL`(기본 http://127.0.0.1:9200)이며 loopback 기본 URL만 허용한다. 인증정보 포함 URL·외부 주소·인덱스 경로·리다이렉트·환경 프록시를 거부한다. 현재 인증이 필요한 ES 구성은 지원하지 않으며 무단 보안 설정 변경으로 우회하지 않는다. 운영 접속 설정은 만들지 않는다.

인덱스 이름은 `hope-rag-eval-<selectionHash>`로 고정한다. 지정 이름 외 데이터 경로를 차단하며 운영/다른 환경으로 전환하지 않는다. 생성 시 bulk create, refresh=wait_for, 전체 _source/ID/건수/매핑/선정 해시 대조를 수행한다. 기존 이름은 기본 거부하고 --reuse는 검증 후 읽기 전용 재사용한다. 삭제·덮어쓰기 기능은 없다. 새 선정 버전은 새 인덱스로 분리한다. 초기 시험 인덱스 `hope-rag-eval-0f34218a...`도 33개 평가 자료만 포함하며 최종 인덱스와 별도로 보존했다.

현재 최종 선정 파일:
`data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json`

확대 선정 파일(색인하지 않음):
`data/processed/scopes/5df071cdace2ed4a3789960caf8036631c44deba3b6fd00441a775184ccdb427/scope.json`

chatbot/에서 실행한다. Python 실행 파일은 로컬 가상환경을 사용한다.

```powershell
python scripts/build_scope_candidates.py --corpus data/processed/8417ec42dc78a0194dbc5edc18dd8aa68ed1f5fd1566f0e5326e57ade0b612f3 app/data/raw --corpus data/processed/evidence/2026-11-11-core3-v3/processed/d76986490b3e0271582f16d2d11bd1169f515cdcf952de7377fe338f4a58fc45 data/processed/evidence/2026-11-11-core3-v3/inputs --ledger data/processed/evidence/2026-11-11-core3-v3/review-ledger-draft.jsonl
python scripts/index_evaluation_chunks.py --selection data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json --reuse
python scripts/evaluate_bm25.py --selection data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json
```

새 승인 규칙이나 프레임워크를 추가하지 않고 기존 v3 승인 내보내기와 분리했다. `reject_operational_input`은 원본/평가 자료의 운영 입력을 거부하며 운영 색인 자체도 미구현으로 차단한다. 실제 운영 연결 시 최신 승인 원장 재검사·승인 회수 반영이 별도로 필요하다.

### 실제 평가와 한계

대표 질문은 공제별 10개, 총 30개이며 scripts/evaluate_bm25.py의 QUESTIONS에 있다. 원문에 실제 조문·앵커가 있는 경우에만 TEXT_LOCATOR로 정답 그룹을 만든다. 이는 검색 위치 정답이며 법적 정답이나 전문가 관련성 라벨이 아니다. 전체 원문 숫자·적용 조건을 승인했다는 의미가 없다. 문서의 검증 상태는 UNVERIFIED, 귀속연도 null/false를 유지한다.

최종 실제 결과:
`data/processed/bm25-evaluations/88f22ae215458416dd38d2e193e14521d57e42e9068e71d8d4f845340bc274ce/evaluation.json`

- 점수 산정 23문항: Recall@5=0.9565217391, MRR@10=0.5598343685. 지표 단위는 중복 제거 조문 그룹이다. 관련 순위와 출처·버전·점수·다른 버전 variants를 질문별 기록했다.
- 월세 7문항 1.0/0.547619, 카드 8문항 0.875/0.580357, 청약 8문항 1.0/0.55(Recall/MRR).
- 미확정 4개: RENT-07의 신청·증빙 앵커 위치, RENT-09/CARD-09/HOUSING_SAVING-09의 적용시기 질문. 임의 정답이나 0점으로 채우지 않았다.
- 범위 밖 3개는 점수에서 제외하며 3개 모두 유사 문서를 노출했다. 현재 검색기는 질문 범위 판별기가 아니며 API에 연결하면 안 된다.
- CARD-05 자녀 수별 카드 한도는 목표 조문 7위로 Top5 실패다. 개정 요약·용어 중복과 다른 공제의 자녀 조건이 경쟁한다.
- 30개 모두 상위 결과에 종전/개정 혼합 요약 또는 버전 차이가 있었다. 위험 플래그이며 자동 법적 불일치 판정이 아니다. otherTopicResults도 주제 태그 기반의 교차 주제 신호이지 수동 관련성 판정은 아니다.
- 향후 조문 직접 질의 우대·주제 범위 판별·요약/본문 분리 평가 및 별도 검토용 질문 세트를 우선한다. 검색 점수 개선만으로 2026 적용을 승인하지 않는다.

운영 승인 자료는 여전히 0건이며 실제 사용자 생성·저장과 연결하지 않았다.

## 2026-11-11 승인 게이트 v3

`review-policy-v3`는 법령 원문 영역과 필수 문맥 묶음을 독립 승인/회수한다.
`legalConditions` 원문을 보존하고 `unresolvedIssues` 및 기존 미분류 conditions는 차단한다.
공식 근거의 영역/버전/발췌 해시를 대조하며 원본/기존 v2 원장은 변경하지 않는다.
운영 출력은 `approved-context-v3`의 regions 배열로 분리되며 API DTO에는 영향을 주지 않는다.
개정 요약 비교표와 2025 안내서는 v3 운영 승인을 계속 보류한다. 실제 승인 자료 0건이다.
세부 계약과 한계는 `decisions/2026-11-11_승인게이트보완.md`를 따른다.

## 2026-11-11 검수 및 검색 승인 도구

`quality_checks.py`, `review_models.py`, `review_queue.py`, `approval_gate.py` 및 오프라인 CLI를 추가했다.
기존 3,133개 청크는 변경하지 않는다. 구조 검증·법령 적용·사용 승인을 독립 원장으로 관리하며
자동 검사/키워드 후보/표본 선택은 법적 적용이나 운영 사용을 승인하지 않는다.
실제 결과는 P0 154/P1 103/P2 79/P3 2,797, 표본 180, 개정 검수 묶음 35개다.
공식 비교문 미제공으로 공식 비교는 NOT_PERFORMED이고 모든 원장은 HOLD다. 실제 승인 내보내기는 0개다.
정책·실행 경로·조건부 적용·종전/개정 부분 선택 제한은
`decisions/2026-11-11_청크검수및검색승인.md`에 기록했다. 실제 Elasticsearch 및 API 연결은 하지 않았다.

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
## 2026-11-12 차단 원인 대조와 최소 수정

기존 세 사례의 실제 프롬프트를 재구성하여 저장된 promptHash와 3/3 일치함을 확인했다. `data/processed/rag-diagnostics/2026-11-12-blocking-analysis/`의 reconstructed-inputs.json과 case-analysis.json에 당시 원문·지시문·출력·문장별 대조를 보존한다. 아래 수치는 과거 오류 분석이며 현행 세법 안내가 아니다.

| 사례 | 실제 오류 표현 | 전달된 근거와의 차이 | 분류 |
|---|---|---|---|
| 월세 | 합계 1천만원을 초과하지 않아야 혜택, E2 인용 | E2에 합산한도가 없고 E1②는 초과액을 배우자 금액에서 차감한다 | A 잘못된 단순화·인용 |
| 월세 | 2026년 1월 1일 적용을 E5로 설명 | E5는 시행령 시행일이고 법률 시행 및 지급 적용례는 E3·E4에 따로 있다 | A·D |
| 카드 | 각각 40%, 연간 250만원 한도, E2·E3 인용 | E2⑩에 급여·자녀별 한도가 이미 있고 E3⑱는 자녀 정의다. 25는 총급여 비율이라는 단위도 누락했다 | A·D |
| 청약 | 300만원 한도로 납입 가능 | E1②는 소득공제 대상 납입액 한도이며 통장 납입한도가 아니다 | A |
| 청약 | 주택 당첨 등 정하는 사유로 중도해지하면 제외 | E1의 ‘외의 사유로’를 누락하여 예외를 뒤집었다 | A |
| 청약 | 2026년 9월 18일 시행을 E3로 인용 | E3은 과거 개정일 목록이며 문서 버전일은 개별 규정 적용시기가 아니다 | A·D |

카드 법률 제126조의2⑩과 시행령 제121조의2⑱는 이미 전체 입력에 있었다. 핵심 한도 검색 누락으로 분류하지 않는다. 외부 참조 정의의 완결성(C), 적용시점 검증(D)은 별도로 남는다. 기존 세 건에서 금액 표현 동등성에 의한 검증기 오탐(B)은 확인되지 않았다. 원문에 숫자가 존재해도 미승인 정성 평가의 숫자 사용 승인은 아니다.

새 재생성에서 정상 그룹 인용을 단일 인용 정규식이 놓치는 B 사례를 확인했다. 그룹 표기만 개별 ID 집합으로 해석하고 인용 배열과 본문 집합 일치·존재 여부 및 수치·날짜 제한은 유지한다. unknown ID·범위·누락을 보정하지 않는다. grouped-citation-regression.json에 동일 원시 출력의 전후 판정을 저장했다. 모델 자체 보류이므로 최종 MODEL_WITHHELD, answer=null이며 승인되지 않는다.

방값·체크로·영수증 받은 현금·교통비의 제한적 검색 정규화는 공제 자격 확정과 분리한다. 숙박·출장 등 범위 밖 목적과 혼합 공제 보류는 유지한다. 질문 중심 힌트는 개념 중첩으로 계산하며 정답 ID나 답변 문구를 넣지 않고 모든 필수 문맥을 전달한다.

같은 24문항은 DEVELOPMENT_REGRESSION으로 표시한다. 범위 20/24→24/24, Recall@5 73.33%→100%, MRR@10 0.5778→0.7778이나 일반화 성능은 미검증이다. 최종 실모델은 월세 인용 누락·수치, 카드 자체 보류, 청약 인용 집합 불일치·급여와 납입액 혼동으로 0/3 통과했다. 자동 진단은 의미적 정확성을 입증하지 않는다. 운영 연결 전 필수 정의·적용시점·직접 답변 및 예외 보존 검증이 필요하다.
