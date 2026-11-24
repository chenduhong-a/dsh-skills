# -*- coding: utf-8 -*-
"""校验 PDF 内嵌的 JPEG 字节与清单顺序逐页一致（最强的一条顺序验收）。

用法:
    python verify_order.py <清单.json> <pdf>

原理:
    build_pdf.py 用 DCTDecode 原样内嵌 JPEG，所以可以把 PDF 里每个图像流的字节
    取出来，与清单第 i 条图片文件的字节做 SHA256 比对——全部相等才说明
    「页序 = 清单序、且画面没有被重新编码」。

输出:
    每页 mismatch 明细 + 最后一行 PASS / FAIL
"""
import hashlib
import json
import os
import re
import sys

PAT = re.compile(rb'/Subtype /Image /Width (\d+) /Height (\d+) [^>]*?/Length (\d+) >>\nstream\n', re.S)


def main(list_path, pdf_path):
    base = os.path.dirname(os.path.abspath(list_path))
    items = json.load(open(list_path, encoding='utf-8'))
    raw = open(pdf_path, 'rb').read()

    embedded = []
    for m in PAT.finditer(raw):
        start, length = m.end(), int(m.group(3))
        embedded.append(raw[start:start + length])
    print('PDF 内嵌图像: %d / 清单条目: %d' % (len(embedded), len(items)))

    bad = 0
    for i, it in enumerate(items):
        p = os.path.join(base, it['file'])
        if not os.path.exists(p):
            print('  MISSING page %d: %s' % (i + 1, it['file']))
            bad += 1
            continue
        src = open(p, 'rb').read()
        if i >= len(embedded):
            print('  PDF 短了：缺第 %d 页 %s' % (i + 1, it['file']))
            bad += 1
            continue
        if hashlib.sha256(src).digest() != hashlib.sha256(embedded[i]).digest():
            print('  MISMATCH page %d: %s' % (i + 1, it['file']))
            bad += 1

    if len(embedded) > len(items):
        print('  PDF 多出 %d 张图（末尾多余页）' % (len(embedded) - len(items)))
        bad += len(embedded) - len(items)

    print('order + bytes identical:', 'PASS' if bad == 0 else 'FAIL (%d 处)' % bad)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
