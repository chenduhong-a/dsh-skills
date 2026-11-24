# -*- coding: utf-8 -*-
"""把多个 PDF 按讲次合并成一本整册，并给每一讲加顶层书签。

用法:
    python merge_pdfs.py --out 高等量子力学_课件整理.pdf --dir _pdf \
        --pattern '^高量(\\d+)-(.+)\\.pdf$' --label '第{n}讲  {t}' --title '高等量子力学 课件整理'

pattern:
    第 1 个捕获组 = 排序键（按整数排），第 2 个（可选）= 标题。
    没有捕获组时，按文件名排序、标题取文件名（去扩展名）。
label:
    可用 {n}（排序键）与 {t}（标题）。

输出末尾报「总页数 / 体积 / 每讲起始页」，与各文件页数相加必须对得上。
"""
import argparse
import os
import re
import sys

from pypdf import PdfReader, PdfWriter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--dir', required=True, help='PDF 所在目录')
    ap.add_argument('--pattern', default=r'(.+)\.pdf$')
    ap.add_argument('--label', default='{t}')
    ap.add_argument('--title', default='课件整理')
    a = ap.parse_args()

    pat = re.compile(a.pattern, re.I)
    found = []
    for name in sorted(os.listdir(a.dir)):
        if not name.lower().endswith('.pdf'):
            continue
        m = pat.match(name)
        if not m:
            continue
        groups = m.groups()
        if len(groups) >= 2:
            key, title = groups[0], groups[1]
        elif len(groups) == 1:
            key, title = groups[0], os.path.splitext(name)[0]
        else:
            key, title = os.path.splitext(name)[0], os.path.splitext(name)[0]
        try:
            order = int(key)
        except ValueError:
            order = key
        found.append((order, title, os.path.join(a.dir, name)))
    found.sort(key=lambda x: x[0])
    if not found:
        sys.exit('没有匹配到 PDF，检查 --dir 与 --pattern')

    writer = PdfWriter()
    total = 0
    for no, title, path in found:
        reader = PdfReader(path)
        start = total
        for page in reader.pages:
            writer.add_page(page)
        total += len(reader.pages)
        writer.add_outline_item(a.label.format(n=no, t=title), start)
        print(f'  {str(no):>3}. {title:<28} {len(reader.pages):>4} 页  -> 起始页 {start + 1}')

    writer.add_metadata({'/Title': a.title, '/Producer': 'study-intake/merge_pdfs.py'})
    with open(a.out, 'wb') as f:
        writer.write(f)

    size = os.path.getsize(a.out) / 1024 / 1024
    print(f'\n共 {total} 页 / {len(found)} 份 / {size:.2f} MB')
    print('输出:', a.out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
