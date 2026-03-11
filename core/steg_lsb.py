from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Tuple

from PIL import Image


@dataclass
class StegParams:
    bits_per_channel: int = 1  # 1..2 rekomenduoju; 1 = saugiau vizualiai


def _bytes_to_bits(data: bytes):
    for b in data:
        for i in range(7, -1, -1):
            yield (b >> i) & 1


def _bits_to_bytes(bits):
    out = bytearray()
    acc = 0
    n = 0
    for bit in bits:
        acc = (acc << 1) | (bit & 1)
        n += 1
        if n == 8:
            out.append(acc)
            acc = 0
            n = 0
    return bytes(out)


def capacity_bytes(img: Image.Image, params: StegParams) -> int:
    # RGB channels only
    w, h = img.size
    bits_total = w * h * 3 * params.bits_per_channel
    return bits_total // 8 - 4  # minus 4 bytes length header


def embed_text(img: Image.Image, text: str, params: StegParams) -> Image.Image:
    if params.bits_per_channel < 1 or params.bits_per_channel > 2:
        raise ValueError("bits_per_channel must be 1 or 2")

    payload = text.encode("utf-8")
    header = struct.pack(">I", len(payload))
    data = header + payload

    im = img.convert("RGB")
    pixels = list(im.getdata())  # type: ignore[arg-type]

    cap = (im.size[0] * im.size[1] * 3 * params.bits_per_channel) // 8
    if len(data) > cap:
        raise ValueError(
            f"Message too large. Need {len(data)} bytes, capacity {cap} bytes.")

    bit_iter = _bytes_to_bits(data)
    new_pixels = []

    mask = (1 << params.bits_per_channel) - 1
    clear_mask = 0xFF ^ mask

    try:
        for (r, g, b) in pixels:
            chans = [r, g, b]
            for ci in range(3):
                val = chans[ci]
                val = val & clear_mask
                # write bits_per_channel bits
                write_val = 0
                for _ in range(params.bits_per_channel):
                    write_val = (write_val << 1) | next(bit_iter)
                chans[ci] = val | write_val
            new_pixels.append(tuple(chans))
    except StopIteration:
        # No more bits to write; keep the rest unchanged
        new_pixels.extend(pixels[len(new_pixels):])

    out = Image.new("RGB", im.size)
    out.putdata(new_pixels)
    return out


def extract_text(img: Image.Image, params: StegParams) -> str:
    if params.bits_per_channel < 1 or params.bits_per_channel > 2:
        raise ValueError("bits_per_channel must be 1 or 2")

    im = img.convert("RGB")
    pixels = list(im.getdata())  # type: ignore[arg-type]

    mask = (1 << params.bits_per_channel) - 1

    bits = []
    for (r, g, b) in pixels:
        for val in (r, g, b):
            # read bits_per_channel bits (MSB-first as written)
            for i in range(params.bits_per_channel - 1, -1, -1):
                bits.append((val >> i) & 1)

    raw = _bits_to_bytes(bits)
    if len(raw) < 4:
        raise ValueError("Not enough data")

    msg_len = struct.unpack(">I", raw[:4])[0]
    msg_bytes = raw[4:4 + msg_len]
    return msg_bytes.decode("utf-8", errors="replace")


def clean_lsb(img: Image.Image, params: StegParams) -> Image.Image:
    """'Išvalytas' variantas: nulina LSB bits_per_channel RGB kanaluose visiems pikseliams."""
    im = img.convert("RGB")
    pixels = list(im.getdata())  # type: ignore[arg-type]

    mask = (1 << params.bits_per_channel) - 1
    clear_mask = 0xFF ^ mask

    new_pixels = []
    for (r, g, b) in pixels:
        new_pixels.append((r & clear_mask, g & clear_mask, b & clear_mask))

    out = Image.new("RGB", im.size)
    out.putdata(new_pixels)
    return out
