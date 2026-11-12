"""격리된 loopback 평가 인덱스만 적재한다. 운영 API와 무관하다."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.elasticsearch_documents import evaluation_documents  # noqa: E402
from app.rag.elasticsearch_store import EvaluationSearchError, EvaluationStore  # noqa: E402
from app.rag.loader import digest  # noqa: E402
from app.rag.pipeline import canonical  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument(
        "--profile", choices=["baseline", "quality-v2"], default="baseline"
    )
    args = parser.parse_args()
    store = None
    try:
        selection = json.loads(args.selection.read_text(encoding="utf-8"))
        documents = evaluation_documents(selection, profile=args.profile)
        store = EvaluationStore(selection["selectionHash"], profile=args.profile)
        result = {
            "server": store.health(),
            **store.index_documents(documents, reuse=args.reuse),
            "selectionHash": selection["selectionHash"],
            "usageScope": "EVALUATION_ONLY",
        }
        root = (
            Path(__file__).resolve().parents[1]
            / "data/processed/evaluation-index-reports"
        )
        path = root / digest(canonical(result).encode()) / "index-report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != result:
            raise ValueError("기존 색인 검증 보고서가 다릅니다.")
        if not path.exists():
            path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(path)
    except (OSError, ValueError, EvaluationSearchError) as exc:
        parser.exit(1, f"평가 색인 실패: {exc}\n")
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    main()
