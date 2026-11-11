"""기존 전처리 결과를 읽어 별도 검수 묶음을 생성한다."""

import argparse
import sys
from pathlib import Path

CHATBOT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHATBOT_ROOT))

from app.rag.review_queue import build_review_bundle  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="승인 없는 검수 대기열 생성")
    parser.add_argument("--processed-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument(
        "--output-root", type=Path, default=CHATBOT_ROOT / "data/processed/reviews"
    )
    parser.add_argument("--seed", default="hope-refund-v1")
    parser.add_argument("--sample-size", type=int, default=30)
    args = parser.parse_args()
    allowed = (CHATBOT_ROOT / "data/processed/reviews").resolve()
    if not args.output_root.resolve().is_relative_to(allowed):
        parser.error("검수 출력은 chatbot/data/processed/reviews 하위만 허용합니다.")
    try:
        print(
            build_review_bundle(
                args.processed_dir,
                args.raw_dir,
                args.output_root,
                args.seed,
                args.sample_size,
            )
        )
    except (ValueError, FileExistsError, OSError) as exc:
        parser.exit(1, f"검수 묶음 생성 실패: {exc}\n")


if __name__ == "__main__":
    main()
