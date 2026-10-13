from video_agent import progress


def test_stage_prints_numbered_line(capsys):
    progress.stage(2, 6, "Voiceover", "3 segments")
    assert capsys.readouterr().out.strip() == "[2/6] Voiceover … 3 segments"


def test_stage_without_detail_has_no_trailing_dots(capsys):
    progress.stage(1, 6, "Narration")
    assert capsys.readouterr().out.strip() == "[1/6] Narration"


def test_detail_is_indented(capsys):
    progress.detail("wrote narration.json")
    assert capsys.readouterr().out.strip() == "· wrote narration.json"


def test_disabled_prints_nothing(capsys):
    progress.ENABLED = False
    try:
        progress.stage(1, 6, "Narration")
        progress.detail("x")
    finally:
        progress.ENABLED = True
    assert capsys.readouterr().out == ""