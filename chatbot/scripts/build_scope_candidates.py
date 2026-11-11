"""기존 두 코퍼스와 v3 초안을 읽어 평가 후보만 별도 저장한다."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.scope import build_scope, save_selection  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        nargs=2,
        action="append",
        required=True,
        metavar=("PROCESSED", "RAW"),
    )
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--mode", choices=["initial", "expanded"], default="initial")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data/processed/scopes",
    )
    args = parser.parse_args()
    try:
        print(
            save_selection(
                build_scope(args.corpus, args.ledger, mode=args.mode), args.output_root
            )
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"후보 선정 실패: {exc}\n")


if __name__ == "__main__":
    main()
