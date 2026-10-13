"""Keep template text inside the visible frame.

Manim clips any mobject wider than the logical frame, and CJK strings quickly
exceed it in the narrow 9:16 frame. Templates call these helpers so an
over-long heading/line shrinks to fit instead of being cut off.
"""
from __future__ import annotations

from manim import Text

from ..config import DESIGN_FRAME_WIDTH

# A small horizontal margin so glyph edges never touch the frame border.
FRAME_SAFE_WIDTH: float = DESIGN_FRAME_WIDTH - 0.6


def fit_width(mobj, max_width: float = FRAME_SAFE_WIDTH):
    """Scale ``mobj`` down to ``max_width`` if it is wider; otherwise no-op.

    Returns the same mobject so calls can be chained."""
    if mobj.width > max_width:
        mobj.scale_to_fit_width(max_width)
    return mobj


def fit_group(group, max_width: float = FRAME_SAFE_WIDTH):
    """Scale a whole group down uniformly so its width fits ``max_width``,
    preserving the relative sizes of its members."""
    if group.width > max_width:
        group.scale_to_fit_width(max_width)
    return group


def wrapped_text(value: str, *, max_width: float, font_size: int, **text_kwargs) -> Text:
    """Wrap at measured glyph widths, retaining the requested font size.

    Manim does not wrap ``Text`` automatically. Measuring the actual font also
    handles CJK and mixed Latin text more reliably than character-count limits.
    """
    source = str(value)

    def width(s: str) -> float:
        return Text(s, font_size=font_size, **text_kwargs).width

    lines: list[str] = []
    for paragraph in source.split("\n"):
        remaining = paragraph
        if not remaining:
            lines.append("")
            continue
        while remaining:
            if width(remaining) <= max_width:
                lines.append(remaining)
                break
            low, high = 1, len(remaining)
            while low < high:
                middle = (low + high + 1) // 2
                if width(remaining[:middle]) <= max_width:
                    low = middle
                else:
                    high = middle - 1
            end = low
            # Keep English words whole when a space is available on this line.
            space = remaining.rfind(" ", 0, end + 1)
            if space > 0:
                end = space
                lines.append(remaining[:end])
                remaining = remaining[end + 1:]
            else:
                lines.append(remaining[:end])
                remaining = remaining[end:]
    result = Text("\n".join(lines), font_size=font_size,
                  line_spacing=0.2, **text_kwargs)
    return fit_width(result, max_width)
