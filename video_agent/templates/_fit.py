"""Keep template text inside the visible frame.

Manim clips any mobject wider than the logical frame, and CJK strings quickly
exceed it in the narrow 9:16 frame. Templates call these helpers so an
over-long heading/line shrinks to fit instead of being cut off.
"""
from __future__ import annotations

from ..render import DESIGN_FRAME_WIDTH

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