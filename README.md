# AI Roughcut

本项目是一个通用的访谈视频自动粗剪流水线。它不负责最终内容取舍，只处理机械环节：统一素材格式、转写、检测长空白、标出口头禅候选、生成 AI 判断任务、合并剪辑清单、输出粗剪视频、字幕和人工复查报告。

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
│   ├── ai/
│   ├── cuts/
│   └── clips/
├── output/
│   ├── rough_cut.mp4
│   ├── final_clean.mp4
│   ├── final_burned.mp4
│   ├── subtitle.srt
│   ├── subtitle.ass
│   ├── review_report.html
│   └── handoff/
│       ├── timeline.fcpxml
│       ├── edit_decisions.csv
│       └── import_notes.md
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

### 4. 配置 AI 模型，可选

只有传入 `--ai` 时才需要配置 OpenAI-compatible API。默认使用 OpenAI 官方接口，也可以通过 `AI_BASE_URL` 指向其他兼容 OpenAI Chat Completions 格式的服务：

```bash
export AI_API_KEY="你的 key"
export AI_BASE_URL="https://api.openai.com/v1"
export AI_MODEL="gpt-4.1-mini"
```

使用第三方兼容服务时，替换 `AI_BASE_URL` 和 `AI_MODEL` 即可：

```bash
export AI_API_KEY="你的服务商 key"
export AI_BASE_URL="https://your-provider.example/v1"
export AI_MODEL="provider-model-name"
```

模型名以对应服务商控制台实际可用模型为准。

## 运行

### 1. 放入素材

把待处理视频放到 `input/` 目录，例如：

```text
input/interview_001.mp4
```

### 2. 完整粗剪

调用 OpenAI-compatible API 做删除判断，并在粗剪后重跑 WhisperX 生成字幕：

```bash
python roughcut.py input/demo.MOV --ai --subtitle --project-dir .
```

> 将 `input/demo.MOV` 替换为你的实际素材路径即可。

完成后重点查看：

- `output/rough_cut.mp4`: 自动粗剪版。
- `output/final_clean.mp4`: 不烧字幕版本。
- `output/final_burned.mp4`: 烧字幕版本。
- `output/review_report.html`: 人工复查表。
- `work/cuts/cut_list.json`: 可复查的剪辑清单。

### 3. 不调用 AI

如果还没有配置 API key，可以先用本地保守规则运行。本地规则会自动压缩明显长空白，口头禅候选默认进入复查：

```bash
python roughcut.py input/demo.MOV --project-dir .
```

### 4. 只生成清单，不渲染视频

调试转写、候选检测或 AI 判断时，可以先不生成粗剪视频：

```bash
python roughcut.py input/demo.MOV --no-render --project-dir .
```

### 5. 生成 Auto-Editor 参考版

如果安装了 Auto-Editor，可以额外生成一个快速去空白预览版：

```bash
python roughcut.py input/demo.MOV --autoeditor-preview --project-dir .
```

输出位置：`work/01_autoeditor_preview.mp4`。

### 6. 查看命令帮助

```bash
python roughcut.py --help
```

## 输出

- `work/candidates/silence_candidates.json`: 长空白候选。
- `work/candidates/filler_candidates.json`: 口头禅候选。
- `work/ai/ai_task_001.json`: 交给 AI 模型的任务 JSON。
- `work/ai/ai_result_001.json`: AI 模型或本地保守规则的结果。
- `work/cuts/cut_list.json`: 最终可执行剪辑清单。
- `work/cuts/review_items.csv`: 人工复查 CSV。
- `output/review_report.html`: 人工复查网页。
- `output/rough_cut.mp4`: 自动粗剪版。
- `output/final_clean.mp4`: 不烧字幕成片。
- `output/final_burned.mp4`: 烧字幕成片。
- `output/subtitle.srt` / `output/subtitle.ass`: 平台字幕和样式字幕。
- `output/<素材名>/handoff/timeline.fcpxml`: 可尝试导入剪映或 CapCut 桌面版的单轨时间线交换文件。
- `output/<素材名>/handoff/edit_decisions.csv`: 保留和删除片段的源时间码、时间线时间码和删除原因。
- `output/<素材名>/handoff/import_notes.md`: 导入建议和 XML 不兼容时的兜底流程。

### 剪映 / CapCut 后续精剪

每次生成 `cut_list.json` 后，项目会额外写入 `output/<素材名>/handoff/`：

- `timeline.fcpxml`: 基于保留片段生成的单轨时间线，可优先尝试导入支持 FCPXML/XML 的剪映或 CapCut 桌面版。
- `edit_decisions.csv`: 保留和删除片段的源时间码、时间线时间码和删除原因。
- `import_notes.md`: 导入建议和 XML 不兼容时的兜底流程。

如果当前剪映版本不能导入 XML，可以直接导入 `rough_cut.mp4` 或 `final_clean.mp4`，再参考 `edit_decisions.csv`、`review_report.html` 和可选的 `subtitle.srt` 继续精剪。

## 当前保守规则

- 0.8 秒以内停顿忽略。
- 0.8-1.5 秒停顿只标记。
- 1.5 秒以上停顿建议压缩。
- 3 秒以上停顿压缩后默认保留 0.6 秒。
- AI 模型或本地规则置信度低于 `0.85` 不自动执行，进入复查。
- 两个删除片段距离小于 `0.3` 秒会合并。
- 删除点前后默认保留 `0.15` 秒余量。

## 测试

```bash
python -m pytest
```

测试覆盖纯逻辑部分：空白段分类、WhisperX 词级口头禅候选、AI 决策合并、keep interval 生成。
