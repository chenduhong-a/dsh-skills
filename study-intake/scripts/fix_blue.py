# -*- coding: utf-8 -*-
"""深色底幻灯片的补裁：灰度阈值会把深蓝/深绿屏幕判成暗区，改用饱和度 + 亮度双通道。

用法:
    python fix_blue.py <源目录> <目标目录> <文件名...>
    python fix_blue.py <源目录> <目标目录> --all     # 整个目录都重裁

输出:
    裁切件写进 <目标目录>
    预览（带红框，缩到宽 800）写进 <目标目录的父目录>/_fixprev/
    必须 read_image 看预览，确认红框贴住屏幕、没包进观众人头

判据:
    连通域面积 < 全图 15% → 判失败（说明这不是一块完整的彩色屏幕）

什么时候用:
    crop_portrait.py 报告里 areaPct < 15%、ratio > 3 的那几张 —— 典型是深蓝底 PPT。
"""
import os
import sys

import cv2
import numpy as np

AN = 1024
MARGIN = 0.008


def blue_box(bgr_small):
    hsv = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)
    gray = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2GRAY)
    mask = (((s > 80) & (v > 70)) | (gray >= 205)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    H, W = gray.shape
    if w * h < W * H * 0.15:
        return None
    return x, y, w, h


def main(src, out, names):
    os.makedirs(out, exist_ok=True)
    prev = os.path.join(os.path.dirname(os.path.abspath(out)), '_fixprev')
    os.makedirs(prev, exist_ok=True)
    ok = 0
    for name in names:
        im = cv2.imdecode(np.fromfile(os.path.join(src, name), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            print('%-30s ✗ 读不出' % name)
            continue
        H, W = im.shape[:2]
        sc = AN / max(W, H)
        small = cv2.resize(im, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA)
        box = blue_box(small)
        if box is None:
            print('%-30s ✗ 检测失败（可能不是整块彩色屏，手工裁）' % name)
            continue
        x, y, w, h = box
        inv = 1 / sc
        m = int(round(max(W, H) * MARGIN))
        x0, y0 = max(0, int(x * inv) - m), max(0, int(y * inv) - m)
        x1, y1 = min(W, int((x + w) * inv) + m), min(H, int((y + h) * inv) + m)
        cv2.imencode('.jpg', im[y0:y1, x0:x1],
                     [int(cv2.IMWRITE_JPEG_QUALITY), 95])[1].tofile(os.path.join(out, name))
        pv = small.copy()
        cv2.rectangle(pv, (x, y), (x + w, y + h), (0, 0, 255), 3)
        pvis = cv2.resize(pv, (800, int(800 * pv.shape[0] / pv.shape[1])))
        cv2.imencode('.jpg', pvis)[1].tofile(
            os.path.join(prev, os.path.splitext(name)[0] + '_preview.jpg'))
        cw, ch = x1 - x0, y1 - y0
        ok += 1
        print('%-30s 框 %4d,%4d %4dx%-4d → 裁 %4dx%-4d  ratio=%.2f area=%.1f%%' % (
            name, x, y, w, h, cw, ch, cw / ch, cw * ch / (W * H) * 100))
    print('\n成功 %d / 共 %d；预览在 %s' % (ok, len(names), prev))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    src, out = sys.argv[1], sys.argv[2]
    if sys.argv[3] == '--all':
        names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.jpg', '.jpeg', '.png')))
    else:
        names = sys.argv[3:]
    main(src, out, names)
