"""Assemble and package actual v6 Blender screenshots without editing geometry.

Run after all ten 1200x1200 PNGs are complete:
    python3 assemble_sides.py
Requires Pillow and a Chinese font. Never writes to the parent model directory.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import tempfile
import zipfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BG = (40, 47, 57)
INK = (245, 243, 239)
MUTED = (203, 213, 225)
SIDES = [
    ('v6-left-front-side.png', '左侧 · 前斜'),
    ('v6-left-side.png', '左侧 · 正侧'),
    ('v6-left-rear-side.png', '左侧 · 后斜'),
    ('v6-right-front-side.png', '右侧 · 前斜'),
    ('v6-right-side.png', '右侧 · 正侧'),
    ('v6-right-rear-side.png', '右侧 · 后斜'),
]
EARS = [
    ('v6-left-ear-front.png', '左耳 · 前侧近景'),
    ('v6-left-ear-rear.png', '左耳 · 后侧近景'),
    ('v6-right-ear-front.png', '右耳 · 前侧近景'),
    ('v6-right-ear-rear.png', '右耳 · 后侧近景'),
]
ARCHIVE = 'march7-v6-side-views.zip'
CHECKS = 'side-view-checksums.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def model_hashes():
    names = ('march7-bjd-head-v0.6-draft.blend',
             'march7-head-shell-v0.6-draft.stl',
             'march7-head-cap-v0.6-draft.stl')
    missing = [name for name in names if not (ROOT.parent / name).is_file()]
    if missing:
        raise FileNotFoundError('Cannot verify unchanged v6 model files: ' + ', '.join(missing))
    return {name: file_sha(ROOT.parent / name) for name in names}


def find_font(requested):
    candidates = [Path(requested)] if requested else [
        Path('/System/Library/Fonts/STHeiti Medium.ttc'),
        Path('/System/Library/Fonts/Hiragino Sans GB.ttc'),
        Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
        Path('C:/Windows/Fonts/msyh.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
    ]
    for path in candidates:
        if path.is_file():
            ImageFont.truetype(str(path), 32)
            return path
    raise FileNotFoundError('Chinese font unavailable; supply --font /path/to/font.ttf')


def load_originals():
    items = SIDES + EARS
    missing = [name for name, _ in items if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError('Render all ten images before assembling. Missing:\n' + '\n'.join(missing))
    images, records = {}, {}
    for name, label in items:
        data = (ROOT / name).read_bytes()
        with Image.open(io.BytesIO(data)) as image:
            image.load()  # Reject incomplete renders before publishing anything.
            if image.format != 'PNG' or image.size != (1200, 1200):
                raise ValueError(f'{name}: expected a complete 1200x1200 PNG, got {image.format} {image.size}')
            rgba = image.convert('RGBA')
            rgb = Image.new('RGBA', rgba.size, (*BG, 255))
            rgb.alpha_composite(rgba)
            images[name] = rgb.convert('RGB')
        records[name] = {'sha256': sha(data), 'bytes': len(data),
                         'width': 1200, 'height': 1200, 'label_zh': label,
                         'role': 'original_render'}
    return images, records


def make_board(images, font_path, items, size, columns, tile, x0, y0, xgap,
               row_step, title, subtitle, footer):
    board = Image.new('RGB', size, BG)
    draw = ImageDraw.Draw(board)
    def font(px):
        return ImageFont.truetype(str(font_path), px)
    draw.text((30, 18), title, font=font(44), fill=INK)
    draw.text((32, 78), subtitle, font=font(25), fill=MUTED)
    for i, (name, label) in enumerate(items):
        x = x0 + (i % columns) * (tile + xgap)
        y = y0 + (i // columns) * row_step
        # Square originals are uniformly resized, without cropping, mirroring,
        # retouching, changing camera projection, or generating image content.
        board.paste(images[name].resize((tile, tile), Image.Resampling.LANCZOS), (x, y))
        f = font(32)
        box = draw.textbbox((0, 0), label, font=f)
        tx = x + (tile - (box[2] - box[0])) / 2 - box[0]
        draw.text((tx, y + tile + 7), label, font=f, fill=INK)
    draw.text((30, size[1] - 29), footer, font=font(20), fill=MUTED)
    return board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', help='Chinese font file; macOS STHeiti is detected by default.')
    args = parser.parse_args()
    font_path = find_font(args.font)
    before_models = model_hashes()
    images, records = load_originals()
    boards = {
        'all-side-views.png': make_board(
            images, font_path, SIDES, (2100, 1600), 3, 666, 30, 120, 21, 738,
            '三月七四分 BJD · v6 侧面六视图',
            '真实几何渲染  /  上排：左侧  /  下排：右侧',
            '同一 v6 模型，仅新增截图；每个角度另附 1200 × 1200 原图。'),
        'ear-closeups.png': make_board(
            images, font_path, EARS, (1800, 1960), 2, 840, 48, 120, 24, 906,
            '三月七四分 BJD · v6 耳部近景',
            '真实几何渲染  /  上排：左耳  /  下排：右耳',
            '拼图仅作等比例缩放与排版，未修形；近景用于观察耳廓与侧脑壳衔接。'),
    }
    readme = '''# v6 侧面截图

本文件夹只新增同一 v6 娃头的真实 Blender 几何渲染截图，未修改 v6 Blender、STL 或尺寸。

- all-side-views.png：六视图，上排左侧、下排右侧；每排依次为前斜、正侧、后斜。
- ear-closeups.png：四张耳部近景，上排左耳、下排右耳；每排依次为前侧、后侧。
- 十张 v6-*.png：各方向独立原图，均为 1200×1200。
- march7-v6-side-views.zip：独立原图、两张拼图、本说明及校验文件。

拼图只做等比例缩放、排版和中文标注，不裁切、不镜像、不修形，也没有 AI 补画。近景与全头视图的画幅不同，不应跨图直接测量尺寸。

side-view-checksums.json 和 SHA256SUMS.txt 记录包内文件校验值；ZIP 的校验值另存于 march7-v6-side-views.zip.sha256。JSON 还记录组图前后保持不变的 v6 模型文件 SHA256。模型文件本身不放入截图 ZIP。

待全部十张原图渲染完成后，可用 `python3 assemble_sides.py` 重新生成拼图与截图包；需要 Pillow 和中文字体。脚本不会写入父目录的模型或原 manifest。
'''
    with tempfile.TemporaryDirectory(prefix='.assemble-sides-', dir=ROOT) as temp:
        stage = Path(temp)
        for name, board in boards.items():
            board.save(stage / name, format='PNG', compress_level=6)
            records[name] = {'sha256': file_sha(stage / name), 'bytes': (stage / name).stat().st_size,
                             'width': board.width, 'height': board.height, 'role': 'labeled_contact_sheet'}
        (stage / 'README.md').write_text(readme, encoding='utf-8')
        entries = {name: ROOT / name for name, _ in SIDES + EARS}
        entries.update({name: stage / name for name in boards})
        entries['README.md'] = stage / 'README.md'
        entries['assemble_sides.py'] = Path(__file__).resolve()
        for name in ('README.md', 'assemble_sides.py'):
            records[name] = {'sha256': file_sha(entries[name]), 'bytes': entries[name].stat().st_size,
                             'role': 'documentation' if name.endswith('.md') else 'assembly_script'}
        if any(file_sha(ROOT / name) != records[name]['sha256'] for name, _ in SIDES + EARS):
            raise RuntimeError('A source render changed during assembly; rerun after rendering is complete.')
        after_models = model_hashes()
        if before_models != after_models:
            raise RuntimeError('A v6 model changed during assembly; refusing to label this as an unchanged-model screenshot set.')
        manifest = {'description_zh': 'v6 真实几何渲染截图与拼图；模型未修改。',
                    'model_files_before_sha256': before_models,
                    'model_files_after_sha256': after_models,
                    'model_files_unchanged_during_assembly': True,
                    'assembly': 'Uniform image scaling and labels only; no crop, mirror or geometric retouching.',
                    'files': records,
                    'hash_scope': 'This JSON excludes its own hash and the ZIP hash to avoid circular checksums.'}
        (stage / CHECKS).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        entries[CHECKS] = stage / CHECKS
        sums = ''.join(f'{file_sha(path)}  {name}\n' for name, path in sorted(entries.items()))
        (stage / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
        entries['SHA256SUMS.txt'] = stage / 'SHA256SUMS.txt'
        with zipfile.ZipFile(stage / ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in sorted(entries.items()):
                archive.write(path, 'march7-v6-side-views/' + name)
        with zipfile.ZipFile(stage / ARCHIVE) as archive:
            failed = archive.testzip()
            if failed:
                raise RuntimeError('ZIP verification failed: ' + failed)
        archive_sha = file_sha(stage / ARCHIVE)
        (stage / (ARCHIVE + '.sha256')).write_text(f'{archive_sha}  {ARCHIVE}\n', encoding='utf-8')
        # Only explicitly named presentation/package files in side-views are
        # replaced. The original renders, model files and main manifest stay read-only.
        outputs = list(boards) + ['README.md', CHECKS, 'SHA256SUMS.txt', ARCHIVE, ARCHIVE + '.sha256']
        for name in outputs:
            os.replace(stage / name, ROOT / name)
    print(json.dumps({'outputs': [str(ROOT / name) for name in outputs],
                      'original_renders': len(SIDES + EARS),
                      'archive_sha256': archive_sha, 'model_files_unchanged': True},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
