"""질문 하나를 로컬 ES→문맥 묶음→실제 Ollama로 평가한다. 운영 API와 무관하다."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.elasticsearch_store import EvaluationSearchError  # noqa: E402
from app.rag.evaluation_rag import load_evaluation_rag  # noqa: E402
from app.rag.evidence_bundles import BundleError  # noqa: E402
from app.rag.loader import digest  # noqa: E402
from app.rag.pipeline import canonical  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = (
    ROOT
    / "data/processed/scopes/73c351ccb18f18833928ddc78052bf0e3233f3b7a83bee9fdaf411748f44e642/scope.json"
)
DEFAULT_EVIDENCE = ROOT / "data/processed/evidence/2026-11-11-core3-v3"


def save_report(result, root):
    root = Path(root).resolve()
    if not root.is_relative_to((ROOT / "data/processed").resolve()):
        raise ValueError("평가 결과는 chatbot/data/processed 하위에 저장합니다.")
    file = root / digest(canonical(result).encode()) / "evaluation.json"
    if file.exists():
        if json.loads(file.read_text(encoding="utf-8")) != result:
            raise ValueError("기존 결과를 덮어쓸 수 없습니다.")
    else:
        file.parent.mkdir(parents=True, exist_ok=False)
        file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument(
        "--context-window", type=int, choices=[8192, 16384, 32768], default=32768
    )
    parser.add_argument(
        "--output-root", type=Path, default=ROOT / "data/processed/rag-evaluations"
    )
    args = parser.parse_args()
    runner = None
    try:
        runner = load_evaluation_rag(
            args.selection, args.evidence_root, context_window=args.context_window
        )
        result = asyncio.run(runner.respond(args.question, generate=not args.no_model))
    except (OSError, ValueError, BundleError, EvaluationSearchError):
        result = {
            "status": "INSUFFICIENT_EVIDENCE",
            "usageScope": "EVALUATION_ONLY",
            "question": args.question,
            "modelCalled": False,
            "holdReason": "EVALUATION_RESOURCES_UNAVAILABLE",
            "answerUseAllowed": False,
        }
    finally:
        if runner:
            runner.store.close()
    print(save_report(result, args.output_root))
    return (
        0
        if result["status"] in {"ANSWERED", "PREPARED_NOT_GENERATED", "OUT_OF_SCOPE"}
        else 2
    )


if __name__ == "__main__":
    sys.exit(main())
