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

def test_build_sequence_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        build_scene_sequence(SCENES, [2.0], None)  # 2 scenes, 1 duration

def test_degrade_shot_on_render_error(monkeypatch, caplog):
    import video_agent.render as r
    def boom(*a, **k):
        raise RuntimeError("template boom")
    monkeypatch.setattr(r, "render_scene", boom)
    with caplog.at_level("WARNING"):
        seq = r.build_scene_sequence(SCENES, [2.0, 3.0], None)
    assert len(seq) == 2
    assert abs(sum(a.run_time for _, anims in seq for a in anims) - 5.0) < 1e-6
    # Degradation must not swallow errors silently: every degrade leaves a log line
    assert caplog.text.count("degrading to a text-only shot") == 2

def test_build_subtitle_map_from_narration_sentences():
    from video_agent.render import build_subtitle_map
    spec = {"scenes": [{"id": 0}, {"id": 1}]}
    assert build_subtitle_map(spec, ["alpha", "beta"]) == {0: "alpha", 1: "beta"}
    assert build_subtitle_map(spec, None) == {}

def test_frame_dimensions_match_canvas_aspect():
    # The logical frame must match the pixel canvas ratio, or the 9:16 version
    # gets squeezed into a 16:9 letterbox with subtitles falling off-screen
    from video_agent.render import frame_dimensions
    for aspect, (w, h) in (("916", (1080, 1920)), ("169", (1920, 1080))):
        fw, fh = frame_dimensions(aspect)
        assert abs(fw / fh - w / h) < 1e-9

def test_progress_callback_called_with_done_total(monkeypatch):
    # Regression: the progress callback is a plain lambda (done, total). Stored as a
    # class attribute and called via `self`, it used to be descriptor-bound as an
    # instance method, injecting `self` and crashing with
    # "takes 2 positional arguments but 3 were given". It must be called through the
    # class so exactly two positional args reach the callback.
    import video_agent.render as r
    calls = []
    scenes = [
        {"id": 0, "narration_id": 0, "type": "title", "props": {"title": "T"}},
        {"id": 1, "narration_id": 1, "type": "quote", "props": {"text": "q"}},
    ]
    monkeypatch.setattr(r, "render_scene", lambda *a, **k: [])
    r.ExplainSpec.SCENES = scenes
    r.ExplainSpec.DURATIONS = [1.0, 1.0]
    r.ExplainSpec.SUBTITLE_MAP = {}
    r.ExplainSpec.PROGRESS = lambda done, total: calls.append((done, total))  # plain fn
    r.ExplainSpec._DONE = 0
    sc = r.ExplainSpec()
    monkeypatch.setattr(sc, "play", lambda *a, **k: None)
    sc.construct()
    assert calls == [(0, 2), (1, 2)]


def test_caption_wraps_narration_without_tiny_text():
    from video_agent.render import _caption
    text = "这是给手机用户阅读的较长字幕，需要自动换行而不是缩小成难以看清的一行"
    caption = _caption(text)
    visible = [m for m in caption.submobjects if hasattr(m, "text")]
    assert len(visible) == 1
    assert visible[0].original_text.replace("\n", "") == text
    assert "\n" in visible[0].original_text
    assert caption.width <= 12.8


def test_scene_content_stays_above_caption(monkeypatch):
    from manim import FadeIn, Text, VGroup, config

    import video_agent.render as r
    old_h = config.frame_height
    config.frame_height = 8.0
    try:
        body = VGroup(*[Text("一整行画面文字" * 4, font_size=38) for _ in range(5)]).arrange(r.DOWN)
        monkeypatch.setattr(r, "render_scene", lambda *a, **k: [FadeIn(body)])
        r.ExplainSpec.SCENES = [{"id": 0, "type": "title", "props": {"title": "文字"}}]
        r.ExplainSpec.DURATIONS = [2.0]
        r.ExplainSpec.SUBTITLE_MAP = {
            0: "很长的一段配音字幕应该与画面正文保持清晰的距离，避免文字叠在一起"
        }
        r.ExplainSpec.PROGRESS = None
        scene = r.ExplainSpec()
        added = []
        monkeypatch.setattr(scene, "add", lambda obj: added.append(obj))
        monkeypatch.setattr(scene, "play", lambda *a, **k: None)
        scene.construct()
        assert body.get_bottom()[1] >= added[0].get_top()[1] + 0.2
        assert body.get_top()[1] <= config.frame_height / 2 - 0.2
    finally:
        config.frame_height = old_h


def test_vertical_sparse_content_uses_more_of_frame():
    from manim import FadeIn, Text, config

    from video_agent.render import _place_content
    old_h = config.frame_height
    config.frame_height = 25.28
    try:
        title = Text("核心观点", font_size=56)
        before = title.width
        _place_content([FadeIn(title)])
        assert title.width >= before * 2
        assert title.get_center()[1] > 0
    finally:
        config.frame_height = old_h


def test_content_placement_ignores_wait_placeholder():
    from manim import FadeIn, Text

    from video_agent.render import _place_content
    from video_agent.templates import entrance_hold

    title = Text("核心观点")
    anims = entrance_hold(FadeIn(title), duration=2.0)
    _place_content(anims)
    assert title.width > 0


def test_vertical_caption_is_readable_and_inside_frame():
    from manim import config

    from video_agent.render import _caption
    old_h = config.frame_height
    config.frame_height = 25.28
    try:
        caption = _caption(
            "较长的中文配音字幕需要在竖屏上清晰易读，同时保持完整并留出平台操作栏空间" * 2
        )
        text = caption[1]
        assert text.font_size >= 40
        assert "\n" in text.original_text
        assert caption.get_bottom()[1] > -config.frame_height / 2 + 2.0
        assert caption.get_top()[1] < config.frame_height / 2
        assert caption.width < config.frame_width - 0.8
    finally:
        config.frame_height = old_h


def test_long_caption_is_split_into_two_line_cards_at_full_glyph_size():
    from manim import Text, config

    from video_agent.render import _caption, _caption_chunks
    from video_agent.style import FONT
    old_h = config.frame_height
    config.frame_height = 25.28
    try:
        chunks = _caption_chunks(
            "长字幕应当按配音的时间分段显示，让手机屏幕上的文字始终足够清楚。" * 5
        )
        assert len(chunks) >= 3
        one_line = Text("字幕", font=FONT, font_size=42).height
        for chunk in chunks:
            caption = _caption(chunk)
            line_count = caption[1].original_text.count("\n") + 1
            assert line_count <= 2
            assert caption[1].height / line_count >= one_line * 0.8
            assert caption.width < config.frame_width - 0.8
    finally:
        config.frame_height = old_h


def test_caption_card_changes_keep_shot_duration(monkeypatch):
    from manim import FadeIn, Text, Wait

    import video_agent.render as r
    body = Text("正文")
    monkeypatch.setattr(r, "render_scene", lambda *a, **k: [FadeIn(body, run_time=0.4), Wait(5.6)])
    r.ExplainSpec.SCENES = [{"id": 0, "type": "title", "props": {"title": "正文"}}]
    r.ExplainSpec.DURATIONS = [6.0]
    r.ExplainSpec.SUBTITLE_MAP = {0: "这段较长的字幕要逐段切换，保持每段文字清楚易读。" * 4}
    r.ExplainSpec.PROGRESS = None
    scene = r.ExplainSpec()
    shown, durations = [], []
    monkeypatch.setattr(scene, "add", lambda obj: shown.append(obj))
    monkeypatch.setattr(scene, "remove", lambda obj: None)
    monkeypatch.setattr(scene, "play", lambda anim: durations.append(anim.run_time))
    scene.construct()
    assert len(shown) >= 2
    assert abs(sum(durations) - 6.0) < 1e-6


def test_caption_cards_follow_unequal_spoken_lengths():
    from manim import FadeIn, Text, Wait

    from video_agent.render import _caption, _play_with_captions

    cards = [_caption("短句"),
             _caption("这是一段明显更长的字幕，朗读需要更多时间才能让观众看清楚内容。"),
             _caption("结束")]

    class SceneSpy:
        def __init__(self):
            self.elapsed = 0.0
            self.starts = []

        def play(self, animation):
            self.elapsed += animation.run_time

        def remove(self, caption):
            pass

        def add(self, caption):
            self.starts.append(self.elapsed)

    spy = SceneSpy()
    spy.add(cards[0])
    _play_with_captions(spy, [FadeIn(Text("画面"), run_time=0.4), Wait(5.6)], cards)
    first_time = spy.starts[1] - spy.starts[0]
    long_time = spy.starts[2] - spy.starts[1]
    assert long_time > first_time * 2
    assert abs(spy.elapsed - 6.0) < 1e-6


def test_english_caption_weight_counts_words():
    from video_agent.render import _caption_weight
    assert _caption_weight("A clear explanation with several words") > _caption_weight("OK") * 4
