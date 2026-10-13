# article2mp4 — 文章转讲解视频流水线 · 设计文档

- 日期：2026-10-13
- 状态：设计已逐节确认，待用户复核本文件
- 目标仓库：`git@6eanut:6eanut/article2mp4.git`

---

## 1. 目标与定位

把一篇 Markdown 文章，自动转成一条带 AI 语音旁白、数据/动画演示风格的讲解视频。

**工具形态（硬性契约）：**

- 输入：一个 Markdown 文件
- 输出：一个（或两个）MP4
- 用户唯一需要配置的：`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 三项
- 一次性命令跑通，不经过任何人工对话环节
- 独立仓库，克隆即可用；用户的文章与产物不进仓库

**内容形态（来自早期需求）：**

- 同时产出 9:16 竖版（小红书/抖音短视频）与 16:9 横版（公众号/哔哩哔哩中视频）
- 纯文字输入：旁白、画面、配乐均由工具生成/内置
- AI 语音旁白，默认中文女声
- 数据/动画演示风格（知识讲解向）
- 可复用工具，而非一次性脚本

**质量原则（用户明确授权）：** 凡是"实现细节 vs 质量"冲突处，一律偏向质量。成本、速度让位于成片质量。

---

## 2. 引擎选型：Manim

- 选 Manim（Python）作为唯一渲染引擎。
- 理由：数学/图表/文字动画的渲染质量天花板最高；纯 CPU 逐帧确定性渲染，**同代码同输入 100% 可复现**，是批量出片最需要的性质；中文可通过显式字体（`Noto Sans SC`）正确渲染，已由 CS329 样片验证。
- 备选 Remotion（React/TS）保留为将来可能性，本期不做。营销/UI 风格若成为主需求，再评估。

**依赖：** Manim Community ≈0.22.0、ffmpeg、edge-tts、openai（兼容客户端）。

> 已知坑：Manim 0.22 **不导出** `CheckMark`，需自绘勾。CJK 必须显式指定字体，否则中文渲染为方框（tofu）。

---

## 3. 流水线骨架（六步）

```
article.md
   │
   ▼
① 口播稿生成      LLM 调用 #1
   文章 → 口播稿，按"句子/意群"切 N 段
   产出 narration.json   [ {id, text}, ... ]
   │
   ▼
② 分镜生成        LLM 调用 #2
   输入：口播稿 + 可用模板清单
   产出 scene_spec.json  [ {id, narration_id, type, props}, ... ]
   含 schema 校验 / 重试 / 兜底
   │
   ▼
③ 语音合成        edge-tts（不需要 key）
   逐句合成 mp3 → ffprobe 读每句真实时长
   产出 audio/001.mp3… + durations.json
   │
   ▼
④ 时长对齐        纯 Python，不调用模型
   把每句时长写回 scene_spec → 每镜得到目标秒数
   产出 scene_spec.timed.json
   │
   ▼
⑤ Manim 渲染      按 type 分派到模板库
   每个模板"时长可参数化"，内部把动画时间与停留时间分配到目标秒数
   产出：无声 9:16 与 16:9 两条无声视频
   │
   ▼
⑥ 合成            ffmpeg
   无声画面 + 逐句旁白拼接 + 内置 BGM（+ 可选字幕）
   产出 output/<名字>/<名字>_916.mp4 与 _169.mp4
```

**边界：模型只出现在 ① ② 两步。** 从 ③ 起全部为确定性计算，可复现、不花钱。

**关键设计点：**

- 第 ① 步的"切段"决定镜头数：旁白按句/意群切 N 段，每段将来即一个镜头。"分几个镜头"在写口播稿那刻已定——这是"旁白驱动"的直接后果。
- 第 ④ 步把"每句念了多久"这一唯一真值翻译成"每镜停多久"，是声画同步的落点，且不调用任何模型。

---

## 4. 选题决策：旁白驱动（Narration-driven）

已确认采用**方案 A**：先生成旁白音频、取得每句时长，再用它驱动镜头时长与切换点。声音是唯一主时钟，画面跟随。

（一度考虑的方案 B——固定画面时长、拉伸/裁剪旁白——已否决，因为错半拍的观感在知识讲解里极易露馅。）

---

## 5. 镜头模板库（12 型）

模型不能自创镜头，只能从以下 12 型中挑。这批类型由 CS329 样片归纳而来，每个模板要求**时长可参数化**（能吃一个"秒数"，内部据此分配入场与停留）。

| # | type | 用途 | props |
|---|------|------|-------|
| 1 | `title` | 开场标题镜 | `{title, subtitle}` |
| 2 | `section` | 章节过渡镜 | `{index, heading}` |
| 3 | `bullets` | 要点逐条浮现（**最常用**） | `{heading, items[]}` |
| 4 | `steps` | 流程/步骤条（可标进度） | `{heading, steps[], done_index}` |
| 5 | `cycle` | 3~4 节点循环图（反复/闭环） | `{heading, nodes[]}` |
| 6 | `tree` | 树状图，可高亮路径（搜索/规划） | `{heading, root, children[][], highlight_path}` |
| 7 | `compare` | 双栏对比（A vs B） | `{heading, left:{title,items[]}, right:{title,items[]}}` |
| 8 | `grid` | 候选网格，可勾可叉（多试挑选） | `{heading, cells:[{label, mark}]}` |
| 9 | `metric` | 大数字滚动 + 柱/折图（砸数据） | `{heading, value, unit, label, chart?}` |
| 10 | `quote` | 金句放大镜（钉观点） | `{text, source?}` |
| 11 | `summary` | 关键词收束镜 | `{heading, items[]}` |
| 12 | `closing` | 结尾镜 + 可选署名 | `{text, handle?}` |

**保底三件套：** `title` + `bullets` + `closing`。任何文章至少能靠这三型拼出一条完整片。降级时退到这三型，**保证永远出得了片**。

**视觉风格：** 纯文字 + 色块 + 几何图形（CS329 风格）。本期**不做自动配图/图标**——不吃图、不依赖图库、不侵权，风格已足够高级。

**配色/字体设计令牌（沿用 CS329 样片）：**
`FONT="Noto Sans SC"`、`BG="#0F172A"`、`PANEL="#1E293B"`、`FG="#F8FAFC"`、`MUTED="#94A3B8"`、`DIM="#475569"`、`RED="#F87171"`、
`ACCENT=["#38BDF8","#818CF8","#A78BFA","#F472B6","#34D399"]`。

---

## 6. 分镜 JSON 契约（系统的唯一接口）

模型与模板之间仅靠此形状对接。**这是整个系统最重要的合同。**

### 6.1 中间产物一：`narration.json`（第 ① 步）

```json
{
  "title": "LLM 推理与智能体：从测试时计算到规划",
  "segments": [
    { "id": 0, "text": "如果让模型多做几次尝试，它的推理能力会明显提升。" },
    { "id": 1, "text": "这就是我们说的测试时计算。" }
  ]
}
```

### 6.2 中间产物二：`scene_spec.json`（第 ② 步）

```json
{
  "title": "LLM 推理与智能体",
  "aspects": ["916", "169"],
  "scenes": [
    { "id": 0, "type": "title", "narration_id": 0,
      "props": { "title": "LLM 推理与智能体", "subtitle": "从测试时计算到规划" } },
    { "id": 1, "type": "quote", "narration_id": 1,
      "props": { "text": "测试时计算：多试几次，答案就更准" } }
  ]
}
```

### 6.3 三条铁律

1. **`scenes` 与 `segments` 严格 1:1**：`scenes[i].narration_id == i`，镜头数 = 旁白段数。声画同步由数据结构保证，不可能错拍。（开场镜也占一个 id、配一句旁白，不设游离镜头。）
2. **`type` 必须取自 12 型之一**：否则校验失败、触发重试。
3. **`props` 形状由 `type` 决定**：每型有固定 props 定义；多写字段忽略，缺必填字段则校验失败。

**`narration_id` 显式存在**（虽恒等于 id）：第 ④ 步靠它去 `durations.json` 查时长；将来若要放开"两句话共用一个镜头"，只需放松此约束，其余不动。

---

## 7. 时长对齐机制（旁白驱动的引擎室）

**核心公式：** `镜头 i 时长 = 旁白 i 真实音频时长 + gap`（gap = 镜头间呼吸停顿，默认 0.4s）。

```
旁白段         ①            ②           ③
音频时长     a₀=5.2s      a₁=1.6s     a₂=4.0s
镜头时长     d₀=a₀+0.4    d₁=a₁+0.4   d₂=a₂+0.4
画面        [title 5.6s][quote 2.0s][grid 4.4s]
声音                 [旁白①][旁白②][旁白③]
BGM         [━━━━━ 贯穿全片、循环 ━━━━━]
```

**模板如何吃掉一个秒数：** 每个模板声明两段时间——

```
        d = 5.6s
   ├──────────────────────────┤
   ├─ entrance ─┤├──── hold ────┤
     入场动画      停住不动
     （有最短时长）
```

- 分配规则：`hold = d − entrance`。d 长则多停；d 短则把入场压到最短。
- 极端兜底：若 d 短于"最短入场"，则加速播放入场（压缩 `run_time`），实在不行轻微延长本镜——**宁可画面多停半秒，也不让动画崩**。

**旁白驱动的最直观体现：** 观众看到"画面停了一会儿"，是因为"这句话念了 5 秒"，而非"动画被写死了多停 3 秒"。

### 字幕

- **做一个可开关的内嵌字幕**，默认**关**，`--subtitle` 打开。
- 字幕内容 = 该镜对应的那句旁白，随镜头同步出现。
- 作为**模板的通用能力**（所有 12 型共享），不是某一型专属。
- 动机：竖版短视频大量静音刷，屏上有字几乎是标配。

### 语速

- **不提供速率参数**。默认自然语速，不做 `--rate` 开关。（用户明确：语速不用调。）

---

## 8. 仓库结构与使用形态

```
article2mp4/                     ← 仓库根（git@6eanut:6eanut/article2mp4.git）
├─ README.md                       ← 安装 + 3 行配置说明 + 一条命令示例
├─ requirements.txt                ← manim / edge-tts / openai / …
├─ .env.example                    ← 提交（3 个空值模板）
├─ .gitignore                      ← 挡 .env / articles/ / output/ / media/ / __pycache__
├─ video_agent/                    ← 工具本体
│   ├─ cli.py                       ← 命令行入口
│   ├─ llm.py                       ← OpenAI 兼容客户端（唯一读 .env 之处）
│   ├─ script_gen.py                ← ① 文章→口播稿
│   ├─ scene_gen.py                 ← ② 口播稿→分镜JSON（校验/重试/兜底）
│   ├─ schema.py                    ← 分镜 JSON 的合法形状定义
│   ├─ tts.py                       ← ③ edge-tts 逐句配音
│   ├─ timing.py                    ← ④ 时长对齐
│   ├─ render.py                    ← ⑤ 按 type 分派 + 调 Manim
│   ├─ compose.py                   ← ⑥ ffmpeg 合成
│   ├─ templates/                   ← 12 个模板，一型一文件
│   │   ├─ title.py  section.py  bullets.py  steps.py
│   │   ├─ cycle.py  tree.py     compare.py  grid.py
│   │   └─ metric.py quote.py    summary.py  closing.py
│   └─ prompts/                     ← ①② 的提示词（可改）
│       ├─ script.md
│       └─ scene.md
├─ assets/bgm/                     ← 内置免版权循环乐（**必须提交**，否则克隆即哑）
├─ articles/   (gitignored)        ← 用户输入区
└─ output/     (gitignored)        ← 出片区
```

**配置 `.env`（唯一配置处，3 行）：**

```
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=deepseek-chat
```

**日常操作（一条命令）：**

```
python -m video_agent make articles/my_article.md
```

可开关：
`--aspect 916`（只出竖版）、`--aspect 169`（只出横版）、`--max-seconds 90`（压时长）、`--voice zh-CN-XiaoxiaoNeural`（换声）、`--subtitle`（开字幕）、`--voiceover-only`（只出口播稿先审词）。

**默认同时出 9:16 与 16:9 两版**；想省时间用 `--aspect` 指定单版。

`scene_spec.json` 里的 `aspects` 字段与命令行的 `--aspect` 若同时存在，**以命令行为准**（CLI 覆盖 JSON）。`--aspect` 只影响本次渲染选择，不写回 JSON。

**输出布局：**

```
output/my_article/
├─ narration.json          ← ① 产物（可读可改）
├─ scene_spec.json         ← ② 产物
├─ scene_spec.timed.json   ← ④ 产物（带上每镜秒数）
├─ audio/001.mp3 …         ← ③ 产物
├─ my_article_916.mp4      ← 竖版
└─ my_article_169.mp4      ← 横版
```

**两条仓库规矩：** `assets/bgm/` 必须进仓库（否则克隆下来是哑巴工具）；`.env`、文章、产物一律 gitignore（密钥与私人内容绝不进库）。附 `.env.example`，clone → 填 3 值 → 给 md → 出片。

**"手改续跑"能力：** 中间产物全部落盘成可读 JSON。对口播不满意 → 直接改 `narration.json` 重跑后半段，不必重新调模型；分镜 JSON 错了 → 改一行重跑。把一次昂贵模型调用变成可反复打磨的文件。

---

## 9. 可靠性与错误处理

**原则：画面出问题就降级继续；声音/内容出问题就停下报错。** 因为画面朴素还能看，没声音/内容错乱就没法看。

| 环节 | 可能失败 | 处理 |
|------|---------|------|
| ① 口播稿 | LLM 超时 / 返回空 | 重试 2 次；仍失败 → 报错停 |
| ② 分镜 JSON | JSON 不合法 / type 不在 12 型内 / props 缺字段 | 带错误信息回问模型一次；仍不行 → 该镜降级 `bullets`；再不行 → 全文降级 `title+bullets+closing`，**保证出片** |
| ③ edge-tts | 某句合成失败 | 重试 2 次；仍失败 → 报错停 |
| ④ 时长对齐 | 音频缺时长 | 用字数估算兜底，继续 |
| ⑤ Manim 渲染 | 单模板抛异常 | 该镜降级为纯文字镜，继续渲其余 |
| ⑥ ffmpeg 合成 | 音画对不上 | 断言总音长 vs 总片长，偏差 > 0.3s 报错 |

**降级链：** `理想模板 → bullets → title+bullets+closing`，是通向"一定能出片"的阶梯。

每一步向 `output/<名字>/` 写日志，出错能一眼看到卡在哪。

---

## 10. 测试策略（只押三件事）

1. **金标准冒烟测试**：仓库内放一篇 ~200 字测试文章，跑完整链，断言产物齐全（两 mp4 存在、时长>0、分辨率正确）。每次改完代码跑它。
2. **JSON 契约测试**：一份合法 `scene_spec.json` + 几份故意写坏的（type 错、props 缺字段），断言"合法能过、坏能被拦"。系统命门，必须锁死。
3. **模板单渲测试**：每个模板吃假数据 + 一个秒数，单独渲一小段不报错。改某模板时只跑它，秒级验证。

**明确不写：** LLM 输出质量测试（主观且依赖外部模型）、ffmpeg 逐帧比对（太重）。

---

## 11. 已确认决策清单

| # | 决策 | 结论 |
|---|------|------|
| 1 | 声画时序 | 旁白驱动（声音先行） |
| 2 | 渲染引擎 | Manim |
| 3 | 内容生成步数 | 两段式 LLM 调用（文章→口播稿→分镜） |
| 4 | 分镜生成护栏 | schema 校验 + 重试 + 兜底 |
| 5 | 输出比例 | 默认同时出 9:16 与 16:9 |
| 6 | 成片时长 | 不硬压，软上限约 6 分钟（`--max-seconds` 可调） |
| 7 | 旁白 | edge-tts，默认中文女声，无速率参数 |
| 8 | 字幕 | 可开关，默认关 |
| 9 | 配乐 | 内置免版权循环乐 |
| 10 | 配置面 | 仅 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` |
| 11 | 仓库 | 独立仓库 article2mp4，工具进库、数据 gitignore |
| 12 | 配图 | 本期不做，纯文字+色块+几何 |
| 13 | 测试 | 只押冒烟 / 契约 / 单模板三件 |

---

## 12. 明确不做（YAGNI）

- Remotion 双引擎分流
- 自动配图/图标/图库接入
- 旁白语速参数
- LLM 输出质量的自动化评测
- "两句话共用一个镜头"的多对一映射
