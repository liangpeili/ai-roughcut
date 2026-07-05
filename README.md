# AI Roughcut

本项目是一个通用的访谈视频自动粗剪流水线。它不负责最终内容取舍，只处理机械环节：统一素材格式、转写、检测长空白、标出口头禅候选、生成 Kimi 判断任务、合并剪辑清单、输出粗剪视频、字幕和人工复查报告。

默认策略偏保守，适合纪实访谈、街采、口述访谈、课程访谈等需要保留真实语气和人物状态的素材：被访者的犹豫、沉默、笑声、方言语气词默认进入复查或保留，不做激进自动删除。

## 目录

```text
ai_roughcut/
├── input/
├── work/
│   ├── 00_normalized.mp4
│   ├── audio.wav
│   ├── transcript/
│   ├── candidates/
│   ├── kimi/
│   ├── cuts/
│   └── clips/
├── output/
│   ├── rough_cut.mp4
│   ├── final_clean.mp4
│   ├── final_burned.mp4
│   ├── subtitle.srt
│   ├── subtitle.ass
│   └── review_report.html
├── src/ai_roughcut/
├── tests/
└── roughcut.py
```

## 安装

### 1. 获取代码

```bash
git clone git@github.com:liangpeili/ai-roughcut.git
cd ai-roughcut
```

如果已经在本地有这个目录，直接进入项目目录即可：

```bash
cd /path/to/ai-roughcut
```

### 2. 创建 Python 环境

建议使用 Python 3.10 或更高版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 3. 安装外部命令

本项目通过命令行调用 `ffmpeg`、`ffprobe` 和 `whisperx`。先确认它们可用：

```bash
ffmpeg -version
ffprobe -version
whisperx --help
```

如果 `ffmpeg` 不存在，请先安装 FFmpeg。macOS 可以使用 Homebrew：

```bash
brew install ffmpeg
```

Ubuntu/Debian 可以使用 apt：

```bash
sudo apt update
sudo apt install ffmpeg
```

WhisperX 需要按你的 CPU/GPU 环境单独安装。本项目不固定 WhisperX 的安装方式，只要求安装后能运行 `whisperx` 命令。

Auto-Editor 是可选依赖，只在使用 `--autoeditor-preview` 时需要：

```bash
auto-editor --help
```

### 4. 配置 Kimi，可选

只有传入 `--kimi` 时才需要配置 Moonshot/Kimi API key：

```bash
export MOONSHOT_API_KEY="你的 key"
export KIMI_MODEL="kimi-latest"
```

模型名以你的 Moonshot 控制台实际可用模型为准。

## 运行

### 1. 放入素材

把待处理视频放到 `input/` 目录，例如：

```text
input/interview_001.mp4
```

### 2. 完整粗剪

调用 Kimi 做删除判断，并在粗剪后重跑 WhisperX 生成字幕：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --kimi \
  --subtitle \
  --project-dir .
```

完成后重点查看：

- `output/rough_cut.mp4`: 自动粗剪版。
- `output/final_clean.mp4`: 不烧字幕版本。
- `output/final_burned.mp4`: 烧字幕版本。
- `output/review_report.html`: 人工复查表。
- `work/cuts/cut_list.json`: 可复查的剪辑清单。

### 3. 不调用 Kimi

如果还没有配置 API key，可以先用本地保守规则运行。本地规则会自动压缩明显长空白，口头禅候选默认进入复查：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --project-dir .
```

### 4. 只生成清单，不渲染视频

调试转写、候选检测或 Kimi 判断时，可以先不生成粗剪视频：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --no-render \
  --project-dir .
```

### 5. 生成 Auto-Editor 参考版

如果安装了 Auto-Editor，可以额外生成一个快速去空白预览版：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --autoeditor-preview \
  --project-dir .
```

输出位置：`work/01_autoeditor_preview.mp4`。

### 6. 查看命令帮助

```bash
python roughcut.py --help
```

## 输出

- `work/candidates/silence_candidates.json`: 长空白候选。
- `work/candidates/filler_candidates.json`: 口头禅候选。
- `work/kimi/kimi_task_001.json`: 交给 Kimi 的任务 JSON。
- `work/kimi/kimi_result_001.json`: Kimi 或本地保守规则的结果。
- `work/cuts/cut_list.json`: 最终可执行剪辑清单。
- `work/cuts/review_items.csv`: 人工复查 CSV。
- `output/review_report.html`: 人工复查网页。
- `output/rough_cut.mp4`: 自动粗剪版。
- `output/final_clean.mp4`: 不烧字幕成片。
- `output/final_burned.mp4`: 烧字幕成片。
- `output/subtitle.srt` / `output/subtitle.ass`: 平台字幕和样式字幕。

## 当前保守规则

- 0.8 秒以内停顿忽略。
- 0.8-1.5 秒停顿只标记。
- 1.5 秒以上停顿建议压缩。
- 3 秒以上停顿压缩后默认保留 0.6 秒。
- Kimi 或本地规则置信度低于 `0.85` 不自动执行，进入复查。
- 两个删除片段距离小于 `0.3` 秒会合并。
- 删除点前后默认保留 `0.15` 秒余量。

## 测试

```bash
python -m pytest
```

测试覆盖纯逻辑部分：空白段分类、WhisperX 词级口头禅候选、Kimi 决策合并、keep interval 生成。
