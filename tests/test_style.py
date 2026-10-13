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
    # Manim 0.22 stores background_color as a ManimColor, not a raw str
    assert str(manim.config.background_color) == BG