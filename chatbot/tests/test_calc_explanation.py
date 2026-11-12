"""Calc 결과 fixture와 로컬 계산 규칙 기반 설명을 검증한다."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.recommendation import RecommendationRequest
from app.services.calc_rules import CalcRuleCatalog
from app.services.generation import GenerationService
from app.services.recommendation_service import RecommendationService
from app.services.tax_result_service import TaxResultService

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "member_additional_payment.json",
        "member_refund.json",
        "member_sme_reduction.json",
        "member_unapplied_deduction.json",
    ],
)
def test_spring_chat_request_fixtures_match_contract(fixture_name):
    payload = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
    request = ChatRequest.model_validate(payload)

    assert request.question_type == "TAX_RESULT"
    assert request.tax_result is not None
    assert request.tax_result.details
    result = request.tax_result
    assert result.expected_refund == result.withheld_tax - result.decided_tax
    assert result.inputs is not None
    if any(
        d.type_code == "SME_YOUTH" and d.deduction_amount > 0 for d in result.details
    ):
        assert result.inputs.sme_reduction_yn == "Y"


def test_calc_rule_document_is_valid_and_has_expected_rules():
    catalog = CalcRuleCatalog.load()

    assert (
        catalog.get_for_detail(
            ChatRequest.model_validate(
                json.loads(
                    (FIXTURE_DIR / "member_unapplied_deduction.json").read_text(
                        encoding="utf-8"
                    )
                )
            ).tax_result.details[2]
        ).code
        == "RENT"
    )


def test_rule_sentence_selection_preserves_calculation_order():
    rule = CalcRuleCatalog.load().get("SME_YOUTH")
    assert TaxResultService._is_grounded_explanation(
        " ".join(rule.description_steps), rule
    )
    assert not TaxResultService._is_grounded_explanation(
        " ".join(reversed(rule.description_steps)), rule
    )
    assert not TaxResultService._is_grounded_explanation(
        rule.description_steps[0] + " " + rule.description_steps[0], rule
    )


def recommendation_request(name):
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return RecommendationRequest.model_validate(
        {"taxYear": payload["taxYear"], "taxResult": payload["taxResult"]}
    )


@pytest.mark.parametrize(
    "fixture_name,amount,first_code",
    [
        (
            "member_additional_payment.json",
            "추가 납부액은 117,000원",
            "PENSION",
        ),
        ("member_refund.json", "환급액은 450,000원", None),
        ("member_sme_reduction.json", "환급액은 800,000원", "PENSION"),
        ("member_unapplied_deduction.json", "환급액은 80,000원", "RENT"),
    ],
)
def test_initial_message_for_each_member(fixture_name, amount, first_code):
    request = recommendation_request(fixture_name)
    retriever = Mock(search=AsyncMock(side_effect=AssertionError("RAG 사용 금지")))
    model = Mock(return_value=None)
    model.generate.return_value = "추가로 999999원을 절세할 수 있습니다."
    service = RecommendationService(GenerationService(retriever, model))
    candidates = service._candidates(request.tax_result)
    assert (candidates[0].code if candidates else None) == first_code

    response = asyncio.run(service.respond(request))

    assert response.status == "ANSWERED"
    assert len(response.recommendations) == 1
    message = response.recommendations[0]
    assert amount in message.content
    assert "999999" not in message.content
    assert "계산 기준액은 원래 입력 전체를 뜻하지 않습니다" in message.content
    assert message.type_code is None
    assert message.sources == []
    assert len(candidates) <= 3
    assert not any(item.code == "NATIONAL_PENSION" for item in candidates)
    assert not any(item.code == "SME_YOUTH" for item in candidates)
    for candidate in candidates:
        assert candidate.fact in message.content
    if first_code == "RENT":
        assert "실제 적용액 0원" in message.content
        assert "원인은 현재 결과만으로 확정할 수 없습니다" in message.content
    retriever.search.assert_not_called()
    model.generate.assert_called_once()


def test_initial_message_limits_candidates_and_ignores_duplicate_adjustments():
    request = recommendation_request("member_refund.json")
    other = recommendation_request("member_sme_reduction.json")
    zero = recommendation_request("member_unapplied_deduction.json")
    request.tax_result.details += other.tax_result.details + zero.tax_result.details
    request.tax_result.inputs.monthly_rent = 500000
    request.tax_result.inputs.housing_saving = 1200000
    request.tax_result.inputs.health_insurance = 600000
    service = RecommendationService(GenerationService(Mock(), Mock()))
    candidates = service._candidates(request.tax_result)
    assert len(candidates) == 3
    assert candidates[0].code == "RENT"
    assert len({item.code for item in candidates}) == 3


@pytest.mark.parametrize(
    "raw", ["{}", "[]", "null", '{"explanations":["부적격이라 공제가 없습니다"]}']
)
def test_initial_message_rejects_unsupported_model_explanations(raw):
    request = recommendation_request("member_unapplied_deduction.json")
    model = Mock()
    model.generate.return_value = raw
    service = RecommendationService(GenerationService(Mock(), model))
    response = asyncio.run(service.respond(request))
    assert "부적격이라" not in response.recommendations[0].content
    assert "확정할 수 없습니다" in response.recommendations[0].content


@pytest.mark.parametrize("fenced", [False, True])
def test_initial_message_accepts_verified_model_sentence_selection(fenced):
    request = recommendation_request("member_unapplied_deduction.json")
    model = Mock()
    service = RecommendationService(GenerationService(Mock(), model))
    candidates = service._candidates(request.tax_result)
    selected = [item.options[1] for item in candidates]
    model.generate.return_value = json.dumps({"explanations": selected})
    if fenced:
        model.generate.return_value = (
            "```json\n" + model.generate.return_value + "\n```"
        )
    response = asyncio.run(service.respond(request))
    for sentence in selected:
        assert sentence in response.recommendations[0].content


def test_initial_message_requests_missing_information_without_suggesting_absent_items():
    request = recommendation_request("member_refund.json")
    request.tax_result.details = []
    request.tax_result.inputs = None
    model = Mock()
    model.generate.return_value = '{"explanations": []}'
    service = RecommendationService(GenerationService(Mock(), model))
    response = asyncio.run(service.respond(request))
    content = response.recommendations[0].content
    assert "입력값과 공제·감면 상세 결과를 확인" in content
    assert "월세" not in content
    assert "연금저축" not in content
    assert len(response.recommendations) == 1


def test_initial_message_does_not_treat_negative_card_adjustment_as_opportunity():
    request = recommendation_request("member_refund.json")
    detail = request.tax_result.details[0]
    request.tax_result.details = [
        detail.model_copy(
            update={
                "type_code": "CARD_ADJUSTMENT",
                "kind": "CARD_RULE",
                "base_amount": 500000,
                "deduction_amount": -100000,
            }
        )
    ]
    service = RecommendationService(GenerationService(Mock(), Mock()))
    assert not any(
        item.code == "CARD" for item in service._candidates(request.tax_result)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("monthlyRent", -1),
        ("pensionSaving", True),
        ("irpSaving", "0"),
        ("homelessHeadYn", "yes"),
    ],
)
def test_calc_inputs_are_strict(field, value):
    payload = json.loads(
        (FIXTURE_DIR / "member_refund.json").read_text(encoding="utf-8")
    )
    payload["taxResult"]["inputs"][field] = value
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


@pytest.mark.parametrize(
    "fixture_name,field",
    [
        ("member_refund.json", "pensionSaving"),
        ("member_refund.json", "nationalPension"),
        ("member_refund.json", "totalSalary"),
        ("member_unapplied_deduction.json", "monthlyRent"),
    ],
)
def test_calc_input_and_result_snapshot_mismatches_are_rejected(fixture_name, field):
    payload = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
    payload["taxResult"]["inputs"][field] += 1
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


def test_old_payload_remains_valid_and_unknown_inputs_are_not_zero():
    payload = json.loads(
        (FIXTURE_DIR / "member_refund.json").read_text(encoding="utf-8")
    )
    del payload["taxResult"]["inputs"]
    request = ChatRequest.model_validate(payload)
    service = RecommendationService(GenerationService(Mock(), Mock()))
    assert request.tax_result.inputs is None
    assert service._candidates(request.tax_result) == []
    payload["taxResult"]["inputs"] = {"pensionSaving": 0}
    request = ChatRequest.model_validate(payload)
    assert request.tax_result.inputs.irp_saving is None
    assert service._candidates(request.tax_result) == []


def test_entered_but_missing_detail_is_not_reported_as_zero_applied():
    request = recommendation_request("member_unapplied_deduction.json")
    request.tax_result.details = [
        d for d in request.tax_result.details if d.type_code != "RENT"
    ]
    service = RecommendationService(GenerationService(Mock(), Mock()))
    candidate = service._candidates(request.tax_result)[0]
    assert candidate.code == "RENT"
    assert "상세행이 없습니다" in candidate.fact
    assert "실제 적용액 0원" not in candidate.fact


def test_no_candidate_from_zero_spending_or_applied_pension():
    request = recommendation_request("member_refund.json")
    service = RecommendationService(GenerationService(Mock(), Mock()))
    assert service._candidates(request.tax_result) == []
    request.tax_result.inputs = request.tax_result.inputs.model_copy(
        update={"monthly_rent": 0, "housing_saving": 0}
    )
    assert service._candidates(request.tax_result) == []


def test_sme_request_without_applied_detail_requires_diagnosis_not_eligibility_claim():
    request = recommendation_request("member_sme_reduction.json")
    request.tax_result.details = [
        d for d in request.tax_result.details if d.type_code != "SME_YOUTH"
    ]
    service = RecommendationService(GenerationService(Mock(), Mock()))
    candidate = service._candidates(request.tax_result)[0]
    assert candidate.code == "SME_YOUTH"
    assert "신청 입력은 Y" in candidate.fact
    assert "진단 결과값" in candidate.options[0]
    assert "확정할 수 없습니다" in candidate.options[0]


def test_pension_planning_is_not_suggested_without_remaining_tax():
    request = recommendation_request("member_additional_payment.json")
    request.tax_result.decided_tax = 0
    service = RecommendationService(GenerationService(Mock(), Mock()))
    assert service._candidates(request.tax_result) == []
