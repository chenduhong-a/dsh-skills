# -*- coding: utf-8 -*-
"""竖拍投影幕裁切：找出屏幕矩形，温和去暗边后裁出。

用法:
    python crop_portrait.py <源目录> <目标目录> [报告json]

算法（经 92 张 + 89 张两批实测）:
    长边 1024 → Otsu 与亮区均值折中阈值 → 闭运算连碎片 → 最大轮廓外接框
    → 按 0.8% 留白裁 → JPEG q95 原始字节写盘（imencode + tofile，避开中文路径坑）

判据:
    - 框宽 < 图宽 20% 或 框高 < 图高 10% → 判失败
    - 报告里 areaPct < 15% 或 ratio > 3 的，多半是深色底幻灯片，改用 fix_blue.py
"""
import json
import os
import sys

import cv2
import numpy as np

AN = 1024          # 分析用长边
MARGIN = 0.008     # 留白比例


def screen_box(gray_small):
    blur = cv2.GaussianBlur(gray_small, (5, 5), 0)
    otsu_val, otsu_img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = blur[otsu_img > 0]
    bright_mean = float(bright.mean()) if bright.size else float(otsu_val)
    thr = int(max(otsu_val * 0.95, bright_mean * 0.55))
    mask = (blur >= thr).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    if w < gray_small.shape[1] * 0.2 or h < gray_small.shape[0] * 0.1:
        return None
    return x, y, w, h


def main(src, out, report_path, names):
    os.makedirs(out, exist_ok=True)
    report = []
    for i, name in enumerate(names, 1):
        path = os.path.join(src, name)
        im = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            report.append({'f': name, 'ok': False, 'err': 'decode'})
            continue
        H, W = im.shape[:2]
        sc = AN / max(W, H)
        small = cv2.resize(im, (max(2, int(W * sc)), max(2, int(H * sc))),
                           interpolation=cv2.INTER_AREA)
        box = screen_box(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        if box is None:
            report.append({'f': name, 'ok': False, 'err': 'no-box', 'src': '%dx%d' % (W, H)})
            continue
        x, y, w, h = box
        inv = 1 / sc
        m = int(round(max(W, H) * MARGIN))
        x0, y0 = max(0, int(x * inv) - m), max(0, int(y * inv) - m)
        x1, y1 = min(W, int((x + w) * inv) + m), min(H, int((y + h) * inv) + m)
        crop = im[y0:y1, x0:x1]
        cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 95])[1].tofile(
            os.path.join(out, name))
        cw, ch = x1 - x0, y1 - y0
        report.append({'f': name, 'ok': True, 'src': '%dx%d' % (W, H),
                       'crop': '%dx%d' % (cw, ch), 'ratio': round(cw / ch, 2),
                       'areaPct': round(cw * ch / (W * H) * 100, 1)})
        if i % 10 == 0 or i == len(names):
            print('  %d/%d 已完成' % (i, len(names)), flush=True)

    with open(report_path, 'w', encoding='utf-8') as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)

    okn = sum(1 for r in report if r.get('ok'))
    bad = [r for r in report if not r.get('ok')]
    print('\n成功 %d / 共 %d' % (okn, len(report)))
    if bad:
        print('失败 %d 张:' % len(bad))
        for r in bad:
            print('  ', r['f'], r.get('err'))
    sus = [r for r in report if r.get('ok') and (r['ratio'] < 1.0 or r['ratio'] > 2.0)]
    if sus:
        print('宽高比可疑 %d 张（需人工看）:' % len(sus))
        for r in sus:
            print('  ', r['f'], r['crop'], 'ratio=%.2f' % r['ratio'])
    areas = [r['areaPct'] for r in report if r.get('ok')]
    if areas:
        print('面积占比 min/中位/max = %.1f%% / %.1f%% / %.1f%%' % (
            min(areas), sorted(areas)[len(areas) // 2], max(areas)))
        small_ones = [r for r in report if r.get('ok') and r['areaPct'] < 15]
        if small_ones:
            print('面积 <15%% 的 %d 张（多半是深色底幻灯片，试 fix_blue.py）:' % len(small_ones))
            for r in small_ones:
                print('  ', r['f'], '%.1f%%' % r['areaPct'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    src, out = sys.argv[1], sys.argv[2]
    report_path = (sys.argv[3] if len(sys.argv) > 3
                   else os.path.join(os.path.dirname(os.path.abspath(out)), '_crop_report.json'))
    names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.jpg', '.jpeg', '.png')))
    print('源 %s' % src)
    print('出 %s' % out)
    print('待处理 %d 张' % len(names))
    main(src, out, report_path, names)
