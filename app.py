from __future__ import annotations

import base64
import html
import json
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List

import cv2
from flask import Flask, Response, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "outputs" / "uploads"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
IMAGE_DIR = BASE_DIR / "outputs" / "images"
DEFAULT_WEIGHTS = BASE_DIR / "weights" / "best.pt"

DEFAULT_CONF = 0.5
DEFAULT_IMGSZ = 640
DEFAULT_FRAME_STEP = 1
JPEG_QUALITY = 75
KEYFRAME_IOU = 0.3          # IoU threshold to treat two boxes as the same target
KEYFRAME_MAX = 30           # cap on keyframes embedded in the report
REPORT_CLASSES = (0, 2)     # only 违规车辆(0) and 其他占用(2) go in the report (no 禁停区)
CATEGORY_SECONDS = 5        # parked >= 5s -> 占用 ; < 5s -> 可疑占用
CATEGORY_OK = "占用"
CATEGORY_SUSPECT = "可疑占用"

# Chinese display names for the results panel.
CLASS_NAME_ZH = {
    0: "违规车辆",
    1: "消防通道占用",
    2: "其他占用",
}

app = Flask(__name__)

# --- lightweight inference tuning --------------------------------------
# Reuse one YOLO instance per weights file instead of reloading on every
# /video_feed request (model load alone can cost seconds).
_model_lock = Lock()
_model_cache: dict = {}


def _require_gpu_device():
    """Require CUDA at startup. Refuse to run on CPU."""
    try:
        import torch
    except Exception as exc:
        raise RuntimeError("PyTorch is not installed in the current environment.") from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available in this environment. This web detector is pinned to GPU only. "
            "Install a CUDA-enabled PyTorch build and run it in the yolo environment."
        )
    return 0


DEVICE = _require_gpu_device()
app.secret_key = "safe-fly-local-video-web"

state_lock = Lock()
runtime_state = {
    "video_path": "",
    "weights_path": str(DEFAULT_WEIGHTS),
    "conf": DEFAULT_CONF,
    "imgsz": DEFAULT_IMGSZ,
    "frame_step": DEFAULT_FRAME_STEP,
    "category_seconds": CATEGORY_SECONDS,
    "logs": deque(maxlen=300),
    "results": deque(maxlen=500),
    "current_counts": [],
    "latest_summary": "Waiting for video upload.",
    "report_file": "",
    "is_running": False,
}


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "weights").mkdir(parents=True, exist_ok=True)


def load_model(weights_path: str) -> YOLO:
    if YOLO is None:
        raise RuntimeError("ultralytics is not installed. Run: pip install -r requirements.txt")
    path = Path(weights_path)
    if not path.exists():
        raise FileNotFoundError(f"Model weights not found: {path}")
    key = str(path.resolve())
    with _model_lock:
        model = _model_cache.get(key)
        if model is None:
            model = YOLO(str(path))
            _model_cache[key] = model
    return model


def draw_detections(frame, detections) -> "numpy.ndarray":
    """Redraw previously detected boxes onto a new frame (keeps motion smooth)."""
    for item in detections:
        x1, y1, x2, y2 = item["bbox"]
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        label = f"{item['class_name']} {item['confidence']:.2f}"
        cv2.putText(
            frame,
            label,
            (int(x1), max(int(y1) - 6, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
    return frame


def add_log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    with state_lock:
        runtime_state["logs"].appendleft(f"[{timestamp}] {message}")


def set_summary(message: str) -> None:
    with state_lock:
        runtime_state["latest_summary"] = message


def clear_logs() -> None:
    with state_lock:
        runtime_state["logs"].clear()
        runtime_state["results"].clear()


def append_result(line: str) -> None:
    with state_lock:
        runtime_state["results"].append(line)


def set_current_counts(detections: List[dict]) -> None:
    """Store per-frame per-class counts for all 3 classes (0 when absent)."""
    counter = Counter(item["class_id"] for item in detections)
    counts = [
        {"class_id": cid, "class_name": CLASS_NAME_ZH.get(cid, str(cid)), "count": counter.get(cid, 0)}
        for cid in (0, 1, 2)
    ]
    with state_lock:
        runtime_state["current_counts"] = counts


def mmss(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def cn_counter_summary(counter: Counter) -> str:
    """Chinese per-class summary like '违规车辆*2，禁停区*1'."""
    if not counter:
        return "无"
    parts = [
        f"{CLASS_NAME_ZH.get(cid, str(cid))}*{n}" for cid, n in counter.most_common()
    ]
    return "，".join(parts)


def class_summary(detections: List[dict]) -> str:
    if not detections:
        return "no target"
    counter = Counter(item["class_name"] for item in detections)
    return ", ".join(f"{name}: {count}" for name, count in counter.items())


def class_counts_cn(detections: List[dict]) -> List[dict]:
    """Per-class Chinese counts for the image results panel."""
    counter = Counter(item["class_id"] for item in detections)
    return [
        {"class_name": CLASS_NAME_ZH.get(cid, str(cid)), "count": n}
        for cid, n in counter.most_common()
    ]


def extract_detections(result) -> List[dict]:
    detections: List[dict] = []
    boxes = getattr(result, "boxes", None)
    names = result.names or {}
    if boxes is None:
        return detections

    for box in boxes:
        cls_id = int(box.cls[0]) if getattr(box, "cls", None) is not None else -1
        conf = float(box.conf[0]) if getattr(box, "conf", None) is not None else 0.0
        xyxy = box.xyxy[0].tolist() if getattr(box, "xyxy", None) is not None else [0, 0, 0, 0]
        detections.append(
            {
                "class_id": cls_id,
                "class_name": names.get(cls_id, str(cls_id)),
                "confidence": round(conf, 4),
                "bbox": [round(v, 2) for v in xyxy],
            }
        )
    return detections


@app.post("/detect_image")
def detect_image():
    ensure_dirs()
    image = request.files.get("image")
    weights_path = request.form.get("weights_path", str(DEFAULT_WEIGHTS))
    try:
        conf = float(request.form.get("conf", DEFAULT_CONF))
        imgsz = int(request.form.get("imgsz", DEFAULT_IMGSZ))
    except ValueError:
        return jsonify({"error": "置信度和输入尺寸必须是有效数字。"}), 400

    if not image or not image.filename:
        return jsonify({"error": "请先选择图片。"}), 400

    suffix = Path(image.filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "仅支持 JPG、PNG、BMP 或 WEBP 图片。"}), 400

    image_path = IMAGE_DIR / f"input_{int(time.time() * 1000)}{suffix}"
    result_path = IMAGE_DIR / f"result_{int(time.time() * 1000)}.jpg"
    image.save(image_path)

    try:
        model = load_model(weights_path)
        result = model.predict(source=str(image_path), conf=conf, imgsz=imgsz, verbose=False, device=DEVICE)[0]
        detections = extract_detections(result)
        annotated = result.plot()
        if not cv2.imwrite(str(result_path), annotated):
            raise RuntimeError("检测结果图片保存失败。")
    except Exception as exc:
        return jsonify({"error": f"图片检测失败：{exc}"}), 500

    add_log(f"Image detected: {image.filename} | {class_summary(detections)}")
    set_current_counts(detections)
    return jsonify(
        {
            "result_url": url_for("media", kind="images", filename=result_path.name),
            "detections": detections,
            "summary": class_summary(detections),
            "class_counts": class_counts_cn(detections),
            "current_counts": list(runtime_state["current_counts"]),
        }
    )


def box_iou(a, b) -> float:
    """IoU between two boxes in [x1, y1, x2, y2] form."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def is_same_target(det: dict, captured: List[dict], iou_thr: float = KEYFRAME_IOU) -> bool:
    """True if this detection overlaps an already-captured target of the same class."""
    for t in captured:
        if t["class_id"] == det["class_id"] and box_iou(det["bbox"], t["bbox"]) >= iou_thr:
            return True
    return False


def _make_report_entry(t: dict, category_seconds: float) -> dict:
    """Categorize a tracked target by how long it stayed: >= threshold -> 占用, else 可疑占用."""
    duration = t["last_second"] - t["first_second"]
    category = CATEGORY_OK if duration >= category_seconds else CATEGORY_SUSPECT
    return {
        "image_b64": t["image_b64"],
        "time": t["time"],
        "category": category,
        "duration": duration,
    }


def generate_html_report(video_name, report_frames) -> str:
    """Build a self-contained HTML report with embedded keyframe images."""
    report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report_path = REPORT_DIR / report_name

    # sort: 占用 first, then 可疑占用
    order = {CATEGORY_OK: 0, CATEGORY_SUSPECT: 1}
    frames_sorted = sorted(report_frames, key=lambda fr: order.get(fr["category"], 2))
    total = Counter(fr["category"] for fr in report_frames)
    total_cn = "，".join(f"{name}*{n}" for name, n in total.items()) or "无"

    cards = ""
    if frames_sorted:
        for fr in frames_sorted:
            cards += f"""
            <figure class="frame">
              <img src="data:image/jpeg;base64,{fr['image_b64']}" alt="关键帧">
              <figcaption><b>{html.escape(fr['time'])}</b>　{html.escape(fr['category'])}（{fr['duration']:.0f}s）</figcaption>
            </figure>"""
    else:
        cards = '<p class="empty">未捕获到检测目标的关键帧。</p>'

    html_text = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>视频检测报告</title>
<style>
  body {{ font-family: 'Segoe UI','Microsoft YaHei',sans-serif; max-width: 1100px; margin: 0 auto; padding: 24px; color: #112236; background: #f3f6fb; }}
  h1 {{ font-size: 24px; }}
  .meta {{ color: #66778c; margin-bottom: 20px; }}
  .summary {{ background: #fff; border: 1px solid #d9e2ee; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; }}
  .summary b {{ color: #1763ff; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
  .frame {{ margin: 0; background: #fff; border: 1px solid #d9e2ee; border-radius: 12px; overflow: hidden; }}
  .frame img {{ width: 100%; display: block; }}
  .frame figcaption {{ padding: 8px 12px; font-size: 14px; color: #24364a; border-top: 1px solid #eef2f7; }}
  .empty {{ color: #66778c; }}
</style></head><body>
  <h1>视频检测报告</h1>
  <p class="meta">视频：{html.escape(video_name)}　·　生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <div class="summary"><b>检测结果：</b>{html.escape(total_cn)}（占用在前，可疑占用在后）</div>
  <h2>关键帧（占用在前，可疑占用在后）</h2>
  <div class="grid">{cards}</div>
</body></html>"""
    report_path.write_text(html_text, encoding="utf-8")

    with state_lock:
        runtime_state["report_file"] = report_name
    return report_name


def save_report(video_name, report_frames) -> str:
    """Alias for the HTML report generator (kept for compatibility)."""
    return generate_html_report(video_name, report_frames)


def generate_video_stream(video_path: str, weights_path: str, conf: float, imgsz: int, frame_step: int, category_seconds: float = CATEGORY_SECONDS):
    frame_logs: List[str] = []
    report_frames: List[dict] = []  # report entries: 占用/可疑占用 keyframes
    # Persistence tracking: match boxes across frames by IoU to measure how long
    # a target stays put. Only 违规车辆(0)/其他占用(2) are reported; each is
    # categorized by parked duration: >= CATEGORY_SECONDS -> 占用, else 可疑占用.
    tracked: dict = {}
    next_track_id = 0
    captured_count = 0

    try:
        model = load_model(weights_path)
    except Exception as exc:
        add_log(f"Model load failed: {exc}")
        set_summary("Model load failed.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        add_log("Video open failed. Check video format.")
        set_summary("Video open failed.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_index = 0
    last_detections = None
    log_every_n_frames = max(1, int(fps // 2))

    # rolling FPS measurement
    proc_count = 0
    proc_start = time.time()
    fps_str = "?"

    with state_lock:
        runtime_state["is_running"] = True
        runtime_state["report_file"] = ""

    add_log(f"Start detection. conf={conf}, imgsz={imgsz}, frame_step={frame_step}, device={DEVICE}")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_index += 1
        should_detect = frame_index % max(1, frame_step) == 0 or last_detections is None

        if should_detect:
            results = model.predict(source=frame, conf=conf, imgsz=imgsz, verbose=False, device=DEVICE)
            result = results[0]
            detections = extract_detections(result)
            annotated = result.plot()
            last_detections = detections

            current_second = frame_index / fps
            # Live per-frame counts: always update the fixed 3-category display.
            set_current_counts(detections)

            # --- persistence tracking (only 违规车辆/其他占用 matter for the report) ---
            report_dets = [d for d in detections if d["class_id"] in REPORT_CLASSES]

            # match each detection to a same-class, overlapping tracked object
            matched_ids = set()
            for d in report_dets:
                best_id, best_iou = None, -1.0
                for tid, t in tracked.items():
                    if tid in matched_ids or t["class_id"] != d["class_id"]:
                        continue
                    iou = box_iou(d["bbox"], t["bbox"])
                    if iou >= KEYFRAME_IOU and iou > best_iou:
                        best_iou, best_id = iou, tid
                if best_id is not None:
                    tracked[best_id]["bbox"] = d["bbox"]
                    tracked[best_id]["last_second"] = current_second
                    matched_ids.add(best_id)
                else:
                    # new target: capture its first-seen keyframe
                    keyframe_b64 = None
                    if captured_count < KEYFRAME_MAX:
                        ok_enc, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                        if ok_enc:
                            keyframe_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
                            captured_count += 1
                    tracked[next_track_id] = {
                        "class_id": d["class_id"],
                        "bbox": d["bbox"],
                        "first_second": current_second,
                        "last_second": current_second,
                        "image_b64": keyframe_b64,
                        "time": mmss(current_second),
                    }
                    matched_ids.add(next_track_id)
                    next_track_id += 1

            # finalize + prune tracks that have left the zone (absent >= prune_after)
            prune_after = max(category_seconds * 3, 15)
            gone = [
                tid
                for tid, t in tracked.items()
                if current_second - t["last_second"] >= prune_after
            ]
            for tid in gone:
                t = tracked.pop(tid)
                if t["image_b64"] is not None and len(report_frames) < KEYFRAME_MAX:
                    report_frames.append(_make_report_entry(t, category_seconds))

            if frame_index % log_every_n_frames == 0:
                summary = class_summary(detections)
                log_line = f"{current_second:.1f}s: {summary}"
                add_log(log_line)
                frame_logs.append(log_line)
                set_summary(log_line)
        else:
            # Redraw last boxes on the live frame so motion stays smooth and
            # boxes don't freeze/stutter like they did with the stale frame.
            if last_detections:
                annotated = draw_detections(frame.copy(), last_detections)
            else:
                annotated = frame

        # report actual processing throughput ~ every 10 frames
        proc_count += 1
        now = time.time()
        if proc_count >= 10:
            elapsed = now - proc_start
            if elapsed > 0:
                fps_now = proc_count / elapsed
                fps_str = f"{fps_now:.1f}"
                add_log(f"Processing FPS: {fps_str} (imgsz={imgsz}, frame_step={frame_step})")
            proc_start = now
            proc_count = 0

        success, buffer = cv2.imencode(
            ".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )
        if success:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"

        time.sleep(max(0.001, min(0.04, 1 / fps)))

    cap.release()
    # finalize any tracks still active when the video ends
    for t in tracked.values():
        if t["image_b64"] is not None and len(report_frames) < KEYFRAME_MAX:
            report_frames.append(_make_report_entry(t, category_seconds))
    report_name = save_report(Path(video_path).name, report_frames)
    add_log(f"Detection finished. Avg FPS ~ {fps_str}. Report: {report_name}")
    set_summary("Detection finished.")
    with state_lock:
        runtime_state["is_running"] = False


@app.get("/")
def index():
    ensure_dirs()
    with state_lock:
        video_path = runtime_state["video_path"]
        status = runtime_state["latest_summary"]
        report_file = runtime_state["report_file"]
        conf = runtime_state["conf"]
        imgsz = runtime_state["imgsz"]
        frame_step = runtime_state["frame_step"]
        category_seconds = runtime_state["category_seconds"]
    return render_template(
        "index.html",
        default_weights=str(DEFAULT_WEIGHTS).replace("\\", "/"),
        default_conf=conf,
        default_imgsz=imgsz,
        default_frame_step=frame_step,
        default_category_seconds=category_seconds,
        video_ready=bool(video_path),
        status=status,
        report_file=report_file,
    )


@app.post("/upload")
def upload_video():
    ensure_dirs()
    video = request.files.get("video")
    weights_path = request.form.get("weights_path", str(DEFAULT_WEIGHTS))
    try:
        conf = float(request.form.get("conf", DEFAULT_CONF))
        imgsz = int(request.form.get("imgsz", DEFAULT_IMGSZ))
        frame_step = int(request.form.get("frame_step", DEFAULT_FRAME_STEP))
        category_seconds = float(request.form.get("category_seconds", CATEGORY_SECONDS))
    except ValueError:
        set_summary("参数必须是有效数字。")
        return redirect(url_for("index"))

    if not video or not video.filename:
        set_summary("Please choose a video file.")
        return redirect(url_for("index"))

    suffix = Path(video.filename).suffix or ".mp4"
    video_path = UPLOAD_DIR / f"uploaded_video{suffix}"
    video.save(video_path)

    clear_logs()
    add_log(f"Uploaded video: {video.filename}")
    add_log(f"Settings: conf={conf}, imgsz={imgsz}, frame_step={frame_step}, 占用判定={category_seconds}s")
    set_summary("Video uploaded. Click start detection.")
    with state_lock:
        runtime_state["video_path"] = str(video_path)
        runtime_state["weights_path"] = weights_path
        runtime_state["conf"] = conf
        runtime_state["imgsz"] = imgsz
        runtime_state["frame_step"] = frame_step
        runtime_state["category_seconds"] = category_seconds
        runtime_state["report_file"] = ""

    return redirect(url_for("index"))


@app.get("/video_feed")
def video_feed():
    with state_lock:
        video_path = runtime_state["video_path"]
        weights_path = runtime_state["weights_path"]
        conf = runtime_state["conf"]
        imgsz = runtime_state["imgsz"]
        frame_step = runtime_state["frame_step"]
        category_seconds = runtime_state["category_seconds"]

    if not video_path:
        return ("Please upload a video first.", 400)

    return Response(
        generate_video_stream(video_path, weights_path, conf, imgsz, frame_step, category_seconds),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/logs")
def logs():
    with state_lock:
        payload = {
            "logs": list(runtime_state["logs"]),
            "results": list(runtime_state["results"]),
            "current_counts": list(runtime_state["current_counts"]),
            "summary": runtime_state["latest_summary"],
            "report_file": runtime_state["report_file"],
            "is_running": runtime_state["is_running"],
        }
    return Response(json.dumps(payload, ensure_ascii=False), mimetype="application/json")


@app.get("/download/<path:filename>")
def download_report(filename: str):
    path = REPORT_DIR / filename
    if not path.exists():
        return ("Report file not found.", 404)
    return send_file(path, as_attachment=True)


@app.get("/media/<path:kind>/<path:filename>")
def media(kind: str, filename: str):
    root_map = {"uploads": UPLOAD_DIR, "reports": REPORT_DIR, "images": IMAGE_DIR}
    root = root_map.get(kind)
    if root is None:
        return ("File type not found.", 404)
    return send_from_directory(root, filename)


if __name__ == "__main__":
    ensure_dirs()
    print(f"[Safe Fly] Inference device: GPU (device={DEVICE})")
    print(f"[Safe Fly] Starting server at http://127.0.0.1:7860")
    app.run(host="0.0.0.0", port=7860, debug=True, threaded=True)
