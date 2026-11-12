"""기존 카드 RAG와 원문 선택형 최소 구성을 비교하는 로컬 평가 CLI."""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import InternalApiSettings, OllamaSettings  # noqa: E402
from app.llm.ollama import OllamaService  # noqa: E402
from app.rag.elasticsearch_store import EvaluationStore  # noqa: E402
from app.rag.evaluation_rag import load_evaluation_rag  # noqa: E402
from app.rag.focused_card import (  # noqa: E402
    NATURAL_SYSTEM,
    SYSTEM,
    build_focused_material,
    documents,
    natural_prompt,
    prompt_and_schema,
    supported_question,
    validate_natural,
    validate_selection,
    verify_material,
)
from app.rag.pipeline import canonical  # noqa: E402
from app.services.generation import GenerationService, UnavailableRetriever  # noqa: E402
from scripts.run_rag_evaluation import (  # noqa: E402
    DEFAULT_EVIDENCE,
    DEFAULT_SELECTION,
    ROOT,
    save_report,
)


def save_material(material):
    file = (
        ROOT
        / "data/processed/focused-card-materials"
        / material["selectionHash"]
        / "material.json"
    )
    if file.exists():
        if canonical(json.loads(file.read_text(encoding="utf-8"))) != canonical(
            material
        ):
            raise ValueError("EXISTING_FOCUSED_MATERIAL_CHANGED")
    else:
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(material, ensure_ascii=False, indent=2) + "\n")
    return str(file.relative_to(ROOT))


async def compare(question, *, generate=True):
    if not supported_question(question):
        return {
            "status": "HOLD",
            "reason": "FOCUSED_QUESTION_NOT_SUPPORTED",
            "answerUseAllowed": False,
        }
    original = load_evaluation_rag(DEFAULT_SELECTION, DEFAULT_EVIDENCE)
    focused = None
    try:
        prepared = await original.respond(question, generate=False)
        material = build_focused_material(prepared)
        verify_material(material, prepared)
        material_file = save_material(material)
        focused = EvaluationStore(material["selectionHash"])
        index_report = focused.index_documents(documents(material), reuse=True)
        start = time.perf_counter()
        hits = focused.search(question, deduplicate=False, size=6)
        search_seconds = time.perf_counter() - start
        prompt, schema = prompt_and_schema(question, hits, material)
        result = {
            "status": "PREPARED_NOT_GENERATED",
            "usageScope": "EVALUATION_ONLY",
            "answerUseAllowed": False,
            "material": material,
            "materialFile": material_file,
            "index": focused.index,
            "indexVerification": index_report,
            "question": question,
            "retrieved": hits,
            "searchSeconds": search_seconds,
            "systemMessage": SYSTEM,
            "userMessage": prompt,
            "baselinePromptBytes": prepared["promptBudget"]["inputBytes"],
            "focusedPromptBytes": len((SYSTEM + prompt).encode()),
            "comparisonCaveat": "자유 생성과 원문 선택은 다른 능력이며 답변 통과율을 동등 지표로 비교하지 않습니다.",
        }
        if generate:
            settings = OllamaSettings.from_env()
            if (
                settings.base_url.host not in {"localhost", "127.0.0.1", "::1"}
                or settings.base_url.username
                or settings.base_url.password
            ):
                raise ValueError("LOCAL_OLLAMA_REQUIRED")
            generation = GenerationService(
                UnavailableRetriever(),
                OllamaService(
                    settings, num_ctx=32768, num_predict=512, response_format=schema
                ),
                InternalApiSettings(model_timeout=60),
            )
            start = time.perf_counter()
            baseline = await original.respond(question)
            result["baselineSeconds"] = time.perf_counter() - start
            result["baseline"] = baseline
            start = time.perf_counter()
            raw = await generation.generate_prompt(prompt, SYSTEM)
            result["focusedGenerationSeconds"] = time.perf_counter() - start
            result["rawModelOutput"] = raw
            result["focused"] = validate_selection(raw, material)
            result["status"] = result["focused"]["status"]
        # 기존 인덱스는 읽기만 수행하고 마지막에 전체 문서를 대조한다.
        result["originalIndexVerification"] = original.store.verify(
            list(original.documents.values())
        )
        return result
    finally:
        if focused:
            focused.close()
        original.store.close()


async def compare_natural(question):
    """새 파일/색인을 만들지 않고 기존 평가 자료만 읽어 2단계 모델 호출을 평가한다."""
    result = {
        "question": question,
        "usageScope": "EVALUATION_ONLY",
        "answerUseAllowed": False,
        "answer": None,
        "status": "HOLD",
    }
    if not supported_question(question):
        return {
            **result,
            "reason": "FOCUSED_QUESTION_NOT_SUPPORTED",
            "modelCalled": False,
        }
    original = load_evaluation_rag(DEFAULT_SELECTION, DEFAULT_EVIDENCE)
    focused = None
    try:
        prepared = await original.respond(question, generate=False)
        material = build_focused_material(prepared)
        file = (
            ROOT
            / "data/processed/focused-card-materials"
            / material["selectionHash"]
            / "material.json"
        )
        if not file.is_file() or canonical(
            json.loads(file.read_text(encoding="utf-8"))
        ) != canonical(material):
            raise ValueError("EXISTING_MATERIAL_REQUIRED")
        focused = EvaluationStore(material["selectionHash"])
        result["indexVerification"] = focused.verify(documents(material))
        hits = focused.search(question, deduplicate=False, size=6)
        result.update(
            {
                "retrieved": hits,
                "index": focused.index,
                "materialHash": material["selectionHash"],
            }
        )
        prompt, schema = prompt_and_schema(question, hits, material)
        settings = OllamaSettings.from_env()
        if (
            settings.base_url.host not in {"localhost", "127.0.0.1", "::1"}
            or settings.base_url.username
            or settings.base_url.password
        ):
            raise ValueError("LOCAL_OLLAMA_REQUIRED")

        async def call(payload, system, response_schema):
            generation = GenerationService(
                UnavailableRetriever(),
                OllamaService(
                    settings,
                    num_ctx=32768,
                    num_predict=512,
                    response_format=response_schema,
                ),
                InternalApiSettings(model_timeout=60),
            )
            return await generation.generate_prompt(payload, system)

        start = time.perf_counter()
        selection = await call(prompt, SYSTEM, schema)
        result.update(
            {
                "modelCalled": True,
                "rawSelection": selection,
                "selectionValidation": validate_selection(selection, material),
            }
        )
        if result["selectionValidation"]["status"] != "EXTRACTIVE_EVALUATION":
            return {**result, "reason": result["selectionValidation"]["reason"]}
        prompt, schema = natural_prompt(question, selection, material)
        raw = await call(prompt, NATURAL_SYSTEM, schema)
        result.update(
            {
                "rawNaturalOutput": raw,
                "naturalSystem": NATURAL_SYSTEM,
                "naturalPrompt": prompt,
                "modelSeconds": time.perf_counter() - start,
            }
        )
        validated = validate_natural(raw, selection, material)
        result.update(
            {
                "naturalValidation": validated,
                "status": validated["status"],
                "answer": validated["answer"],
            }
        )
        if "reason" in validated:
            result["reason"] = validated["reason"]
        result["originalIndexVerification"] = original.store.verify(
            list(original.documents.values())
        )
        return result
    finally:
        if focused:
            focused.close()
        original.store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--question", default="애가 둘이면 카드로 쓴 돈의 공제 상한도 달라지나요?"
    )
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument(
        "--natural",
        action="store_true",
        help="자연어 평가. 기존 자료를 읽고 결과를 표준 출력으로만 반환",
    )
    args = parser.parse_args()
    try:
        if args.natural and args.no_model:
            parser.error("--natural과 --no-model은 함께 사용할 수 없습니다.")
        result = asyncio.run(
            compare_natural(args.question)
            if args.natural
            else compare(args.question, generate=not args.no_model)
        )
    except Exception as exc:
        # 로컬 CLI도 내부 오류 세부사항/인증정보를 결과에 복사하지 않는다.
        result = {
            "status": "HOLD",
            "reason": type(exc).__name__,
            "answerUseAllowed": False,
        }
    if args.natural:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(save_report(result, ROOT / "data/processed/focused-card-evaluations"))
    return (
        0
        if result["status"]
        in {"EXTRACTIVE_EVALUATION", "PREPARED_NOT_GENERATED", "NATURAL_EVALUATION"}
        else 2
    )


if __name__ == "__main__":
    sys.exit(main())
