# Drone-Assisted Fire Lane Occupancy Detection Web App

这是一个本地运行的无人机巡检消防通道占用检测网页。它把训练好的 YOLO 模型接入 Flask 应用，支持上传图片和视频，在浏览器中查看检测结果，并为视频检测生成 HTML 报告。

## 项目功能

- 上传图片并查看带检测框的结果图
- 上传无人机巡检视频并进行逐帧检测
- 图片和视频共用同一个检测画面
- 显示检测类别、置信度、日志和当前统计
- 视频检测完成后生成包含关键帧和时间信息的 HTML 报告
- 推理固定使用第 1 张 CUDA GPU（`device=0`）

## 工作流程

```text
无人机采集巡检视频
        ↓
用户在网页上传图片或视频
        ↓
Flask 后端接收文件
        ↓
YOLO 模型进行图片/视频帧检测
        ↓
网页显示检测结果
        ↓
视频检测结束后生成 HTML 报告
```

## 文件结构

```text
drone-fire-lane-detection-web/
├── app.py                 # Flask 后端、模型推理和报告生成
├── run_server.py          # 无调试模式启动脚本
├── requirements.txt       # Python 依赖
├── README.md              # 项目说明
├── templates/
│   └── index.html         # 网页结构
├── static/
│   ├── app.js             # 上传、请求和页面交互
│   └── style.css          # 页面样式
├── weights/
│   └── best.pt            # 训练好的 YOLO 模型权重
└── outputs/
    ├── uploads/           # 上传的视频
    ├── images/            # 上传图片和检测结果图
    └── reports/           # 生成的 HTML 报告
```

## 环境要求

- Windows
- Python 3.10 或更高版本
- NVIDIA GPU
- 已安装 CUDA 驱动
- CUDA 版 PyTorch

本项目在启动时会检查 CUDA。如果当前环境无法使用 CUDA，程序会直接退出，不会自动改用 CPU。

## 推荐启动方式

建议使用已经安装好 PyTorch CUDA 版本的 `yolo` Conda 环境：

```powershell
cd E:\drone-fire-lane-detection-web
C:\Users\Admin\miniconda3\Scripts\conda.exe run -n yolo python run_server.py
```

如果当前 PowerShell 已经可以使用 Conda，也可以：

```powershell
cd E:\drone-fire-lane-detection-web
conda activate yolo
python run_server.py
```

首次使用或依赖不完整时，可以在 `yolo` 环境中安装依赖：

```powershell
conda activate yolo
python -m pip install -r requirements.txt
```

注意：`requirements.txt` 负责安装通用 Python 依赖。PyTorch 是否为 CUDA 版本，需要单独确认，不建议在没有确认版本的情况下随意覆盖当前 PyTorch。

## 打开网页

服务启动后，在浏览器打开：

```text
http://127.0.0.1:7860
```

只有运行网页服务的这台电脑可以通过 `127.0.0.1` 访问。如果要让其他人访问，需要进一步部署到公网服务器，并配置域名、HTTPS、上传限制和模型运行环境。

## 使用图片检测

1. 打开网页。
2. 在图片检测区域选择 JPG、PNG、BMP 或 WEBP 图片。
3. 确认模型权重路径默认为 `E:/drone-fire-lane-detection-web/weights/best.pt`。
4. 点击“开始图片检测”。
5. 结果会显示在页面顶部的统一检测画面中。

## 使用视频检测

1. 在视频上传区域选择视频文件。
2. 点击上传并保存参数。
3. 点击“开始实时检测”。
4. 网页会在统一检测画面中显示带检测框的视频流。
5. 视频处理完成后，报告会保存在 `outputs/reports/`，页面会出现下载链接。

## 主要参数

- `conf`：置信度阈值。数值越高，结果越少但通常更严格；数值越低，可能检测到更多目标，也可能增加误检。
- `imgsz`：模型输入尺寸。尺寸越大，可能有利于小目标识别，但推理速度会降低。
- `frame_step`：视频检测间隔帧。设置为 `1` 表示每一帧都检测；增大它可以提高处理速度，但可能跳过短暂出现的目标。
- `category_seconds`：报告中持续时间分类使用的阈值。

## 常见问题

### 1. 启动时提示 CUDA 不可用

请确认：

- 使用的是 `yolo` 环境，而不是系统 Python；
- PyTorch 是 CUDA 版本；
- NVIDIA 驱动正常；
- `torch.cuda.is_available()` 返回 `True`。

可以运行：

```powershell
C:\Users\Admin\miniconda3\Scripts\conda.exe run -n yolo python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

### 2. 提示找不到模型权重

确认文件存在：

```text
E:\drone-fire-lane-detection-web\weights\best.pt
```

也可以在网页的模型权重路径输入框中填写绝对路径。

### 3. 视频检测画面速度较慢

视频检测是逐帧推理，速度会受到模型大小、输入尺寸、视频分辨率和显卡性能影响。可以先尝试降低 `imgsz`，或者把 `frame_step` 调大。

### 4. 结果与真实场景不一致

模型的效果取决于训练数据。无人机高度、拍摄角度、天气、光照、背景和目标大小发生变化时，检测效果可能下降。网页只负责调用和展示模型，不能替代更丰富的数据采集和模型评估。

## 项目边界

这是一个本地原型系统，主要用于展示无人机视频接入、目标检测、网页展示和报告生成的完整流程。它不是执法系统，也不能完全替代人工复核。正式应用前，还需要更多真实无人机数据、更严格的测试和安全性设计。

## 相关项目

- YOLO 训练项目：原训练代码、数据集和实验结果位于另一个项目目录。
- 项目展示页：英文展示页可以作为单独的静态项目介绍，不与本检测应用混合部署。
