"""저장소 루트 또는 chatbot 디렉터리에서 실행하는 오프라인 CLI."""

import argparse
import sys
from pathlib import Path

CHATBOT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHATBOT_ROOT))

from app.rag.models import Config  # noqa: E402
from app.rag.pipeline import run_pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="법령 PDF 구조 전처리 (검색/API 연결 없음)"
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--output-root", type=Path, default=CHATBOT_ROOT / "data/processed"
    )
    parser.add_argument("--expected-count", type=int, default=8)
    parser.add_argument("--max-chars", type=int, default=2500)
    parser.add_argument("--verify-reproducibility", action="store_true")
    parser.add_argument("--reuse", action="store_true")
    args = parser.parse_args()
    if not args.output_root.resolve().is_relative_to(
        (CHATBOT_ROOT / "data/processed").resolve()
    ):
        parser.error("출력은 chatbot/data/processed 하위만 허용합니다.")
    try:
        output = run_pipeline(
            args.input_dir.resolve(),
            args.output_root.resolve(),
            Config(max_chars=args.max_chars),
            args.expected_count,
            args.verify_reproducibility,
            args.reuse,
        )
    except (ValueError, FileExistsError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    print(output)


if __name__ == "__main__":
    main()
