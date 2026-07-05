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

## 外部依赖

先确认这些命令可用：

```bash
ffmpeg -version
ffprobe -version
whisperx --help
```

可选：

```bash
auto-editor --help
```

Kimi 调用需要环境变量：

```bash
export MOONSHOT_API_KEY="你的 key"
export KIMI_MODEL="kimi-latest"
```

模型名以你的 Moonshot 控制台实际可用模型为准。

## 安装

```bash
cd /home/ubuntu/summer-holiday/ai_roughcut
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

WhisperX 本身可能需要按你的 CUDA/CPU 环境单独安装；本项目通过 `whisperx` 命令调用它。

## 使用

把素材放入 `input/` 后运行：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --kimi \
  --subtitle \
  --project-dir .
```

不调用 Kimi，只用本地保守规则生成候选、剪辑清单和复查表：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --project-dir .
```

只生成清单和报告，不渲染视频：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --no-render \
  --project-dir .
```

同时生成 Auto-Editor 参考版：

```bash
python roughcut.py input/interview_001.mp4 \
  --profile default \
  --autoeditor-preview \
  --project-dir .
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
