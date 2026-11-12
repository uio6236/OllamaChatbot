"""부분 원문 선택 평가의 무결성과 차단 경계."""

import asyncio
import copy
import json
import os

import pytest

from app.rag.evidence_bundles import BundleError
from app.rag.focused_card import (
    build_focused_material,
    documents,
    prompt_and_schema,
    supported_question,
    validate_selection,
    verify_material,
)

# 자연어 생성 구현 전에 고정. 개발 중 본 질문은 이후 홀드아웃으로 재분류하지 않는다.
NATURAL_DEVELOPMENT_QUESTIONS = (
    "애가 둘이면 카드로 쓴 돈의 공제 상한도 달라지나요?",
    "자녀가 없는 근로자의 카드 소득공제 기본 한도를 알려주세요",
    "자녀 한 명이면 총급여에 따라 카드 공제 한도가 달라지나요?",
    "자녀 둘 이상일 때 카드 기본 한도와 추가 한도는 같은 건가요?",
    "카드 공제 한도의 자녀 나이와 장애 예외는 어떻게 확인하나요?",
    "대학생 아이가 카드 공제 한도의 자녀에 해당하는지 모르겠어요",
    "카드 포인트로 아이 장난감을 사도 되나요?",
    "자녀 카드 공제 한도와 월세 공제를 함께 알려주세요",
)
NATURAL_FINAL_CHECK_QUESTIONS = (
    "아이를 키우지 않는 경우에도 카드 소득공제 기본 한도가 있나요?",
    "외동을 둔 직장인인데 연봉별 카드 공제 한도를 비교하고 싶어요",
    "자녀 셋을 키울 때 카드 공제 기본 상한은 급여별로 어떻게 다른가요?",
    "다른 사람이 기본공제 받는 자녀도 제 카드 공제 한도에 넣나요?",
)


@pytest.fixture
def natural_material(prepared):
    prepared["modelEvidence"][1]["content"] = (
        "⑩ 연간250만원(해당 과세연도의 총급여액이7천만원이하인 경우에는 연간300만원)을 한도로 한다. "
        "1. 해당 과세연도의 총급여액이7천만원이하인 경우: 자녀등이1명인 경우 연간350만원, 자녀등이2명 이상인 경우 연간400만원 "
        "2. 제1호 외의 경우: 자녀등이1명인 경우 연간275만원, 자녀등이2명 이상인 경우 연간300만원\n⑪ 추가 한도"
    )
    prepared["modelEvidence"][2]["content"] = (
        "직계비속 등으로서 다음 각 호의 요건을 모두 충족하는 사람. "
        "1. 소득금액 합계액100만원 이하이거나 총급여500만원 이하의 근로소득만 있을 것 "
        "2. 20세 이하(장애인은 나이의 제한을 받지 않는다)일 것 "
        "3. 다른 거주자의 기본공제를 적용받지 않을 것"
    )
    return build_focused_material(prepared)


def test_natural_facts_bind_salary_and_children_not_just_numbers(natural_material):
    from app.rag.focused_card import card_facts

    facts = card_facts(natural_material)
    assert facts["rows"][0]["salary"] == "7천만원 이하"
    assert facts["rows"][1]["salary"] == "7천만원 초과"
    assert facts["rows"][0]["children"][-1] == ("2", "이상", "400만원")
    assert facts["rows"][1]["children"][-1] == ("2", "이상", "300만원")
    assert "나이의 제한을 받지 않는다" in facts["definitionRequirements"][1]
    assert "적용받지 않을 것" in facts["definitionRequirements"][2]
    assert facts["applicableTaxYear"] is None


def test_natural_hybrid_renders_only_source_facts(natural_material):
    from app.rag.focused_card import validate_natural

    result = validate_natural(
        json.dumps(
            {
                "lead": "공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라집니다.",
                "citations": ["F1", "F2"],
            }
        ),
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}',
        natural_material,
    )
    assert result["status"] == "NATURAL_EVALUATION"
    assert result["checks"]["numbersAndConditions"] and result["checks"]["citations"]
    assert not result["checks"]["userDisplayAllowed"]
    assert not result["checks"]["applicabilityVerified"]
    assert "추가 한도는 구분" in result["answer"]
    assert "검증은 완료되지 않았습니다" in result["answer"]


def test_observed_equivalent_sentence_ending_is_not_semantic_change(natural_material):
    from app.rag.focused_card import validate_natural

    result = validate_natural(
        '{"lead":"공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라진다.","citations":["F1","F2"]}',
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}',
        natural_material,
    )
    assert result["status"] == "NATURAL_EVALUATION"


def test_observed_subject_order_keeps_same_relation(natural_material):
    from app.rag.focused_card import validate_natural

    result = validate_natural(
        '{"lead":"카드 소득공제 기본 한도는 공제대상 자녀 수와 총급여 구간에 따라 달라진다.","citations":["F1","F2"]}',
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}',
        natural_material,
    )
    assert result["status"] == "NATURAL_EVALUATION"


@pytest.mark.parametrize("change", ["미만", "장애 예외 삭제", "부정 삭제"])
def test_condition_parser_fails_closed_on_unsupported_boundaries(
    prepared, natural_material, change
):
    from app.rag.focused_card import card_facts
    from app.rag.loader import digest
    from app.rag.pipeline import canonical

    data = copy.deepcopy(natural_material)
    role = "CAP" if change == "미만" else "DEFINITION"
    region = next(r for r in data["regions"] if r["role"] == role)
    if change == "미만":
        region["content"] = region["content"].replace("이하", "미만")
    elif change == "장애 예외 삭제":
        region["content"] = region["content"].replace(
            "나이의 제한을 받지 않는다", "나이의 제한을 받는다"
        )
    else:
        region["content"] = region["content"].replace("적용받지 않을 것", "적용받을 것")
    data["selectionHash"] = digest(
        canonical({k: v for k, v in data.items() if k != "selectionHash"}).encode()
    )
    with pytest.raises(BundleError):
        card_facts(data)


@pytest.mark.skipif(
    os.environ.get("RUN_NATURAL_CARD_INTEGRATION") != "1",
    reason="실제 자연어 Gemma 평가 명시 실행",
)
def test_live_natural_keeps_evaluation_boundary():
    from scripts.evaluate_focused_card import compare_natural

    result = asyncio.run(compare_natural(NATURAL_DEVELOPMENT_QUESTIONS[0]))
    assert result["indexVerification"]["count"] == 6
    assert result["originalIndexVerification"]["count"] == 33
    assert not result["answerUseAllowed"]
    assert result["rawNaturalOutput"]
    if result["status"] == "NATURAL_EVALUATION":
        assert not result["naturalValidation"]["checks"]["userDisplayAllowed"]
    else:
        assert result["answer"] is None


@pytest.mark.parametrize(
    "lead",
    [
        "자녀가 둘이면 누구나 400만원을 공제받습니다.",
        "공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 같아집니다.",
        "공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라집니다. 장애인은 제외됩니다.",
        "공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라집니다. 2026년부터 확정입니다.",
        "나이가 초과해도 모든 자녀가 포함됩니다.",
        "월세 공제와 합산한 한도입니다.",
        "총급여 미만이면 더 많은 한도가 적용됩니다.",
    ],
)
def test_wrong_meaning_numeric_dates_and_extra_claims_hold(natural_material, lead):
    from app.rag.focused_card import validate_natural

    result = validate_natural(
        json.dumps({"lead": lead, "citations": ["F1", "F2"]}),
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}',
        natural_material,
    )
    assert result["answer"] is None and result["status"] == "HOLD"


def test_natural_unknown_or_unselected_citation_holds(natural_material):
    from app.rag.focused_card import validate_natural

    result = validate_natural(
        json.dumps(
            {
                "lead": "공제대상 자녀 수와 총급여 구간에 따라 카드 소득공제 기본 한도가 달라집니다.",
                "citations": ["F1", "F99"],
            }
        ),
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}',
        natural_material,
    )
    assert result["reason"] == "UNTRACEABLE_NATURAL_CITATION"


def test_natural_dataset_frozen_before_generation_changes():
    from app.rag.loader import digest

    dataset = {
        "NATURAL_DEVELOPMENT_QUESTIONS": NATURAL_DEVELOPMENT_QUESTIONS,
        "NATURAL_FINAL_CHECK_QUESTIONS": NATURAL_FINAL_CHECK_QUESTIONS,
    }
    assert (
        digest(json.dumps(dataset, ensure_ascii=False, sort_keys=True).encode())
        == "bcf2d70dabb6364a355e17965d4ccde4a72d6f865241096fbb2d27530fc779d1"
    )


@pytest.fixture
def prepared():
    def part(role, text, key):
        return {
            "evidenceId": key,
            "content": text,
            "source": {
                "chunkId": key,
                "documentTitle": "테스트 법령",
                "documentVersion": "v1",
                "article": "시험 조문",
            },
            "context": {
                "role": role,
                "officialEvidence": [],
                "officialLawId": "test",
                "officialLawVersion": "v1",
            },
        }

    return {
        "status": "PREPARED_NOT_GENERATED",
        "unresolvedIssues": ["적용시점 미확인"],
        "modelEvidence": [
            part("RULE", "① 자격 단서와 제외 사유\n② 관련 없는 계산식", "a"),
            part(
                "RULE",
                "③ 다른 내용\n⑩ 급여와 자녀 수별 한도. 다만 예외 유지 400만원\n⑪ 추가 한도",
                "b",
            ),
            part(
                "DEFINITION",
                "자녀 소득과 나이, 장애인 예외, 다른 거주자 기본공제를 받지 않을 것",
                "c",
            ),
            part("APPLICATION", "법률 시행일 원문", "d"),
            part("APPLICATION", "시행령 시행일과 예외 원문", "e"),
        ],
    }


def test_reproducible_exact_spans_and_numeric_conditions(prepared):
    original = copy.deepcopy(prepared)
    material = build_focused_material(prepared)
    assert material == build_focused_material(prepared)
    assert prepared == original
    assert len(material["regions"]) == 6
    parents = {p["evidenceId"]: p for p in prepared["modelEvidence"]}
    for r in material["regions"]:
        origin = r["origin"]
        assert (
            r["content"]
            == parents[origin["parentEvidenceId"]]["content"][
                origin["start"] : origin["end"]
            ]
        )
        assert r["applicableTaxYear"] is None and not r["applicabilityVerified"]
        for span in r["structuredEvidence"]["numericSpans"]:
            assert r["content"][span["start"] : span["end"]] == span["text"]
    assert "다만" in material["regions"][0]["content"]
    assert "관련 없는 계산식" not in str(material)


@pytest.mark.parametrize("field", ["content", "contentHash", "role"])
def test_tamper_never_renders(prepared, field):
    material = build_focused_material(prepared)
    material["regions"][0][field] = "변조"
    with pytest.raises(BundleError):
        verify_material(material, prepared)
    assert (
        validate_selection('{"status":"SELECTED","evidenceIds":["F1","F2"]}', material)[
            "answer"
        ]
        is None
    )


@pytest.mark.parametrize(
    "raw",
    [
        '{"status":"SELECTED","evidenceIds":["F1"]}',
        '{"status":"SELECTED","evidenceIds":["F1","F99"]}',
        '{"status":"SELECTED","evidenceIds":["F1","F1","F2"]}',
        '{"status":"SELECTED","evidenceIds":["F1","F2"],"answer":"999만원"}',
        '{"status":"INSUFFICIENT_EVIDENCE","evidenceIds":[]}',
        "not json",
    ],
)
def test_missing_definition_hallucination_or_model_hold(prepared, raw):
    assert validate_selection(raw, build_focused_material(prepared))["answer"] is None


def test_exact_rendering_keeps_context_and_no_approval(prepared):
    material = build_focused_material(prepared)
    result = validate_selection(
        '{"status":"SELECTED","evidenceIds":["F1","F2"]}', material
    )
    assert result["status"] == "EXTRACTIVE_EVALUATION"
    assert not result["answerUseAllowed"] and not result["applicabilityVerified"]
    assert len(result["requiredContext"]) == 6
    assert "400만원" in result["answer"] and "받지 않을 것" in result["answer"]
    assert len(result["citations"]) == 2


@pytest.mark.parametrize(
    "query",
    [
        "월세 공제 한도",
        "카드 추천해줘",
        "아이 카드게임 상한",
        "자녀 카드 공제와 월세 공제 한도",
    ],
)
def test_unsupported_or_mixed_never_calls_model(query):
    assert not supported_question(query)


def test_search_integrity_and_full_context_prompt(prepared):
    material = build_focused_material(prepared)
    hits = documents(material)
    prompt, _ = prompt_and_schema("자녀 둘 카드 공제 한도는?", hits, material)
    assert len(json.loads(prompt)["evidence"]) == 6
    hits[0] = {**hits[0], "content": "원문과 다름"}
    with pytest.raises(BundleError):
        prompt_and_schema("자녀 둘 카드 공제 한도는?", hits, material)


def test_missing_paragraph_boundary_fails_closed(prepared):
    prepared["modelEvidence"][1]["content"] = "⑩ 단서 뒤의 경계가 없어짐"
    with pytest.raises(BundleError):
        build_focused_material(prepared)


@pytest.mark.parametrize(
    "query",
    [
        "애가 둘이면 카드로 쓴 돈의 공제 상한도 달라지나요?",
        "자녀 수에 따른 신용카드 소득공제 한도는?",
        "아이 둘 카드 공제 한도를 알고 싶어요",
    ],
)
def test_related_paraphrases(query):
    assert supported_question(query)


def test_cap_must_be_retrieved_not_just_attached(prepared):
    material = build_focused_material(prepared)
    with pytest.raises(BundleError, match="CAP_NOT_RETRIEVED"):
        prompt_and_schema("자녀 카드 공제 한도는?", documents(material)[1:], material)


def test_saved_material_reuses_json_tuple_representation_without_overwrite(
    prepared, tmp_path, monkeypatch
):
    from scripts import evaluate_focused_card as cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    prepared["unresolvedIssues"] = tuple(prepared["unresolvedIssues"])
    material = build_focused_material(prepared)
    file = tmp_path / cli.save_material(material)
    before = file.read_bytes()
    assert tmp_path / cli.save_material(material) == file
    assert file.read_bytes() == before
    file.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="EXISTING_FOCUSED_MATERIAL_CHANGED"):
        cli.save_material(material)


@pytest.mark.skipif(
    os.environ.get("RUN_FOCUSED_CARD_INTEGRATION") != "1",
    reason="실제 로컬 ES/Ollama 명시 실행",
)
def test_live_focused_comparison_keeps_old_index_and_holds_legal_use():
    from scripts.evaluate_focused_card import compare

    result = asyncio.run(compare("애가 둘이면 카드로 쓴 돈의 공제 상한도 달라지나요?"))
    assert result["originalIndexVerification"]["count"] == 33
    assert result["indexVerification"]["count"] == 6
    assert result["index"].startswith("hope-rag-eval-")
    assert result["focusedPromptBytes"] < result["baselinePromptBytes"]
    assert result["rawModelOutput"]
    assert not result["answerUseAllowed"]
    if result["focused"]["status"] == "EXTRACTIVE_EVALUATION":
        for region in result["material"]["regions"]:
            assert region["applicableTaxYear"] is None
            assert not region["applicabilityVerified"]
    else:
        # 모델의 비결정적 선택 누락을 답변 승인으로 바꾸지 않는다.
        assert result["focused"]["answer"] is None
