from __future__ import annotations

from datetime import datetime
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image


@dataclass
class ImageMeta:
    path: str
    file_size_bytes: int
    modified_time: float
    format: Optional[str]
    mode: str
    width: int
    height: int


def read_metadata(path: str) -> ImageMeta:
    p = Path(path)
    st = p.stat()
    with Image.open(p) as im:
        return ImageMeta(
            path=str(p),
            file_size_bytes=int(st.st_size),
            modified_time=float(st.st_mtime),
            format=im.format,
            mode=im.mode,
            width=int(im.size[0]),
            height=int(im.size[1]),
        )


def metadata_to_text(meta: ImageMeta) -> str:
    return (
        f"Path: {meta.path}\n"
        f"File size: {format_file_size(meta.file_size_bytes)} "
        f"({meta.file_size_bytes} bytes)\n"
        f"Modified (epoch): {format_timestamp(meta.modified_time)}\n"
        f"Format: {meta.format}\n"
        f"Mode: {meta.mode}\n"
        f"Size: {meta.width}x{meta.height}\n"
    )


def format_file_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024  # type: ignore
    return f"{num_bytes:.2f} TB"


def format_timestamp(epoch: float) -> str:
    dt = datetime.fromtimestamp(epoch)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
