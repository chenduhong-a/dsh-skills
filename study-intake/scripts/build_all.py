# -*- coding: utf-8 -*-
"""一次重建三件套：主版（裁切件）/ 轻量版（长边 2000、q82）/ 未裁剪版（原件）。

用法:
    python build_all.py --dir . --name 固体理论 \
        --cropped 课件清单.json --raw 课件清单_未裁剪.json

产物（都在 --dir 下）:
    <name>_课件整理.pdf           主版
    <name>_课件整理_轻量版.pdf     验收与分发用（大文件工具只吃这个）
    <name>_课件整理_未裁剪版.pdf   原件对照版

三份页数必须相同；轻量版只缩分辨率，页序与清单完全一致。
"""
import argparse
import json
import os
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pdf import build  # noqa: E402

LONG_EDGE = 2000
QUALITY = 82


def make_light(cropped_list, base, tmp):
    with open(cropped_list, encoding='utf-8') as fp:
        items = json.load(fp)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    out = []
    for i, it in enumerate(items, 1):
        src = os.path.join(base, it['file'])
        name = f'{i:03d}.jpg'
        im = Image.open(src).convert('RGB')
        im.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)
        im.save(os.path.join(tmp, name), 'JPEG', quality=QUALITY, optimize=True)
        out.append({'file': name, 'title': it['title'], 'group': it['group']})
    lst = os.path.join(tmp, '_清单.json')
    with open(lst, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    return lst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='.', help='课程目录（清单与图片的基准，默认当前目录）')
    ap.add_argument('--name', required=True, help='产物前缀，如「固体理论」')
    ap.add_argument('--cropped', default='课件清单.json', help='主版清单')
    ap.add_argument('--raw', default='课件清单_未裁剪.json', help='未裁剪版清单')
    a = ap.parse_args()

    base = os.path.abspath(a.dir)
    c_list = os.path.join(base, a.cropped)
    r_list = os.path.join(base, a.raw)
    main_pdf = os.path.join(base, f'{a.name}_课件整理.pdf')
    light_pdf = os.path.join(base, f'{a.name}_课件整理_轻量版.pdf')
    raw_pdf = os.path.join(base, f'{a.name}_课件整理_未裁剪版.pdf')
    tmp = os.path.join(base, '_light_tmp')

    print('--- 主版 ---')
    build(c_list, main_pdf, f'{a.name} 课件整理')
    print('--- 轻量版 ---')
    build(make_light(c_list, base, tmp), light_pdf, f'{a.name} 课件整理（轻量版）')
    print('--- 未裁剪版 ---')
    build(r_list, raw_pdf, f'{a.name} 课件整理（未裁剪版）')
    shutil.rmtree(tmp, ignore_errors=True)

    n_c = len(json.load(open(c_list, encoding='utf-8')))
    n_r = len(json.load(open(r_list, encoding='utf-8')))
    if n_c != n_r:
        print(f'⚠ 两个清单条数不同：主版 {n_c} / 未裁剪 {n_r}')
    print(f'\ndone  清单 {n_c} 条  三份 PDF 页数应同为 {n_c}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
