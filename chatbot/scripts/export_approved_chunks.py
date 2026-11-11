"""승인 게이트를 통과한 검색용 자료만 내보낸다. 색인은 하지 않는다."""

import argparse
import sys
from pathlib import Path

CHATBOT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHATBOT_ROOT))

from app.rag.approval_gate import export_approved  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="review-policy-v3 영역·필수 문맥 승인 자료만 내보내기(v2 자동 승격 금지)"
    )
    parser.add_argument("--processed-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument(
        "--output-root", type=Path, default=CHATBOT_ROOT / "data/processed/exports"
    )
    args = parser.parse_args()
    if not args.output_root.resolve().is_relative_to(
        (CHATBOT_ROOT / "data/processed/exports").resolve()
    ):
        parser.error("내보내기는 chatbot/data/processed/exports 하위만 허용합니다.")
    try:
        print(
            export_approved(
                args.processed_dir,
                args.raw_dir,
                args.ledger,
                args.evidence_root,
                args.output_root,
            )
        )
    except (ValueError, FileExistsError, OSError) as exc:
        parser.exit(1, f"승인 자료 내보내기 실패: {exc}\n")


if __name__ == "__main__":
    main()
