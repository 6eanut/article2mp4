# article2mp4 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把一篇 Markdown 文章自动转成一条带 AI 语音旁白、Manim 动画讲解的两版视频（9:16 与 16:9），用户只需配置 LLM 的 url/key/model 三项。

**Architecture:** 六步确定性流水线——① 文章→口播稿、② 口播稿→分镜 JSON（两步用 LLM）→ ③ edge-tts 逐句配音 → ④ 时长对齐（纯 Python）→ ⑤ 12 型 Manim 模板按时长渲染 → ⑥ ffmpeg 合成音画。模型只出现在 ①②；其后全部可复现。声画同步靠"镜头数 = 旁白段数"的 1:1 数据结构保证。

**Tech Stack:** Python 3.14、Manim Community 0.22.0、ffmpeg 9.0.2、edge-tts、openai（OpenAI 兼容客户端）、pydantic v2、pytest。

## Global Constraints

- 引擎唯一为 **Manim Community 0.22.0**；Manim 0.22 **不导出** `CheckMark`，勾号必须自绘。
- CJK 必须显式 `font="Noto Sans SC"`，否则中文渲染为方框。
- 设计令牌（沿用 CS329 样片，逐字照抄）：
  `FONT="Noto Sans SC"`、`BG="#0F172A"`、`PANEL="#1E293B"`、`FG="#F8FAFC"`、`MUTED="#94A3B8"`、`DIM="#475569"`、`RED="#F87171"`、
  `ACCENT=["#38BDF8","#818CF8","#A78BFA","#F472B6","#34D399"]`。
- 渲染尺寸：**916 = 1080×1920**，**169 = 1920×1080**，帧率 **30fps**。
- 用户配置面**仅** `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`（写在 `.env`）；旁白/渲染**不得**要求任何额外 key。
- 镜头数**严格等于**旁白段数（`scenes[i].narration_id == i`）。
- **画面出错降级继续；声音/内容出错停下报错。**
- 降级链：理想模板 → `bullets` → `title+bullets+closing`（保底三件套）。
- `.env`、`articles/`、`output/`、`media/`、`__pycache__` 一律 **gitignore**；`assets/bgm/` **必须提交**。
- 日期格式：文件名用 `YYYY-MM-DD`；JSON 内无日期字段。
- 环境：解释器 `.env-mamba/env/bin/python`（3.14.8）；`ffmpeg`/`ffprobe` 位于 `.env-mamba/env/bin/`，**运行时需加入 PATH**。
- 全程 **TDD**：先写失败测试（RED）→ 最小实现（GREEN）→ 提交。每完成一任务提交一次。

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `video_agent/config.py` | 读 `.env` 的 3 个值；定义渲染常量与 12 型枚举 |
| `video_agent/schema.py` | pydantic 模型：`Narration` / `SceneSpec` / 各 type 的 props |
| `video_agent/llm.py` | OpenAI 兼容客户端；`chat_json()` 强制 JSON 返回 |
| `video_agent/prompts/script.md` | 第①步系统提示词 |
| `video_agent/prompts/scene.md` | 第②步系统提示词 |
| `video_agent/style.py` | 设计令牌 + 复用图元（`chip/badge/heading/tick/cand_box`）|
| `video_agent/templates/__init__.py` | `TEMPLATES` 注册表 + `render_scene(type, props, duration)` 分派 + `entrance_hold` |
| `video_agent/templates/*.py` | 12 个模板，一型一文件，各导出 `render(props, duration, subtitle=None)` |
| `video_agent/render.py` | 组装整片：按秒分派每个 scene，按 `aspect` 设置分辨率输出 |
| `video_agent/script_gen.py` | 第①步：文章→`Narration`（LLM）|
| `video_agent/scene_gen.py` | 第②步：口播稿→`SceneSpec`（LLM + 校验/重试/兜底）|
| `video_agent/tts.py` | 第③步：逐句 edge-tts + ffprobe 量时长（可注入 synth 以便测试）|
| `video_agent/timing.py` | 第④步：时长对齐（纯函数）|
| `video_agent/compose.py` | 第⑥步：ffmpeg 拼音/叠 BGM/可选字幕 |
| `video_agent/cli.py` | 命令行入口 `python -m video_agent make …` |
| `assets/bgm/track.mp3` | 内置循环配乐 |
| `tests/…` | 三件测试：契约 / 单模板 / 冒烟 |

---

### Task 1: 项目骨架与配置层

**Files:**
- Create: `video_agent/__init__.py`、`video_agent/config.py`
- Create: `.env.example`、`.gitignore`、`requirements.txt`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `video_agent.config.Settings`（字段 `base_url: str`、`api_key: str`、`model: str`）、`load_settings() -> Settings`、`Settings.from_env(env: dict) -> Settings`
- Produces: 常量 `CANVAS = {"916": (1080,1920), "169": (1920,1080)}`、`FPS = 30`、`TEMPLATE_TYPES: list[str]`（12 型）、`FALLBACK_CHAIN`
- Consumes: 无

- [ ] **Step 1: 写失败测试**

`tests/test_config.py`：
```python
import pytest
from video_agent.config import Settings, load_settings, CANVAS, TEMPLATE_TYPES

def test_from_env_reads_three_keys():
    s = Settings.from_env({
        "LLM_BASE_URL": "https://api.deepseek.com/v1",
        "LLM_API_KEY": "sk-abc",
        "LLM_MODEL": "deepseek-chat",
    })
    assert s.base_url == "https://api.deepseek.com/v1"
    assert s.api_key == "sk-abc"
    assert s.model == "deepseek-chat"

def test_from_env_missing_key_raises():
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        Settings.from_env({"LLM_BASE_URL": "x", "LLM_MODEL": "y"})

def test_load_settings_reads_dotenv(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("LLM_BASE_URL=u\nLLM_API_KEY=k\nLLM_MODEL=m\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = load_settings()
    assert (s.base_url, s.api_key, s.model) == ("u", "k", "m")

def test_canvas_and_types():
    assert CANVAS["916"] == (1080, 1920)
    assert CANVAS["169"] == (1920, 1080)
    assert len(TEMPLATE_TYPES) == 12
    assert "bullets" in TEMPLATE_TYPES
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_config.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'video_agent'`）

- [ ] **Step 3: 写最小实现**

先补上包管理器缺的 pip（conda env 无 pip，用 ensurepip）并装依赖。
**注意：本机 pip 默认指向清华镜像且连不通，必须显式走官方源。**
```bash
.env-mamba/env/bin/python -m ensurepip --upgrade
.env-mamba/env/bin/python -m pip install --index-url https://pypi.org/simple \
    pytest pydantic openai edge-tts
```

仓库内需有一个指向父目录 conda 环境的软链，使上述命令可用（`.env-mamba` 在仓库父目录）：
```bash
ln -sfn ../.env-mamba .env-mamba
```
并把该软链加入 `.gitignore`（见下方 `.gitignore` 内容中的 `.env-mamba`）。

`video_agent/__init__.py`：
```python
"""article2mp4 —— 文章转讲解视频流水线。"""
```

`video_agent/config.py`：
```python
from __future__ import annotations
import os
from dataclasses import dataclass

CANVAS = {"916": (1080, 1920), "169": (1920, 1080)}
FPS = 30

TEMPLATE_TYPES = [
    "title", "section", "bullets", "steps", "cycle", "tree",
    "compare", "grid", "metric", "quote", "summary", "closing",
]
FALLBACK_CHAIN = ["bullets", "title", "closing"]


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls, env: dict) -> "Settings":
        missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL") if not env.get(k)]
        if missing:
            raise ValueError(f"缺少配置: {', '.join(missing)}（请在 .env 中设置）")
        return cls(env["LLM_BASE_URL"], env["LLM_API_KEY"], env["LLM_MODEL"])


def load_settings() -> Settings:
    env: dict[str, str] = {}
    path = ".env"
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        env.setdefault(k, os.environ.get(k, ""))
    return Settings.from_env(env)
```

`.env.example`：
```
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=
LLM_MODEL=deepseek-chat
```

`.gitignore`：
```
.env
.env-mamba
articles/
output/
media/
__pycache__/
*.pyc
.pytest_cache/
```

`requirements.txt`：
```
manim==0.22.0
edge-tts
openai
pydantic>=2
pytest
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/__init__.py video_agent/config.py tests/test_config.py .env.example .gitignore requirements.txt
git commit -m "feat: project scaffold and config layer"
```

---

### Task 2: 分镜契约（pydantic schema）

**Files:**
- Create: `video_agent/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: `config.TEMPLATE_TYPES`
- Produces: `Narration(title: str, segments: list[Segment])`，`Segment(id: int, text: str)`
- Produces: `SceneSpec(title: str, aspects: list[str], scenes: list[Scene])`，`Scene(id: int, narration_id: int, type: str, props: dict)`
- Produces: `validate_scene_spec(raw: dict, narration: Narration) -> SceneSpec`（校验：1:1 对应、type 合法、props 形状；失败抛 `ContractError`）
- Produces: `ContractError(Exception)`
- Produces: 每型 props 必填字段表 `PROPS_REQUIRED: dict[str, list[str]]`

- [ ] **Step 1: 写失败测试**

`tests/test_schema.py`：
```python
import pytest
from video_agent.schema import Narration, validate_scene_spec, ContractError

NARR = Narration(title="T", segments=[
    {"id": 0, "text": "第一句"}, {"id": 1, "text": "第二句"},
])

def _spec(scenes):
    return {"title": "T", "aspects": ["916", "169"], "scenes": scenes}

def test_valid_spec_passes():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T", "subtitle": "s"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "金句"}},
    ])
    spec = validate_scene_spec(raw, NARR)
    assert len(spec.scenes) == 2
    assert spec.scenes[1].type == "quote"

def test_unknown_type_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "pie_chart", "props": {}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="pie_chart"):
        validate_scene_spec(raw, NARR)

def test_count_mismatch_rejected():
    raw = _spec([{"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}}])
    with pytest.raises(ContractError, match="数量"):
        validate_scene_spec(raw, NARR)

def test_narration_id_mismatch_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 1, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 0, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="narration_id"):
        validate_scene_spec(raw, NARR)

def test_missing_required_prop_rejected():
    raw = _spec([
        {"id": 0, "narration_id": 0, "type": "title", "props": {"subtitle": "缺title"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "x"}},
    ])
    with pytest.raises(ContractError, match="title"):
        validate_scene_spec(raw, NARR)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_schema.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.schema`）

- [ ] **Step 3: 写最小实现**

`video_agent/schema.py`：
```python
from __future__ import annotations
from pydantic import BaseModel
from .config import TEMPLATE_TYPES


class ContractError(Exception):
    """分镜 JSON 不符合契约。"""


class Segment(BaseModel):
    id: int
    text: str


class Narration(BaseModel):
    title: str
    segments: list[Segment]


class Scene(BaseModel):
    id: int
    narration_id: int
    type: str
    props: dict


class SceneSpec(BaseModel):
    title: str
    aspects: list[str]
    scenes: list[Scene]


PROPS_REQUIRED: dict[str, list[str]] = {
    "title":   ["title"],
    "section": ["index", "heading"],
    "bullets": ["heading", "items"],
    "steps":   ["heading", "steps"],
    "cycle":   ["heading", "nodes"],
    "tree":    ["heading", "root", "children"],
    "compare": ["heading", "left", "right"],
    "grid":    ["heading", "cells"],
    "metric":  ["heading", "value", "label"],
    "quote":   ["text"],
    "summary": ["heading", "items"],
    "closing": ["text"],
}


def validate_scene_spec(raw: dict, narration: Narration) -> SceneSpec:
    spec = SceneSpec(**raw)
    if len(spec.scenes) != len(narration.segments):
        raise ContractError(
            f"镜头数量({len(spec.scenes)})与旁白段数({len(narration.segments)})不一致"
        )
    for i, sc in enumerate(spec.scenes):
        if sc.type not in TEMPLATE_TYPES:
            raise ContractError(f"未知镜头类型: {sc.type}")
        if sc.narration_id != i:
            raise ContractError(f"scene[{i}].narration_id={sc.narration_id} 应为 {i}")
        missing = [f for f in PROPS_REQUIRED[sc.type] if f not in sc.props]
        if missing:
            raise ContractError(f"{sc.type} 缺少必填字段: {', '.join(missing)}")
    return spec
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_schema.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/schema.py tests/test_schema.py
git commit -m "feat: scene-spec contract with validation"
```

---

### Task 3: 设计令牌与复用图元

**Files:**
- Create: `video_agent/style.py`
- Test: `tests/test_style.py`

**Interfaces:**
- Produces: 设计令牌 `FONT/BG/PANEL/FG/MUTED/DIM/RED/ACCENT`（值见 Global Constraints）
- Produces: `chip(text, color=ACCENT[0], font_size=30, fill=PANEL) -> VGroup`、`badge(text, color) -> VGroup`、`heading(main, sub=None) -> VGroup`、`tick(color) -> VGroup`、`cand_box(mark: str, color) -> VGroup`
- Produces: `apply_manim_config()`（设置 `config.background_color=BG`、`config.disable_caching=True`）
- Consumes: `manim`

- [ ] **Step 1: 写失败测试**

`tests/test_style.py`：
```python
from video_agent.style import FONT, BG, ACCENT, chip, tick, cand_box, apply_manim_config

def test_tokens():
    assert FONT == "Noto Sans SC"
    assert BG == "#0F172A"
    assert len(ACCENT) == 5

def test_chip_is_a_vgroup():
    from manim import VGroup
    g = chip("测试", font_size=24)
    assert isinstance(g, VGroup)
    assert len(g) == 2  # 圆角框 + 文字

def test_tick_has_two_segments():
    t = tick(ACCENT[0])
    assert len(t) == 2

def test_cand_box_tick_vs_cross():
    assert len(cand_box("tick", ACCENT[0])) == 2
    assert len(cand_box("cross", ACCENT[0])) == 2

def test_apply_config_sets_background():
    import manim
    apply_manim_config()
    assert manim.config.background_color == BG
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_style.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.style`）

- [ ] **Step 3: 写最小实现**

从 `episodes/cs329_explainer.py` 抽出令牌与 `chip/badge/heading/tick/cand_box`（去掉样片专属的 `step_diagram`，它属于 `steps` 模板）。

`video_agent/style.py`：
```python
from __future__ import annotations
import numpy as np
from manim import (
    VGroup, Text, RoundedRectangle, Line, Cross, DOWN, NORMAL, BOLD, config,
)

FONT = "Noto Sans SC"
BG = "#0F172A"
PANEL = "#1E293B"
FG = "#F8FAFC"
MUTED = "#94A3B8"
DIM = "#475569"
RED = "#F87171"
ACCENT = ["#38BDF8", "#818CF8", "#A78BFA", "#F472B6", "#34D399"]


def apply_manim_config() -> None:
    config.background_color = BG
    config.disable_caching = True


def chip(text, color=ACCENT[0], font_size=30, fill=PANEL):
    t = Text(text, font=FONT, font_size=font_size, color=FG)
    box = RoundedRectangle(
        corner_radius=0.16, width=t.width + 0.8, height=t.height + 0.5,
        fill_color=fill, fill_opacity=1, stroke_color=color, stroke_width=2,
    )
    t.move_to(box.get_center())
    return VGroup(box, t)


def badge(text, color):
    g = chip(text, color=color, font_size=30, fill=BG)
    g[1].set_weight(BOLD)
    return g


def heading(main, sub=None, sub_color=ACCENT[0]):
    m = Text(main, font=FONT, font_size=40, weight=BOLD, color=FG)
    if sub is None:
        return VGroup(m)
    s = Text(sub, font=FONT, font_size=25, color=sub_color)
    return VGroup(m, s).arrange(DOWN, buff=0.18)


def tick(color, scale=1.0):
    p1 = np.array([-0.16, 0.02, 0])
    p2 = np.array([-0.02, -0.14, 0])
    p3 = np.array([0.2, 0.16, 0])
    g = VGroup(
        Line(p1, p2, color=color, stroke_width=5),
        Line(p2, p3, color=color, stroke_width=5),
    )
    return g.scale(scale)


def cand_box(mark, color, size=0.68):
    box = RoundedRectangle(
        corner_radius=0.12, width=size, height=size,
        fill_color=PANEL, fill_opacity=1, stroke_color=color, stroke_width=2,
    )
    if mark == "tick":
        g = tick(color).scale(0.9).move_to(box)
    else:
        g = Cross(color=RED, stroke_width=5).scale(0.5).move_to(box)
    return VGroup(box, g)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_style.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/style.py tests/test_style.py
git commit -m "feat: design tokens and reusable primitives"
```

---

### Task 4: 模板注册表 + 保底三件套（title / bullets / closing）

**Files:**
- Create: `video_agent/templates/__init__.py`、`title.py`、`bullets.py`、`closing.py`
- Test: `tests/test_templates_core.py`

**Interfaces:**
- Produces: 模板模块统一接口 `render(props: dict, duration: float, subtitle: str | None = None) -> list[Animation]`——返回动画序列，`run_time` 之和 == `duration`
- Produces: `entrance_hold(anim, duration, min_entrance=0.8) -> list[Animation]`——把入场压进 `[min_entrance, duration]`，末尾补 `Wait` 填满 `duration`
- Produces: `TEMPLATES: dict[str, module]`、`render_scene(type, props, duration, subtitle=None) -> list[Animation]`

> **实现顺序（关键）**：`video_agent/templates/__init__.py` 中必须**先定义 `entrance_hold`，再 `from . import title, bullets, closing`**，否则子模块在导入期引用 `entrance_hold` 会 `ImportError`。

- [ ] **Step 1: 写失败测试**

`tests/test_templates_core.py`：
```python
import pytest
from video_agent.templates import TEMPLATES, render_scene, entrance_hold

def test_entrance_hold_fills_duration():
    anims = entrance_hold(None, duration=3.0, min_entrance=0.8)
    total = sum(a.run_time for a in anims)
    assert abs(total - 3.0) < 1e-6

def test_core_three_registered():
    for t in ("title", "bullets", "closing"):
        assert t in TEMPLATES

def test_render_title_returns_anims():
    anims = render_scene("title", {"title": "标题", "subtitle": "副标题"}, duration=2.5)
    assert len(anims) >= 1
    assert abs(sum(a.run_time for a in anims) - 2.5) < 1e-6

def test_render_bullets_returns_anims():
    anims = render_scene("bullets", {"heading": "要点", "items": ["a", "b", "c"]}, duration=4.0)
    assert abs(sum(a.run_time for a in anims) - 4.0) < 1e-6

def test_render_unknown_type_raises():
    with pytest.raises(KeyError):
        render_scene("nope", {}, duration=1.0)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_core.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.templates`）

- [ ] **Step 3: 写最小实现**

`video_agent/templates/__init__.py`：
```python
from __future__ import annotations
from manim import Animation, Wait


def entrance_hold(anim, duration: float, min_entrance: float = 0.8) -> list[Animation]:
    """把入场动画压进 [min_entrance, duration]，末尾补 Wait 填满 duration。"""
    entrance = min(min_entrance, duration)
    anims: list[Animation] = []
    if anim is not None:
        anim.run_time = entrance
        anims.append(anim)
    rest = duration - entrance
    if rest > 1e-6:
        anims.append(Wait(rest))
    return anims


from . import title, bullets, closing  # noqa: E402  (须在 entrance_hold 之后)

TEMPLATES = {
    "title": title, "bullets": bullets, "closing": closing,
}


def render_scene(type: str, props: dict, duration: float, subtitle=None) -> list[Animation]:
    return TEMPLATES[type].render(props, duration, subtitle)
```

`video_agent/templates/title.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN, UP
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    t = Text(props["title"], font=FONT, font_size=56, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("subtitle"):
        s = Text(props["subtitle"], font=FONT, font_size=30, color=ACCENT[0])
        parts = VGroup(t, s).arrange(DOWN, buff=0.3)
    return entrance_hold(FadeIn(parts, shift=UP * 0.4), duration)
```

`video_agent/templates/bullets.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN, LEFT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    items = VGroup(*[
        Text(f"· {it}", font=FONT, font_size=30, color=ACCENT[i % len(ACCENT)])
        for i, it in enumerate(props["items"])
    ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
    body = VGroup(h, items).arrange(DOWN, buff=0.5)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
```

`video_agent/templates/closing.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, MUTED
from . import entrance_hold


def render(props, duration, subtitle=None):
    t = Text(props["text"], font=FONT, font_size=44, weight="BOLD", color=FG)
    parts = VGroup(t)
    if props.get("handle"):
        h = Text(props["handle"], font=FONT, font_size=24, color=MUTED)
        parts = VGroup(t, h).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(parts), duration)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_core.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/templates/ tests/test_templates_core.py
git commit -m "feat: template registry and core three (title/bullets/closing)"
```

---

### Task 5: 文本型模板（section / quote / compare / summary）

**Files:**
- Create: `video_agent/templates/section.py`、`quote.py`、`compare.py`、`summary.py`
- Modify: `video_agent/templates/__init__.py`（注册 4 型）
- Test: `tests/test_templates_text.py`

**Interfaces:**
- Consumes: `entrance_hold`、`style` 令牌
- Produces: 4 个模板模块，均实现 `render(props, duration, subtitle=None) -> list[Animation]`

- [ ] **Step 1: 写失败测试**

`tests/test_templates_text.py`：
```python
import pytest
from video_agent.templates import render_scene

CASES = [
    ("section", {"index": 2, "heading": "第二幕"}, 2.5),
    ("quote", {"text": "先有内容，再选模板。", "source": "设计原则"}, 3.0),
    ("compare", {"heading": "A vs B", "left": {"title": "选择", "items": ["x"]},
                 "right": {"title": "融合", "items": ["y"]}}, 4.0),
    ("summary", {"heading": "回顾", "items": ["一", "二", "三"]}, 3.5),
]

@pytest.mark.parametrize("t,props,dur", CASES)
def test_text_templates_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_text.py -v`
Expected: FAIL（`KeyError: 'section'`）

- [ ] **Step 3: 写最小实现**

`video_agent/templates/section.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    idx = Text(f"{props['index']:02d}", font=FONT, font_size=90, weight="BOLD", color=ACCENT[1])
    h = Text(props["heading"], font=FONT, font_size=42, color=FG)
    body = VGroup(idx, h).arrange(DOWN, buff=0.25)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.3), duration)
```

`video_agent/templates/quote.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, MUTED
from . import entrance_hold


def render(props, duration, subtitle=None):
    q = Text(f"“{props['text']}”", font=FONT, font_size=46, weight="BOLD", color=FG)
    parts = VGroup(q)
    if props.get("source"):
        s = Text(f"— {props['source']}", font=FONT, font_size=26, color=MUTED)
        parts = VGroup(q, s).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(parts), duration)
```

`video_agent/templates/compare.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN, RIGHT, LEFT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def _col(side, color):
    t = Text(side["title"], font=FONT, font_size=34, weight="BOLD", color=color)
    items = VGroup(*[Text(f"· {i}", font=FONT, font_size=26, color=FG) for i in side["items"]]
                   ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
    return VGroup(t, items).arrange(DOWN, buff=0.3)


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    left = _col(props["left"], ACCENT[0])
    right = _col(props["right"], ACCENT[3])
    cols = VGroup(left, right).arrange(RIGHT, buff=1.2)
    body = VGroup(h, cols).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/summary.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN, RIGHT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    chips = VGroup(*[
        Text(i, font=FONT, font_size=28, color=ACCENT[k % len(ACCENT)])
        for k, i in enumerate(props["items"])
    ]).arrange(RIGHT, buff=0.4)
    body = VGroup(h, chips).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/__init__.py` 导入与注册改为：
```python
from . import title, bullets, closing, section, quote, compare, summary  # noqa: E402
TEMPLATES = {
    "title": title, "bullets": bullets, "closing": closing,
    "section": section, "quote": quote, "compare": compare, "summary": summary,
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_text.py tests/test_templates_core.py -v`
Expected: 9 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/templates/ tests/test_templates_text.py
git commit -m "feat: text templates (section/quote/compare/summary)"
```

---

### Task 6: 图形型模板（steps / cycle / tree / grid / metric）

**Files:**
- Create: `video_agent/templates/steps.py`、`cycle.py`、`tree.py`、`grid.py`、`metric.py`
- Modify: `video_agent/templates/__init__.py`（注册 5 型，凑满 12）
- Test: `tests/test_templates_shapes.py`

**Interfaces:**
- Consumes: `style.chip/tick/cand_box`、`entrance_hold`
- Produces: 5 个模板模块，均实现 `render(props, duration, subtitle=None) -> list[Animation]`

- [ ] **Step 1: 写失败测试**

`tests/test_templates_shapes.py`：
```python
import pytest
from video_agent.templates import TEMPLATES, render_scene

CASES = [
    ("steps", {"heading": "流程", "steps": ["甲", "乙", "丙"], "done_index": 1}, 4.0),
    ("cycle", {"heading": "循环", "nodes": ["推理", "行动", "观察"]}, 4.0),
    ("tree", {"heading": "搜索树", "root": "根", "children": [["a", "b"], ["c"]]}, 4.0),
    ("grid", {"heading": "候选", "cells": [{"label": "A", "mark": "cross"},
                                            {"label": "B", "mark": "tick"}]}, 3.0),
    ("metric", {"heading": "提升", "value": 42, "unit": "%", "label": "准确率"}, 4.0),
]

def test_all_12_registered():
    assert len(TEMPLATES) == 12

@pytest.mark.parametrize("t,props,dur", CASES)
def test_shapes_fill_duration(t, props, dur):
    anims = render_scene(t, props, duration=dur)
    assert abs(sum(a.run_time for a in anims) - dur) < 1e-6
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_shapes.py -v`
Expected: FAIL（`KeyError: 'steps'`；`test_all_12_registered` 断言 7 != 12）

- [ ] **Step 3: 写最小实现**

`video_agent/templates/steps.py`：
```python
from manim import FadeIn, VGroup, Text, Dot, Line, DOWN, UP, LEFT, RIGHT
from ..style import FONT, FG, DIM, ACCENT, tick
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    n = len(props["steps"])
    line = Line(LEFT * (n * 0.6), RIGHT * (n * 0.6), color=DIM, stroke_width=3)
    dots = VGroup(*[Dot(radius=0.14, color=ACCENT[0]) for _ in range(n)]).arrange(RIGHT, buff=1.2)
    dots.move_to(line.get_center())
    labels = VGroup(*[Text(s, font=FONT, font_size=26, color=FG) for s in props["steps"]])
    for i in range(n):
        labels[i].next_to(dots[i], DOWN, buff=0.3)
    marks = VGroup()
    if props.get("done_index") is not None:
        for i in range(props["done_index"] + 1):
            marks.add(tick(ACCENT[4]).next_to(dots[i], UP, buff=0.2))
    body = VGroup(h, line, dots, labels, marks).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/cycle.py`：
```python
import numpy as np
from manim import FadeIn, VGroup, Text, CurvedArrow, DOWN
from ..style import FONT, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=ACCENT[0])
    n = len(props["nodes"])
    r = 1.6
    pos = [np.array([r * np.cos(2 * np.pi * i / n), r * np.sin(2 * np.pi * i / n), 0])
           for i in range(n)]
    nodes = VGroup(*[
        Text(props["nodes"][i], font=FONT, font_size=26, color=ACCENT[i % len(ACCENT)]).move_to(pos[i])
        for i in range(n)
    ])
    arrows = VGroup(*[
        CurvedArrow(pos[i], pos[(i + 1) % n], angle=-np.pi / 4, color=ACCENT[0])
        for i in range(n)
    ])
    ring = VGroup(arrows, nodes)
    body = VGroup(h, ring).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/tree.py`：
```python
from manim import FadeIn, VGroup, Text, Line, DOWN, UP, RIGHT
from ..style import FONT, FG, ACCENT
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=ACCENT[0])
    root = Text(props["root"], font=FONT, font_size=30, color=ACCENT[0]).shift(UP * 1.2)
    kids = VGroup()
    for row in props["children"]:
        for c in row:
            kids.add(Text(c, font=FONT, font_size=24, color=FG))
    kids.arrange(RIGHT, buff=1.0).shift(DOWN * 0.6)
    edges = VGroup(*[Line(root.get_bottom(), k.get_top(), color=ACCENT[2], stroke_width=2)
                     for k in kids])
    graph = VGroup(edges, root, kids)
    body = VGroup(h, graph).arrange(DOWN, buff=0.6)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/grid.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN, RIGHT
from ..style import FONT, FG, ACCENT, cand_box
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    boxes = VGroup()
    for i, c in enumerate(props["cells"]):
        box = cand_box(c.get("mark", "cross"), ACCENT[i % len(ACCENT)])
        lbl = Text(c["label"], font=FONT, font_size=24, color=FG).next_to(box, DOWN, buff=0.18)
        boxes.add(VGroup(box, lbl))
    boxes.arrange(RIGHT, buff=0.6)
    body = VGroup(h, boxes).arrange(DOWN, buff=0.7)
    return entrance_hold(FadeIn(body), duration)
```

`video_agent/templates/metric.py`：
```python
from manim import FadeIn, VGroup, Text, DOWN
from ..style import FONT, FG, ACCENT, MUTED
from . import entrance_hold


def render(props, duration, subtitle=None):
    h = Text(props["heading"], font=FONT, font_size=38, weight="BOLD", color=FG)
    val = Text(f"{props['value']}{props.get('unit', '')}",
               font=FONT, font_size=90, weight="BOLD", color=ACCENT[3])
    lbl = Text(props["label"], font=FONT, font_size=26, color=MUTED)
    body = VGroup(h, val, lbl).arrange(DOWN, buff=0.4)
    return entrance_hold(FadeIn(body, shift=DOWN * 0.2), duration)
```

`video_agent/templates/__init__.py` 导入与注册改为全 12 型：
```python
from . import (  # noqa: E402
    title, bullets, closing, section, quote, compare, summary,
    steps, cycle, tree, grid, metric,
)
TEMPLATES = {
    "title": title, "bullets": bullets, "closing": closing,
    "section": section, "quote": quote, "compare": compare, "summary": summary,
    "steps": steps, "cycle": cycle, "tree": tree, "grid": grid, "metric": metric,
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_shapes.py -v`
Expected: 6 passed（`test_all_12_registered` + 5 parametrized）

- [ ] **Step 5: 全模板回归 + 提交**

Run: `.env-mamba/env/bin/python -m pytest tests/test_templates_core.py tests/test_templates_text.py tests/test_templates_shapes.py -v`
Expected: 全部 passed

```bash
git add video_agent/templates/ tests/test_templates_shapes.py
git commit -m "feat: shape templates (steps/cycle/tree/grid/metric) — all 12 types"
```

---

### Task 7: 分镜渲染器（组装整片 + 双比例）

**Files:**
- Create: `video_agent/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `config.CANVAS/FPS`、`style.apply_manim_config`、`templates.render_scene`
- Produces: `build_scene_sequence(scenes: list[dict], durations: list[float], subtitle_map: dict[int,str] | None) -> list[tuple[str, list[Animation]]]`
- Produces: `render_video(spec: dict, durations: list[float], aspect: str, out_dir: str, subtitle=False) -> str`（返回无声 mp4 路径）
- Produces: `class ExplainSpec(Scene)`（Manim Scene，在 `construct` 里逐镜 `play`）

- [ ] **Step 1: 写失败测试**

`tests/test_render.py`：
```python
from video_agent.render import build_scene_sequence

SCENES = [
    {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
    {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "q"}},
]

def test_build_sequence_length_matches():
    seq = build_scene_sequence(SCENES, [2.0, 3.0], None)
    assert len(seq) == 2
    assert seq[0][0] == "title" and seq[1][0] == "quote"

def test_build_sequence_durations_sum():
    seq = build_scene_sequence(SCENES, [2.0, 3.0], None)
    total = sum(a.run_time for _, anims in seq for a in anims)
    assert abs(total - 5.0) < 1e-6
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_render.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.render`）

- [ ] **Step 3: 写最小实现**

`video_agent/render.py`：
```python
from __future__ import annotations
import os
from manim import Scene, config

from .config import CANVAS, FPS
from .style import apply_manim_config
from .templates import render_scene


def build_scene_sequence(scenes, durations, subtitle_map):
    seq = []
    for sc, dur in zip(scenes, durations):
        sub = subtitle_map.get(sc["id"]) if subtitle_map else None
        anims = render_scene(sc["type"], sc["props"], dur, sub)
        seq.append((sc["type"], anims))
    return seq


class ExplainSpec(Scene):
    SCENES: list = []
    DURATIONS: list = []
    SUBTITLE_MAP: dict = {}

    def construct(self):
        for _, anims in build_scene_sequence(self.SCENES, self.DURATIONS, self.SUBTITLE_MAP):
            for a in anims:
                self.play(a)


def render_video(spec, durations, aspect, out_dir, subtitle=False):
    apply_manim_config()
    w, h = CANVAS[aspect]
    config.pixel_width = w
    config.pixel_height = h
    config.frame_rate = FPS
    config.media_dir = os.path.join(out_dir, "media")
    sub_map = {}
    if subtitle:
        for sc in spec["scenes"]:
            sub_map[sc["id"]] = sc["props"].get("text") or sc["props"].get("heading", "")
    ExplainSpec.SCENES = spec["scenes"]
    ExplainSpec.DURATIONS = durations
    ExplainSpec.SUBTITLE_MAP = sub_map
    scene = ExplainSpec()
    scene.render()
    return str(scene.renderer.file_writer.movie_file_path)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_render.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/render.py tests/test_render.py
git commit -m "feat: spec renderer with dual aspect support"
```

---

### Task 8: LLM 客户端（OpenAI 兼容 + 强制 JSON）

**Files:**
- Create: `video_agent/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `config.Settings`
- Produces: `class LLMClient(settings, transport=None)`，方法 `chat(messages, temperature=0.7) -> str`
- Produces: `chat_json(messages, retries=2) -> dict`（去掉 ```json 围栏、`json.loads`；解析失败按 `retries` 重问）
- Produces: `strip_fence(text) -> str`、`LLMError(Exception)`
- Produces: 可注入 `transport: Callable[[list[dict]], str]` 供测试（默认走 openai SDK）

- [ ] **Step 1: 写失败测试**

`tests/test_llm.py`：
```python
import pytest
from video_agent.llm import LLMClient, strip_fence, LLMError
from video_agent.config import Settings

S = Settings("u", "k", "m")

def test_strip_fence_plain():
    assert strip_fence('{"a":1}') == '{"a":1}'

def test_strip_fence_json_block():
    assert strip_fence('```json\n{"a":1}\n```') == '{"a":1}'
    assert strip_fence('```\n{"a":1}\n```') == '{"a":1}'

def test_chat_json_parses():
    c = LLMClient(S, transport=lambda msgs: '{"ok": true}')
    assert c.chat_json([{"role": "user", "content": "hi"}]) == {"ok": True}

def test_chat_json_retries_then_raises():
    calls = {"n": 0}
    def bad(msgs):
        calls["n"] += 1
        return "not json"
    c = LLMClient(S, transport=bad)
    with pytest.raises(LLMError):
        c.chat_json([{"role": "user", "content": "hi"}], retries=1)
    assert calls["n"] == 2  # 首次 + 1 次重试
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_llm.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.llm`）

- [ ] **Step 3: 写最小实现**

`video_agent/llm.py`：
```python
from __future__ import annotations
import json
from typing import Callable
from .config import Settings


class LLMError(Exception):
    pass


def strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        if t.strip().startswith("json"):
            t = t.strip()[4:]
    return t.strip()


class LLMClient:
    def __init__(self, settings: Settings, transport: Callable[[list[dict]], str] | None = None):
        self.settings = settings
        self._transport = transport or self._openai_transport

    def _openai_transport(self, messages: list[dict]) -> str:
        from openai import OpenAI
        client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        resp = client.chat.completions.create(model=self.settings.model, messages=messages)
        return resp.choices[0].message.content

    def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        return self._transport(messages)

    def chat_json(self, messages: list[dict], retries: int = 2) -> dict:
        last_err = None
        for _ in range(retries + 1):
            raw = self._transport(messages)
            try:
                return json.loads(strip_fence(raw))
            except json.JSONDecodeError as e:
                last_err = e
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"输出不是合法 JSON（{e}）。只输出 JSON，不要解释。"},
                ]
        raise LLMError(f"无法获得合法 JSON: {last_err}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_llm.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/llm.py tests/test_llm.py
git commit -m "feat: openai-compatible LLM client with JSON enforcement"
```

---

### Task 9: 第①步 文章→口播稿（script_gen）

**Files:**
- Create: `video_agent/script_gen.py`、`video_agent/prompts/script.md`
- Test: `tests/test_script_gen.py`

**Interfaces:**
- Consumes: `LLMClient.chat_json`、`schema.Narration`
- Produces: `generate_narration(article_md: str, client: LLMClient) -> Narration`（失败重试 2 次后抛 `LLMError`）
- Produces: `load_prompt(name: str) -> str`（读 `prompts/<name>.md`）

- [ ] **Step 1: 写失败测试**

`tests/test_script_gen.py`：
```python
import pytest
from video_agent.script_gen import generate_narration, load_prompt
from video_agent.llm import LLMClient, LLMError
from video_agent.config import Settings

S = Settings("u", "k", "m")
GOOD = '{"title":"T","segments":[{"id":0,"text":"一"},{"id":1,"text":"二"}]}'

def test_load_prompt_nonempty():
    assert len(load_prompt("script")) > 20

def test_generate_narration_parses():
    c = LLMClient(S, transport=lambda m: GOOD)
    n = generate_narration("# 文章正文", c)
    assert n.title == "T" and len(n.segments) == 2

def test_generate_narration_retries_then_raises():
    c = LLMClient(S, transport=lambda m: "junk")
    with pytest.raises(LLMError):
        generate_narration("# x", c)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_script_gen.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.script_gen`）

- [ ] **Step 3: 写最小实现**

`video_agent/prompts/script.md`：
```markdown
你是一名知识讲解视频的撰稿人。把用户给的 Markdown 文章改写成一段**口播稿**。

要求：
- 口语化、适合朗读，去除 Markdown 语法与链接。
- 按"一句话或一个完整意群"切成若干段（segments），每段将来对应一个镜头。
- 段落数量控制在 8~40 段之间。
- 保留原文的核心事实与数据，不要杜撰。

只输出如下 JSON，不要任何解释：
{"title": "视频标题", "segments": [{"id": 0, "text": "第一句"}, {"id": 1, "text": "第二句"}]}
```

`video_agent/script_gen.py`：
```python
from __future__ import annotations
import os
from .llm import LLMClient, LLMError
from .schema import Narration

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPT_DIR, f"{name}.md"), encoding="utf-8") as f:
        return f.read()


def generate_narration(article_md: str, client: LLMClient) -> Narration:
    messages = [
        {"role": "system", "content": load_prompt("script")},
        {"role": "user", "content": article_md},
    ]
    try:
        raw = client.chat_json(messages, retries=2)
    except LLMError as e:
        raise LLMError(f"口播稿生成失败: {e}")
    return Narration(**raw)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_script_gen.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/script_gen.py video_agent/prompts/script.md tests/test_script_gen.py
git commit -m "feat: step1 article -> narration (script_gen)"
```

---

### Task 10: 第②步 口播稿→分镜（scene_gen，含校验/重试/兜底）

**Files:**
- Create: `video_agent/scene_gen.py`、`video_agent/prompts/scene.md`
- Test: `tests/test_scene_gen.py`

**Interfaces:**
- Consumes: `LLMClient.chat_json`、`schema.validate_scene_spec/ContractError/Narration`、`script_gen.load_prompt`
- Produces: `generate_scene_spec(narration: Narration, client: LLMClient) -> SceneSpec`（校验失败带错误回问一次；仍失败 → `fallback_spec`）
- Produces: `fallback_spec(narration: Narration) -> SceneSpec`（首镜 `title`、中段 `bullets`、末镜 `closing`，严格 1:1）

- [ ] **Step 1: 写失败测试**

`tests/test_scene_gen.py`：
```python
from video_agent.scene_gen import generate_scene_spec, fallback_spec
from video_agent.schema import Narration
from video_agent.llm import LLMClient
from video_agent.config import Settings

S = Settings("u", "k", "m")
NARR = Narration(title="T", segments=[{"id": 0, "text": "一"},
                                      {"id": 1, "text": "二"},
                                      {"id": 2, "text": "三"}])

def test_fallback_has_three_types_and_1to1():
    spec = fallback_spec(NARR)
    assert spec.scenes[0].type == "title"
    assert spec.scenes[-1].type == "closing"
    assert [s.narration_id for s in spec.scenes] == [0, 1, 2]

def test_generate_ok():
    good = ('{"title":"T","aspects":["916","169"],"scenes":['
            '{"id":0,"narration_id":0,"type":"title","props":{"title":"T"}},'
            '{"id":1,"narration_id":1,"type":"quote","props":{"text":"q"}},'
            '{"id":2,"narration_id":2,"type":"closing","props":{"text":"完"}}]}')
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: good))
    assert len(spec.scenes) == 3

def test_generate_bad_then_fallback():
    spec = generate_scene_spec(NARR, LLMClient(S, transport=lambda m: "nonsense"))
    assert spec.scenes[0].type == "title"  # 兜底
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_scene_gen.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.scene_gen`）

- [ ] **Step 3: 写最小实现**

`video_agent/prompts/scene.md`：
```markdown
你是分镜师。把口播稿的每一段分配一个"镜头"。你只能从下列 12 种 type 中挑选，
每种有固定的 props 字段：

- title:   {title, subtitle?}
- section: {index, heading}
- bullets: {heading, items[]}
- steps:   {heading, steps[], done_index?}
- cycle:   {heading, nodes[]}
- tree:    {heading, root, children[][]}
- compare: {heading, left:{title,items[]}, right:{title,items[]}}
- grid:    {heading, cells:[{label, mark:"tick"|"cross"}]}
- metric:  {heading, value, unit?, label}
- quote:   {text, source?}
- summary: {heading, items[]}
- closing: {text, handle?}

规则：
- 镜头数量必须**严格等于**旁白段数，且 scenes[i].narration_id 必须等于 i。
- 第一段用 title，最后一段用 closing。
- 根据内容选择最贴切的画面类型。

只输出 JSON：
{"title":"...","aspects":["916","169"],"scenes":[{"id":0,"narration_id":0,"type":"title","props":{...}}, ...]}
```

`video_agent/scene_gen.py`：
```python
from __future__ import annotations
from .llm import LLMClient, LLMError
from .schema import Narration, SceneSpec, validate_scene_spec, ContractError
from .script_gen import load_prompt


def fallback_spec(narration: Narration) -> SceneSpec:
    scenes = []
    n = len(narration.segments)
    for i, seg in enumerate(narration.segments):
        if i == 0:
            t, props = "title", {"title": narration.title}
        elif i == n - 1:
            t, props = "closing", {"text": seg.text}
        else:
            t, props = "bullets", {"heading": seg.text[:20], "items": [seg.text]}
        scenes.append({"id": i, "narration_id": i, "type": t, "props": props})
    return SceneSpec(title=narration.title, aspects=["916", "169"], scenes=scenes)


def generate_scene_spec(narration: Narration, client: LLMClient) -> SceneSpec:
    messages = [
        {"role": "system", "content": load_prompt("scene")},
        {"role": "user", "content": narration.model_dump_json()},
    ]
    try:
        raw = client.chat_json(messages, retries=2)
        return validate_scene_spec(raw, narration)
    except (LLMError, ContractError) as e:
        messages = messages + [{"role": "user",
                                "content": f"上次输出不合法：{e}。请修正后重新只输出 JSON。"}]
        try:
            raw = client.chat_json(messages, retries=1)
            return validate_scene_spec(raw, narration)
        except (LLMError, ContractError):
            return fallback_spec(narration)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_scene_gen.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/scene_gen.py video_agent/prompts/scene.md tests/test_scene_gen.py
git commit -m "feat: step2 narration -> scene spec with validation and fallback"
```

---

### Task 11: 第③步 语音合成 + 时长探测（tts）

**Files:**
- Create: `video_agent/tts.py`
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `schema.Narration`
- Produces: `ffmpeg_path() -> str`（优先 `.env-mamba/env/bin/ffmpeg`，否则回退 PATH）
- Produces: `synth_segment(text, out_path, voice) -> None`（默认走 edge-tts）
- Produces: `probe_duration(path) -> float`（走 ffprobe）
- Produces: `render_voiceover(narration, out_dir, voice, synth=synth_segment, probe=probe_duration, retries=2) -> list[float]`

- [ ] **Step 1: 写失败测试**

`tests/test_tts.py`：
```python
import pytest
from video_agent.tts import render_voiceover
from video_agent.schema import Narration
from video_agent import tts

NARR = Narration(title="T", segments=[{"id": 0, "text": "一"},
                                      {"id": 1, "text": "二"}])

def test_render_voiceover_returns_durations(tmp_path):
    def fake_synth(text, path, voice):
        open(path, "wb").write(b"\x00")
    calls = iter([5.0, 1.5])
    def fake_probe(path):
        return next(calls)
    durs = render_voiceover(NARR, str(tmp_path), "zh-CN-XiaoxiaoNeural",
                            synth=fake_synth, probe=fake_probe)
    assert durs == [5.0, 1.5]

def test_render_voiceover_retries_then_raises(tmp_path):
    def boom(text, path, voice):
        raise RuntimeError("tts down")
    with pytest.raises(RuntimeError):
        render_voiceover(NARR, str(tmp_path), "v", synth=boom, probe=lambda p: 1.0, retries=1)

def test_ffmpeg_path_points_into_env():
    assert "ffmpeg" in tts.ffmpeg_path()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_tts.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.tts`）

- [ ] **Step 3: 写最小实现**

`video_agent/tts.py`：
```python
from __future__ import annotations
import os
import subprocess
from .schema import Narration


def ffmpeg_path() -> str:
    """优先用环境里的 ffmpeg（.env-mamba/env/bin），否则回退 PATH。"""
    cand = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env-mamba", "env", "bin", "ffmpeg",
    )
    return cand if os.path.exists(cand) else "ffmpeg"


def synth_segment(text: str, out_path: str, voice: str) -> None:
    import asyncio
    import edge_tts

    async def _run():
        await edge_tts.Communicate(text, voice).save(out_path)
    asyncio.run(_run())


def probe_duration(path: str) -> float:
    ffprobe = ffmpeg_path().replace("ffmpeg", "ffprobe")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def render_voiceover(narration: Narration, out_dir: str, voice: str,
                     synth=synth_segment, probe=probe_duration, retries: int = 2) -> list[float]:
    os.makedirs(out_dir, exist_ok=True)
    durations = []
    for seg in narration.segments:
        path = os.path.join(out_dir, f"{seg.id:03d}.mp3")
        last = None
        ok = False
        for _ in range(retries + 1):
            try:
                synth(seg.text, path, voice)
                durations.append(probe(path))
                ok = True
                break
            except Exception as e:  # 声音失败 = 致命
                last = e
        if not ok:
            raise RuntimeError(f"第 {seg.id} 段配音失败: {last}")
    return durations
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_tts.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/tts.py tests/test_tts.py
git commit -m "feat: step3 edge-tts voiceover with duration probing"
```

---

### Task 12: 第④步 时长对齐（timing，纯函数）

**Files:**
- Create: `video_agent/timing.py`
- Test: `tests/test_timing.py`

**Interfaces:**
- Produces: `align_durations(audio_durations, gap=0.4) -> list[float]`
- Produces: `estimate_duration(text, chars_per_sec=5.0) -> float`

- [ ] **Step 1: 写失败测试**

`tests/test_timing.py`：
```python
import pytest
from video_agent.timing import align_durations, estimate_duration

def test_align_adds_gap():
    assert align_durations([5.2, 1.6, 4.0], gap=0.4) == pytest.approx([5.6, 2.0, 4.4])

def test_estimate_uses_char_count():
    assert estimate_duration("你好世界", chars_per_sec=2.0) == pytest.approx(2.0)

def test_estimate_min_floor():
    assert estimate_duration("", chars_per_sec=5.0) >= 0.5
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_timing.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.timing`）

- [ ] **Step 3: 写最小实现**

`video_agent/timing.py`：
```python
from __future__ import annotations
import re

_CJK = re.compile(r"[\u4e00-\u9fff]")


def align_durations(audio_durations, gap: float = 0.4):
    return [d + gap for d in audio_durations]


def estimate_duration(text: str, chars_per_sec: float = 5.0) -> float:
    n = len(_CJK.findall(text)) or len(text)
    return max(0.5, n / chars_per_sec)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_timing.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/timing.py tests/test_timing.py
git commit -m "feat: step4 duration alignment (narration-driven timing)"
```

---

### Task 13: 第⑥步 合成（compose，ffmpeg）

**Files:**
- Create: `video_agent/compose.py`
- Test: `tests/test_compose.py`

**Interfaces:**
- Consumes: `tts.ffmpeg_path`
- Produces: `build_concat_file(ids, audio_dir) -> str`
- Produces: `concat_voiceover(audio_dir, ids, out_path) -> str`
- Produces: `mux(video_path, audio_path, bgm_path, out_path) -> str`
- Produces: `assert_av_sync(video_dur, audio_dur, tol=0.3) -> None`（超差抛 `AssertionError`）

- [ ] **Step 1: 写失败测试**

`tests/test_compose.py`：
```python
import pytest
from video_agent.compose import build_concat_file, assert_av_sync

def test_build_concat_file_lists_in_order(tmp_path):
    (tmp_path / "000.mp3").write_bytes(b"x")
    (tmp_path / "001.mp3").write_bytes(b"x")
    text = build_concat_file([0, 1], str(tmp_path))
    assert text.index("000.mp3") < text.index("001.mp3")
    assert text.count("file ") == 2

def test_assert_av_sync_ok():
    assert_av_sync(10.0, 10.2, tol=0.3)  # 不抛

def test_assert_av_sync_raises():
    with pytest.raises(AssertionError):
        assert_av_sync(10.0, 11.0, tol=0.3)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_compose.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.compose`）

- [ ] **Step 3: 写最小实现**

`video_agent/compose.py`：
```python
from __future__ import annotations
import os
import subprocess
from .tts import ffmpeg_path


def build_concat_file(ids, audio_dir) -> str:
    return "\n".join(f"file '{os.path.join(audio_dir, f'{i:03d}.mp3')}'" for i in ids) + "\n"


def concat_voiceover(audio_dir, ids, out_path) -> str:
    lst = out_path + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        f.write(build_concat_file(ids, audio_dir))
    subprocess.run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out_path], check=True, capture_output=True)
    return out_path


def mux(video_path, audio_path, bgm_path, out_path) -> str:
    ff = ffmpeg_path()
    if bgm_path and os.path.exists(bgm_path):
        subprocess.run([
            ff, "-y", "-i", video_path, "-i", audio_path, "-i", bgm_path,
            "-filter_complex",
            "[2:a]volume=0.12,aloop=loop=-1:size=2e9[b];[1:a][b]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-shortest", out_path,
        ], check=True, capture_output=True)
    else:
        subprocess.run([ff, "-y", "-i", video_path, "-i", audio_path,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-shortest", out_path], check=True, capture_output=True)
    return out_path


def assert_av_sync(video_dur: float, audio_dur: float, tol: float = 0.3) -> None:
    assert abs(video_dur - audio_dur) <= tol, \
        f"音画时长偏差过大: video={video_dur:.2f}s audio={audio_dur:.2f}s tol={tol}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_compose.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add video_agent/compose.py tests/test_compose.py
git commit -m "feat: step6 ffmpeg composition and AV-sync assertion"
```

---

### Task 14: CLI 编排（cli.py）与端到端冒烟

**Files:**
- Create: `video_agent/cli.py`、`video_agent/__main__.py`、`articles/sample.md`、`assets/bgm/README.txt`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: 全部前置模块
- Produces: `run_pipeline(article_path, aspect, max_seconds, voice, subtitle, voiceover_only, out_dir=None, deps=None) -> dict`（`deps` 注入 6 个阶段函数，供测试全链而不触网）
- Produces: `main(argv=None) -> int`

- [ ] **Step 1: 写失败测试**

`tests/test_cli.py`：
```python
import os
from video_agent.cli import run_pipeline
from video_agent.schema import Narration, SceneSpec

NARR = Narration(title="T", segments=[{"id": 0, "text": "一"}, {"id": 1, "text": "二"}])

def _spec():
    return SceneSpec(title="T", aspects=["916", "169"], scenes=[
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 1, "type": "closing", "props": {"text": "完"}},
    ])

def test_run_pipeline_writes_intermediates(tmp_path):
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=lambda n, client: _spec(),
        render=lambda sp, dur, asp, o, sub: f"{o}/silent_{asp}.mp4",
        voiceover=lambda n, o, voice: [2.4, 2.4],
        compose=lambda **k: f"{k['out_dir']}/{k['name']}_{k['aspect']}.mp4",
        client=lambda: object(),
    )
    res = run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                       subtitle=False, voiceover_only=False, out_dir=str(out), deps=deps)
    assert os.path.exists(str(out / "narration.json"))
    assert os.path.exists(str(out / "scene_spec.json"))
    assert "a_916.mp4" in res["video"]

def test_voiceover_only_skips_render(tmp_path):
    art = tmp_path / "a.md"; art.write_text("# hi", encoding="utf-8")
    out = tmp_path / "out"
    called = {"render": 0}
    deps = dict(
        script_gen=lambda md, client: NARR,
        scene_gen=None,
        render=lambda *a: called.__setitem__("render", 1),
        voiceover=lambda n, o, v: [2.4, 2.4],
        compose=lambda **k: "x", client=lambda: object(),
    )
    run_pipeline(str(art), aspect="916", max_seconds=None, voice="v",
                 subtitle=False, voiceover_only=True, out_dir=str(out), deps=deps)
    assert called["render"] == 0
    assert os.path.exists(str(out / "narration.json"))
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.env-mamba/env/bin/python -m pytest tests/test_cli.py -v`
Expected: FAIL（`ModuleNotFoundError: video_agent.cli`）

- [ ] **Step 3: 写最小实现**

`video_agent/cli.py`：
```python
from __future__ import annotations
import argparse
import json
import os

from .config import load_settings
from .llm import LLMClient
from .script_gen import generate_narration
from .scene_gen import generate_scene_spec
from .timing import align_durations
from .tts import render_voiceover
from .render import render_video
from .compose import concat_voiceover, mux


def _default_deps():
    def _client():
        return LLMClient(load_settings())

    def _render(spec, durations, aspect, out_dir, subtitle):
        return render_video(spec, durations, aspect, out_dir, subtitle=subtitle)

    def _voiceover(narration, out_dir, voice):
        return render_voiceover(narration, out_dir, voice)

    def _compose(**k):
        ids = [s.id for s in k["narration"].segments]
        vo = concat_voiceover(k["audio_dir"], ids, os.path.join(k["out_dir"], "voice.mp3"))
        out = os.path.join(k["out_dir"], f"{k['name']}_{k['aspect']}.mp4")
        return mux(k["video"], vo, k.get("bgm"), out)

    return dict(client=_client, render=_render, voiceover=_voiceover,
                compose=_compose, script_gen=generate_narration, scene_gen=generate_scene_spec)


def run_pipeline(article_path, aspect, max_seconds, voice, subtitle,
                 voiceover_only, out_dir=None, deps=None):
    deps = deps or _default_deps()
    name = os.path.splitext(os.path.basename(article_path))[0]
    out_dir = out_dir or os.path.join("output", name)
    os.makedirs(out_dir, exist_ok=True)

    article = open(article_path, encoding="utf-8").read()
    client = deps["client"]()
    narration = deps["script_gen"](article, client)
    with open(os.path.join(out_dir, "narration.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(narration.model_dump_json()), f, ensure_ascii=False, indent=2)

    audio_dir = os.path.join(out_dir, "audio")
    durations = deps["voiceover"](narration, audio_dir, voice)
    if max_seconds:
        durations = [min(d, max_seconds) for d in durations]

    if voiceover_only:
        return {"narration": os.path.join(out_dir, "narration.json")}

    spec = deps["scene_gen"](narration, client)
    with open(os.path.join(out_dir, "scene_spec.json"), "w", encoding="utf-8") as f:
        json.dump(json.loads(spec.model_dump_json()), f, ensure_ascii=False, indent=2)

    shot = align_durations(durations)
    bgm = os.path.join("assets", "bgm", "track.mp3")
    aspects = ["916", "169"] if aspect == "both" else [aspect]
    result = {}
    for asp in aspects:
        video = deps["render"](json.loads(spec.model_dump_json()), shot, asp, out_dir, subtitle)
        result[asp] = deps["compose"](
            video=video, audio_dir=audio_dir, narration=narration, out_dir=out_dir,
            name=name, aspect=asp, bgm=bgm,
        )
    return {"video": result[aspect] if aspect in result else next(iter(result.values())),
            "all": result}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="video_agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("article")
    m.add_argument("--aspect", default="both", choices=["916", "169", "both"])
    m.add_argument("--max-seconds", type=float, default=None)
    m.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    m.add_argument("--subtitle", action="store_true")
    m.add_argument("--voiceover-only", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "make":
        res = run_pipeline(a.article, a.aspect, a.max_seconds, a.voice,
                           a.subtitle, a.voiceover_only)
        print("完成:", res)
        return 0
    return 1
```

`video_agent/__main__.py`：
```python
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

`articles/sample.md`：
```markdown
# 测试文章

这是一段用于冒烟测试的短文。它只有几句话，用来验证整条流水线能跑通。
第二句继续说明这件事。第三句收尾。
```

`assets/bgm/README.txt`：
```
把免版权循环配乐命名为 track.mp3 放在本目录。缺失时合成会自动跳过 BGM。
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.env-mamba/env/bin/python -m pytest tests/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 5: 全量回归 + 提交**

Run: `.env-mamba/env/bin/python -m pytest -v`
Expected: 全部 passed

```bash
git add video_agent/cli.py video_agent/__main__.py articles/sample.md assets/bgm/README.txt tests/test_cli.py
git commit -m "feat: CLI orchestration and end-to-end smoke"
```

---

### Task 15: README、真实冒烟与双比例产物

**Files:**
- Create: `README.md`
- Test: 手动端到端（真实一次渲染）

**Interfaces:**
- Consumes: 整个 CLI
- Produces: 可交付文档 + 一次真实出片证据

- [ ] **Step 1: 写 README.md**

````markdown
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

可选开关：`--aspect 916|169`、`--max-seconds 90`、`--voice zh-CN-YunxiNeural`、
`--subtitle`、`--voiceover-only`。

## 工作原理

文章 →（LLM）口播稿 →（LLM）分镜 JSON →（edge-tts）逐句配音 → 时长对齐 →
（Manim 12 型模板）渲染 →（ffmpeg）合成。详见 `docs/superpowers/specs/`。
````

- [ ] **Step 2: 真实冒烟（先只出口播稿，审词）**

Run: `.env-mamba/env/bin/python -m video_agent make articles/sample.md --voiceover-only`
Expected: 生成 `output/sample/narration.json` 且内容为非空中文口播稿。

- [ ] **Step 3: 真实冒烟（完整出片）**

Run: `.env-mamba/env/bin/python -m video_agent make articles/sample.md`
Expected: `output/sample/sample_916.mp4` 与 `sample_169.mp4` 存在。

- [ ] **Step 4: 校验产物**

Run:
```bash
.env-mamba/env/bin/ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,duration \
  -of default=noprint_wrappers=1 output/sample/sample_916.mp4
```
Expected: `width=1080`、`height=1920`、`duration>0`；横版对应 `1920×1080`。

- [ ] **Step 5: 提交**

```bash
git add README.md
git commit -m "docs: README with install, usage and pipeline overview"
```

---

## 测试策略汇总（对应设计 §10）

1. **契约测试**：`tests/test_schema.py`（Task 2）—— 锁死分镜 JSON 形状。
2. **单模板测试**：`tests/test_templates_*.py`（Task 4–6）—— 12 型逐个可渲。
3. **冒烟测试**：`tests/test_cli.py`（Task 14，注入式，不触网）+ Task 15 真实端到端。

**不写**：LLM 输出质量测试、ffmpeg 逐帧比对。

---

## 自审记录（Self-Review）

- **Spec 覆盖**：设计 §1→Task1/14；§2→Global Constraints+Task3；§3→Task9–14；§4→Task12；§5→Task3–6；§6→Task2；§7→Task12(+字幕在 Task7/14)；§8→Task1/14；§9→Task10/13；§10→测试策略汇总；§11/§12→约束与 YAGNI。**无缺口。**
- **占位符扫描**：无 TBD/TODO；所有代码步骤含完整代码。
- **类型一致性**：`render_scene(type, props, duration, subtitle)`、`entrance_hold(anim, duration, min_entrance)`、`validate_scene_spec(raw, narration)`、`render_voiceover(...)`、`align_durations(...)`、`run_pipeline(...)` 在定义与调用处签名一致。
- **已知顺序坑（已写入 Task 4）**：`templates/__init__.py` 必须先定义 `entrance_hold`，再导入子模块。
