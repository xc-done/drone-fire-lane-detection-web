# Dataset

The dataset itself is **not committed** to this repository (944 images plus
labels would add ~hundreds of MB). What is committed is the configuration and
the split recipe, so the model can be reproduced.

## Source

`firc-dataset` — a public dataset of 944 drone-view images of fire escape
(消防通道) areas, 1920×1080, 3 annotated classes, 4567 bounding boxes.

Expected layout before splitting:

```text
datasets/fly/data/
├── JPEGImages/          # 944 .jpg
├── Annotations/         # 944 Pascal VOC .xml
└── labels/
    ├── classes.txt      # car / fire escape occupation / non-motorized vehicle
    └── *.txt            # YOLO txt labels
```

## Split

Run:

```bash
python scripts/prepare_fly_dataset.py --clean
```

It validates that every image has a matching `.xml` + `.txt`, shuffles with
`seed=42`, and produces `datasets/fly_yolo/`:

| Split | Images |
|-------|--------|
| train | 755 |
| val   | 94 |
| test  | 95 |
| total | 944 |

along with `images/{train,val,test}/`, `labels/{train,val,test}/`,
`fire_escape.yaml`, `manifest.json`, and `splits.json`.

## Classes

| id | name | meaning |
|----|------|---------|
| 0 | car | 机动车 |
| 1 | fire escape occupation | 消防通道占用区域 |
| 2 | non-motorized vehicle | 非机动车 |

These are the exact class names stored inside `weights/best.pt`, so any rename
must be applied to both the dataset YAML and the model.
