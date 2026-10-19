import argparse
import json
import os
import random
import shutil
from collections import Counter
from pathlib import Path


def hardlink_or_copy(src: Path, dst: Path) -> None:
    """Create a hardlink if possible, otherwise copy the file."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def resolve_path(base_dir: Path, path: Path) -> Path:
    return path if path.is_absolute() else base_dir / path


def read_label_classes(label_path: Path) -> list[int]:
    classes: list[int] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Invalid YOLO label line in {label_path}: {line!r}")
        class_id = int(float(fields[0]))
        classes.append(class_id)
    return classes


def build_index(directory: Path, suffixes: set[str], excluded_names: set[str] | None = None) -> dict[str, Path]:
    excluded_names = excluded_names or set()
    index: dict[str, Path] = {}
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in suffixes or path.name in excluded_names:
            continue
        if path.stem in index:
            raise ValueError(f"Duplicate stem found: {path.stem}")
        index[path.stem] = path
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Split the fly dataset into train/val/test YOLO splits.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("datasets/fly/data"),
        help="Source folder containing JPEGImages/, Annotations/ and labels/.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("datasets/fly_yolo"),
        help="Output YOLO dataset root.",
    )
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Training split ratio.")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used for splitting.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete output-root before generating, then create from scratch.",
    )
    args = parser.parse_args()

    if not 0.0 < args.train_ratio < 1.0 or not 0.0 < args.val_ratio < 1.0:
        raise ValueError("train_ratio and val_ratio must be between 0 and 1.")
    if args.train_ratio + args.val_ratio >= 1.0:
        raise ValueError("train_ratio + val_ratio must be less than 1 so test split is non-empty.")

    repo_root = Path(__file__).resolve().parents[1]
    source_root = resolve_path(repo_root, args.source_root)
    output_root = resolve_path(repo_root, args.output_root)

    if args.clean and output_root.exists():
        shutil.rmtree(output_root)

    images_dir = source_root / "JPEGImages"
    labels_dir = source_root / "labels"
    annotations_dir = source_root / "Annotations"
    classes_path = labels_dir / "classes.txt"

    for path in [source_root, images_dir, labels_dir, annotations_dir, classes_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required path: {path}")

    class_names = [
        line.strip() for line in classes_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not class_names:
        raise ValueError(f"No classes found in {classes_path}")

    images = build_index(images_dir, {".jpg", ".jpeg", ".png"})
    labels = build_index(labels_dir, {".txt"}, {"classes.txt"})
    annotations = build_index(annotations_dir, {".xml"})

    common_stems = sorted(set(images) & set(labels) & set(annotations))
    missing_pairs = []
    for stem in sorted(set(images) | set(labels) | set(annotations)):
        missing = []
        if stem not in images:
            missing.append("jpg")
        if stem not in labels:
            missing.append("txt")
        if stem not in annotations:
            missing.append("xml")
        if missing:
            missing_pairs.append((stem, missing))

    if missing_pairs:
        sample = missing_pairs[:10]
        raise ValueError(f"{len(missing_pairs)} images are missing paired files. Examples: {sample}")

    if not common_stems:
        raise ValueError("No matching jpg/txt/xml file sets found.")

    items: list[dict] = []
    total_class_counts: Counter[int] = Counter()
    for stem in common_stems:
        classes = read_label_classes(labels[stem])
        if any(class_id >= len(class_names) for class_id in classes):
            raise ValueError(f"Label class id out of range in {labels[stem]}: {classes}")
        items.append({"stem": stem, "classes": classes})
        total_class_counts.update(classes)

    item_by_stem = {item["stem"]: item for item in items}

    rng = random.Random(args.seed)
    rng.shuffle(items)

    total = len(items)
    train_count = round(total * args.train_ratio)
    val_count = round(total * args.val_ratio)
    split_sizes = {"train": train_count, "val": val_count, "test": total - train_count - val_count}

    split_names: dict[str, list[str]] = {}
    offset = 0
    for split_name in ["train", "val", "test"]:
        split_names[split_name] = [item["stem"] for item in items[offset : offset + split_sizes[split_name]]]
        offset += split_sizes[split_name]

    (output_root / "images").mkdir(parents=True, exist_ok=True)
    (output_root / "labels").mkdir(parents=True, exist_ok=True)
    hardlink_or_copy(classes_path, output_root / "labels" / "classes.txt")

    split_class_counts: dict[str, Counter[int]] = {}
    for split_name, stems in split_names.items():
        (output_root / "images" / split_name).mkdir(parents=True, exist_ok=True)
        (output_root / "labels" / split_name).mkdir(parents=True, exist_ok=True)
        split_class_counts[split_name] = Counter()

        for stem in stems:
            hardlink_or_copy(images[stem], output_root / "images" / split_name / images[stem].name)
            hardlink_or_copy(labels[stem], output_root / "labels" / split_name / labels[stem].name)
            split_class_counts[split_name].update(item_by_stem[stem]["classes"])

    data_yaml = output_root / "fire_escape.yaml"
    # Use the resolved absolute path: ultralytics resolves a *relative* `path`
    # against its global datasets_dir, which duplicates the prefix and breaks.
    yaml_lines = [
        "# Fire escape channel detection dataset",
        f"path: {output_root.resolve().as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(class_names)}",
        "names:",
    ]
    yaml_lines.extend(f"  {index}: \"{name}\"" for index, name in enumerate(class_names))
    data_yaml.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    manifest = {
        "source_root": str(source_root.relative_to(repo_root).as_posix()),
        "output_root": str(output_root.relative_to(repo_root).as_posix()),
        "image_count": total,
        "label_box_count": sum(total_class_counts.values()),
        "class_names": class_names,
        "class_box_counts": {
            name: total_class_counts[index] for index, name in enumerate(class_names)
        },
        "split_counts": split_sizes,
        "split_class_box_counts": {
            split_name: {
                name: split_class_counts[split_name][index] for index, name in enumerate(class_names)
            }
            for split_name in split_class_counts
        },
        "ratios": {"train": args.train_ratio, "val": args.val_ratio, "test": 1 - args.train_ratio - args.val_ratio},
        "seed": args.seed,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_root / "splits.json").write_text(
        json.dumps(split_names, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Saved YOLO dataset to: {output_root}")
    print(f"Dataset config: {data_yaml}")
    print(f"Split sizes: {split_sizes}")
    print(f"Total boxes: {dict(total_class_counts)}")


if __name__ == "__main__":
    main()
