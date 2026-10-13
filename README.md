# article2mp4

把一篇 Markdown 文章转成带 AI 语音旁白、Manim 动画讲解的短视频（9:16 与 16:9 双版）。

## 安装

```bash
# 1) 准备 Python 环境（已有 manim 0.22 + ffmpeg 的 conda 环境即可）
.env-mamba/env/bin/python -m ensurepip --upgrade
.env-mamba/env/bin/python -m pip install -r requirements.txt

# 2) 配置（唯一需要改的地方，仅 3 行）
cp .env.example .env
# 编辑 .env：LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

## 使用

```bash
.env-mamba/env/bin/python -m video_agent make articles/my_article.md
```

产物在 `output/my_article/`：`my_article_916.mp4`（竖版）与 `my_article_169.mp4`（横版）。

可选开关：`--aspect 916|169`、`--max-seconds 90`、`--voice zh-CN-XiaoxiaoNeural`、
`--subtitle`、`--voiceover-only`。

## 工作原理

文章 →（LLM）口播稿 →（LLM）分镜 JSON →（edge-tts）逐句配音 → 时长对齐 →
（Manim 12 型模板）渲染 →（ffmpeg）合成。详见 `docs/superpowers/specs/`。
