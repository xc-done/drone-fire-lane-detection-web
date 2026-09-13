const logBox = document.querySelector("#logBox");
const downloadLink = document.querySelector("#downloadLink");
const startDetection = document.querySelector("#startDetection");
const mediaFrame = document.querySelector("#mediaFrame");
const mediaPlaceholder = document.querySelector("#mediaPlaceholder");
const imageForm = document.querySelector("#imageForm");
const videoForm = document.querySelector("#videoForm");
const weightsPath = document.querySelector("#weightsPath");
const resultsList = document.querySelector("#resultsList");
const resultsStatus = document.querySelector("#resultsStatus");

const CLASS_LABELS = { 0: "违规车辆", 1: "消防通道占用", 2: "其他占用" };
const CLASS_IDS = [0, 1, 2];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderLogs(logs) {
  if (!logBox) return;
  if (!logs || logs.length === 0) {
    logBox.innerHTML = '<p class="empty">检测开始后，这里会实时显示运行日志。</p>';
    return;
  }
  logBox.innerHTML = logs
    .map((line) => `<p class="log-line">${escapeHtml(line)}</p>`)
    .join("");
}

// Fixed 3-category live panel: always shows all classes, count updates, 0 when none.
function renderCounts(counts) {
  if (!resultsList) return;
  const map = {};
  (counts || []).forEach((c) => {
    map[c.class_id] = c.count;
  });
  resultsList.innerHTML = CLASS_IDS.map(
    (id) => `
      <div class="result-line">
        <span class="result-text">${escapeHtml(CLASS_LABELS[id])}：${map[id] ?? 0}</span>
      </div>`
  ).join("");
}

function setResultsStatus(text) {
  if (resultsStatus) resultsStatus.textContent = text || "";
}

function startVideoStream() {
  if (!mediaFrame) return;
  mediaFrame.src = `/video_feed?t=${Date.now()}`;
  mediaFrame.style.display = "block";
  if (mediaPlaceholder) mediaPlaceholder.style.display = "none";
}

async function refreshLogs() {
  try {
    const response = await fetch("/logs", { cache: "no-store" });
    const data = await response.json();
    renderLogs(data.logs);
    renderCounts(data.current_counts);
    if (data.summary) setResultsStatus(data.summary);
    if (downloadLink && data.report_file) {
      downloadLink.href = `/download/${encodeURIComponent(data.report_file)}`;
      downloadLink.classList.remove("hidden");
    }
  } catch (error) {
    setResultsStatus("日志刷新失败，请确认服务仍在运行。");
  }
}

if (startDetection) {
  startDetection.addEventListener("click", startVideoStream);
}

if (imageForm) {
  imageForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = document.querySelector("#imageSubmit");
    submit.disabled = true;
    setResultsStatus("正在检测图片，请稍候...");
    try {
      const formData = new FormData(imageForm);
      if (weightsPath) formData.set("weights_path", weightsPath.value);
      const response = await fetch("/detect_image", { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "图片检测失败");
      if (mediaFrame) {
        mediaFrame.src = `${data.result_url}?t=${Date.now()}`;
        mediaFrame.style.display = "block";
      }
      if (mediaPlaceholder) mediaPlaceholder.style.display = "none";
      renderCounts(data.current_counts);
      setResultsStatus(data.detections.length ? "图片检测完成" : "图片检测完成：没有检测到目标。");
    } catch (error) {
      setResultsStatus(error.message);
    } finally {
      submit.disabled = false;
    }
  });
}

// Sync the shared weight path into the video form before it submits normally.
if (videoForm && weightsPath) {
  const videoWeightsPath = document.querySelector("#videoWeightsPath");
  videoForm.addEventListener("submit", () => {
    if (videoWeightsPath) videoWeightsPath.value = weightsPath.value;
  });
}

if (mediaFrame) mediaFrame.style.display = "none";

refreshLogs();
setInterval(refreshLogs, 1000);
