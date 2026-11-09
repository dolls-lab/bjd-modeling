#!/usr/bin/env python3
"""Lay out the eight original renders without retouching or color adjustments.

Run after all eight PNG inputs exist beside this script:
    python assemble_gallery.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = Path("/System/Library/Fonts/STHeiti Medium.ttc")
CELL_SIZE = 600
MARGIN = 24
GUTTER = 16
HEADER_HEIGHT = 104
FOOTER_HEIGHT = 80
WIDTH = MARGIN * 2 + CELL_SIZE * 2 + GUTTER
HEIGHT = MARGIN * 2 + HEADER_HEIGHT + CELL_SIZE * 2 + GUTTER + FOOTER_HEIGHT
BACKGROUND = (28, 30, 34)
CELL_BACKGROUND = (37, 40, 45)
FOREGROUND = (239, 240, 242)
SECONDARY = (178, 183, 191)
FOOTER = "实际三维渲染 · 当前浅肤色模型 · 仅切换观察角度"

GALLERIES = (
    {
        "output": "face-angles.png",
        "title": "三月七浅肤色 · 面部与俯仰角度",
        "subtitle": "面部近景与正面俯仰 · 四个观察角度",
        "views": (
            ("face-front-close.png", "正面特写", "近距离观察面部整体"),
            ("face-quarter-close.png", "斜侧面特写", "斜侧视角观察面部轮廓"),
            ("front-high.png", "前斜侧俯视", "从较高视点观察面部与头部"),
            ("front-low.png", "前斜侧仰视", "从较低视点观察下颌与颈部"),
        ),
    },
    {
        "output": "head-angles.png",
        "title": "三月七浅肤色 · 侧后与头顶",
        "subtitle": "侧面、后方与顶部 · 四个观察角度",
        "views": (
            ("right-profile.png", "右侧面", "观察头部侧面与面部轮廓"),
            ("rear-quarter.png", "后侧视角", "从斜后方观察头部形态"),
            ("rear.png", "正后方", "观察头部与颈部的后方轮廓"),
            ("top.png", "头顶视角", "从顶部观察头部整体形态"),
        ),
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def put_text(draw: ImageDraw.ImageDraw, position: tuple[int, int], text: str,
             font: ImageFont.FreeTypeFont, color: tuple[int, int, int]) -> None:
    """Anchor text by its visible top left, independent of font bearing."""
    left, top, _, _ = draw.textbbox((0, 0), text, font=font)
    draw.text((position[0] - left, position[1] - top), text, font=font, fill=color)


def assemble(gallery: dict, fonts: dict) -> dict:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    put_text(draw, (MARGIN, MARGIN + 4), gallery["title"], fonts["heading"], FOREGROUND)
    put_text(draw, (MARGIN, MARGIN + 61), gallery["subtitle"], fonts["subtitle"], SECONDARY)
    inputs = []

    for index, (filename, title, subtitle) in enumerate(gallery["views"]):
        path = BASE_DIR / filename
        column, row = index % 2, index // 2
        x = MARGIN + column * (CELL_SIZE + GUTTER)
        y = MARGIN + HEADER_HEIGHT + row * (CELL_SIZE + GUTTER)
        draw.rectangle((x, y, x + CELL_SIZE - 1, y + CELL_SIZE - 1), fill=CELL_BACKGROUND)

        # Reserve the bottom of each 600 px cell for two Chinese label lines.
        # Scale the whole render uniformly; never crop, relight, or recolor it.
        image_box = (x + 18, y + 18, 564, 468)
        with Image.open(path) as source:
            source.load()
            original_size = source.size
            scale = min(image_box[2] / source.width, image_box[3] / source.height)
            size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
            scaled = source.resize(size, Image.Resampling.LANCZOS)
            image_x = image_box[0] + (image_box[2] - size[0]) // 2
            image_y = image_box[1] + (image_box[3] - size[1]) // 2
            if "A" in scaled.getbands() or "transparency" in scaled.info:
                rgba = scaled.convert("RGBA")
                canvas.paste(rgba, (image_x, image_y), rgba.getchannel("A"))
            else:
                canvas.paste(scaled, (image_x, image_y))

        put_text(draw, (x + 22, y + 506), title, fonts["label"], FOREGROUND)
        put_text(draw, (x + 22, y + 552), subtitle, fonts["subtitle"], SECONDARY)
        inputs.append({
            "path": str(path),
            "sha256": sha256(path),
            "original_dimensions_px": list(original_size),
            "display_dimensions_px": list(size),
            "image_position_px": [image_x, image_y],
            "cell_position": {"row": row + 1, "column": column + 1},
            "title": title,
            "subtitle": subtitle,
        })

    footer_y = MARGIN + HEADER_HEIGHT + CELL_SIZE * 2 + GUTTER + 30
    put_text(draw, (MARGIN, footer_y), FOOTER, fonts["footer"], SECONDARY)
    output_path = BASE_DIR / gallery["output"]
    canvas.save(output_path, format="PNG")
    return {
        "title": gallery["title"],
        "subtitle": gallery["subtitle"],
        "inputs": inputs,
        "output": {
            "path": str(output_path),
            "sha256": sha256(output_path),
            "dimensions_px": [WIDTH, HEIGHT],
        },
    }


def main() -> None:
    required = [BASE_DIR / name for gallery in GALLERIES for name, _, _ in gallery["views"]]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing input PNGs:\n" + "\n".join(missing))
    if not FONT_PATH.is_file():
        raise SystemExit(f"Required Chinese font is missing: {FONT_PATH}")

    fonts = {
        "heading": ImageFont.truetype(str(FONT_PATH), 42),
        "label": ImageFont.truetype(str(FONT_PATH), 31),
        "subtitle": ImageFont.truetype(str(FONT_PATH), 24),
        "footer": ImageFont.truetype(str(FONT_PATH), 24),
    }
    galleries = [assemble(gallery, fonts) for gallery in GALLERIES]
    provenance = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "font_path": str(FONT_PATH),
        "layout": {
            "rows": 2,
            "columns": 2,
            "cell_dimensions_px": [CELL_SIZE, CELL_SIZE],
            "background_rgb": list(BACKGROUND),
            "resize_filter": "Pillow LANCZOS",
            "operations": ["aspect-ratio-preserving resize", "centered placement", "Chinese labels"],
            "crop": False,
            "color_adjustment": False,
            "retouching": False,
        },
        "footer": FOOTER,
        "galleries": galleries,
    }
    provenance_path = BASE_DIR / "gallery-provenance.json"
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for gallery in galleries:
        print(gallery["output"]["path"])
    print(provenance_path)


if __name__ == "__main__":
    main()
