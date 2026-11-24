# -*- coding: utf-8 -*-
"""把一目录图片拼成缩略图墙，供目视验收（默认 5×4 = 20 格一张）。

用法:
    python make_sheet.py <源目录> <输出目录> [文件名前缀]

每格下方标注「序号 + 文件名中段」，一眼能对上原件。
生成完必须逐墙 read_image：内容是否完整、有没有裁掉半行、有没有把观众人头当屏幕。
"""
import math
import os
import sys

from PIL import Image, ImageDraw

COLS, ROWS = 5, 4
CELL = 340
PAD = 6
LABEL_H = 22


def main(src, out, prefix):
    os.makedirs(out, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
    per = COLS * ROWS
    n_sheets = math.ceil(len(files) / per)
    print('共 %d 张 → %d 张墙（%dx%d）' % (len(files), n_sheets, COLS, ROWS))

    for si in range(n_sheets):
        chunk = files[si * per:(si + 1) * per]
        ratios, imgs = [], []
        for f in chunk:
            try:
                im = Image.open(os.path.join(src, f)).convert('RGB')
            except Exception:
                continue
            ratios.append(im.size[0] / im.size[1])
            imgs.append((f, im))
        if not imgs:
            continue
        rmin = min(ratios) if ratios else 1.0
        CH = int(CELL / max(rmin, 0.6))
        CH = max(240, min(CH, int(CELL / 1.6) + 200))
        W = COLS * CELL + (COLS + 1) * PAD
        H = ROWS * (CH + LABEL_H) + (ROWS + 1) * PAD
        sheet = Image.new('RGB', (W, H), (250, 248, 243))
        dr = ImageDraw.Draw(sheet)
        for idx, (f, im) in enumerate(imgs):
            r, c = divmod(idx, COLS)
            x = PAD + c * (CELL + PAD)
            y = PAD + r * (CH + LABEL_H + PAD)
            im.thumbnail((CELL, CH), Image.LANCZOS)
            sheet.paste(im, (x + (CELL - im.size[0]) // 2, y + (CH - im.size[1]) // 2))
            dr.rectangle([x, y, x + CELL, y + CH], outline=(200, 195, 185))
            dr.text((x + 2, y + CH + 4), '%02d %s' % (si * per + idx + 1, f[5:24]),
                    fill=(90, 88, 82))
        p = os.path.join(out, '%s_%02d.jpg' % (prefix, si + 1))
        sheet.save(p, quality=88)
        print('  %s  (%d 张, %dx%d)' % (p, len(imgs), W, H))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'sheet')
