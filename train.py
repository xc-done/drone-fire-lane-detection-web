"""Train the fire-lane occupancy detector.

The defaults below reproduce weights/best.pt: they were read back from the
shipped checkpoint's own ``train_args`` / ``train_results`` fields, not copied
from an earlier draft, so re-running this script matches the reported metrics
in results/metrics.md.

Usage:
    python scripts/prepare_fly_dataset.py --clean   # build the YOLO splits first
    python train.py                                  # train (GPU 0 by default)

Dataset images are not in this repository: see datasets/README.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = REPO_ROOT / "datasets" / "fire_escape.yaml"
DEFAULT_PROJECT = REPO_ROOT / "runs" / "fire_escape"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune YOLO26m on the fire-escape dataset.")
    parser.add_argument("--model", default="yolo26m.pt", help="Pretrained checkpoint to start from.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Dataset YAML.")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--device", default="0", help="'0' for the first GPU, 'cpu' to force CPU.")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT, help="Output directory.")
    parser.add_argument("--name", default="gen2", help="Run name inside --project.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.data.exists():
        raise FileNotFoundError(
            f"Missing dataset config: {args.data}\n"
            "Build the splits first: python scripts/prepare_fly_dataset.py --clean"
        )

    model = YOLO(args.model)
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        patience=30,
        optimizer="AdamW",
        lr0=0.0003,
        cos_lr=True,
        warmup_epochs=3,
        mosaic=1.0,
        close_mosaic=10,
        mixup=0.2,
        copy_paste=0.3,
        project=str(args.project),
        name=args.name,
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
