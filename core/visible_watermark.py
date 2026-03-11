from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

from PIL import Image, ImageEnhance


Position = Literal[
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
]


@dataclass
class VisibleParams:
    angle_deg: float = 0.0
    opacity: float = 0.35   # 0..1
    scale: float = 0.25     # watermark width relative to base width (0..1+)
    repeat: bool = False
    tile_spacing: int = 40
    position: Position = "bottom_right"


def _pos_xy(base_size: Tuple[int, int], wm_size: Tuple[int, int], pos: Position) -> Tuple[int, int]:
    bw, bh = base_size
    ww, wh = wm_size

    x_map = {
        "top_left": 0, "center_left": 0, "bottom_left": 0,
        "top_center": (bw - ww)//2, "center": (bw - ww)//2, "bottom_center": (bw - ww)//2,
        "top_right": bw - ww, "center_right": bw - ww, "bottom_right": bw - ww,
    }
    y_map = {
        "top_left": 0, "top_center": 0, "top_right": 0,
        "center_left": (bh - wh)//2, "center": (bh - wh)//2, "center_right": (bh - wh)//2,
        "bottom_left": bh - wh, "bottom_center": bh - wh, "bottom_right": bh - wh,
    }
    return int(x_map[pos]), int(y_map[pos])


def apply_visible_watermark(base: Image.Image, watermark: Image.Image, params: VisibleParams) -> Image.Image:
    base_rgba = base.convert("RGBA")

    # Scale watermark to target width
    target_w = max(1, int(base_rgba.size[0] * params.scale))
    wm_rgba = watermark.convert("RGBA")
    aspect = wm_rgba.size[1] / wm_rgba.size[0]
    wm_rgba = wm_rgba.resize((target_w, max(1, int(target_w * aspect))))

    # Rotate
    if abs(params.angle_deg) > 0.001:
        wm_rgba = wm_rgba.rotate(params.angle_deg, expand=True)

    # Opacity
    if params.opacity < 1.0:
        alpha = wm_rgba.split()[-1]
        alpha = ImageEnhance.Brightness(alpha).enhance(
            max(0.0, min(1.0, params.opacity)))
        wm_rgba.putalpha(alpha)

    out = base_rgba.copy()

    if params.repeat:
        step_x = wm_rgba.size[0] + max(0, int(params.tile_spacing))
        step_y = wm_rgba.size[1] + max(0, int(params.tile_spacing))
        for y in range(0, out.size[1], step_y):
            for x in range(0, out.size[0], step_x):
                out.alpha_composite(wm_rgba, (x, y))
    else:
        x, y = _pos_xy(out.size, wm_rgba.size, params.position)
        out.alpha_composite(wm_rgba, (x, y))

    return out
