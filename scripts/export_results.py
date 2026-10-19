"""Regenerate results/results.csv and assets/training-curves.png from weights/best.pt.

The shipped checkpoint keeps the full per-epoch history in its `train_results`
field, so the original results.csv (which lived in the now-deleted training
workspace) can be rebuilt exactly.
"""

import csv
from pathlib import Path

import matplotlib
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CKPT = REPO / "weights" / "best.pt"
CSV_OUT = REPO / "results" / "results.csv"
PLOT_OUT = REPO / "assets" / "training-curves.png"

COLUMNS = [
    "epoch",
    "time",
    "train/box_loss",
    "train/cls_loss",
    "train/dfl_loss",
    "metrics/precision(B)",
    "metrics/recall(B)",
    "metrics/mAP50(B)",
    "metrics/mAP50-95(B)",
    "val/box_loss",
    "val/cls_loss",
    "val/dfl_loss",
    "lr/pg0",
    "lr/pg1",
    "lr/pg2",
]


def main() -> None:
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
    hist = ckpt["train_results"]
    epochs = int(len(hist["epoch"]))
    metrics = ckpt["train_metrics"]
    args = ckpt.get("train_args") or {}

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for i in range(epochs):
            row = []
            for col in COLUMNS:
                value = hist.get(col, [0.0] * epochs)[i]
                row.append(int(value) if col == "epoch" else round(float(value), 5))
            writer.writerow(row)

    series = {
        "mAP50": [float(v) for v in hist["metrics/mAP50(B)"]],
        "mAP50-95": [float(v) for v in hist["metrics/mAP50-95(B)"]],
        "precision": [float(v) for v in hist["metrics/precision(B)"]],
        "recall": [float(v) for v in hist["metrics/recall(B)"]],
    }
    ep = [int(v) for v in hist["epoch"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6), dpi=150)

    ax1.plot(ep, series["mAP50"], label="mAP@50", lw=2)
    ax1.plot(ep, series["mAP50-95"], label="mAP@50-95", lw=2)
    ax1.set_title("Detection accuracy")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("mAP")
    ax1.grid(alpha=0.3)
    ax1.legend()
    ax1.annotate(
        f"best mAP@50 = {max(series['mAP50']):.4f}\nbest mAP@50-95 = {max(series['mAP50-95']):.4f}",
        xy=(0.42, 0.18),
        xycoords="axes fraction",
        fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec="0.7"),
    )

    ax2.plot(ep, series["precision"], label="precision", lw=2)
    ax2.plot(ep, series["recall"], label="recall", lw=2)
    ax2.set_title("Precision / recall")
    ax2.set_xlabel("epoch")
    ax2.set_ylabel("score")
    ax2.set_ylim(0, 1)
    ax2.grid(alpha=0.3)
    ax2.legend()

    fig.suptitle(
        "YOLO26m · fire-escape dataset · "
        f"{epochs} epochs · batch={args.get('batch')} · imgsz={args.get('imgsz')}",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(PLOT_OUT)
    plt.close(fig)

    print(f"wrote {CSV_OUT} ({epochs} rows)")
    print(f"wrote {PLOT_OUT}")
    print(
        "final:",
        {k: round(float(v), 5) for k, v in metrics.items() if k.startswith("metrics/")},
    )


if __name__ == "__main__":
    main()
