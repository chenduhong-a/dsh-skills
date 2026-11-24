# -*- coding: utf-8 -*-
"""把图片清单拼成 PDF：JPEG 原始字节直接内嵌（DCTDecode），不重编码、不损画质。

用法:
    python build_pdf.py <清单.json> <输出.pdf> [--title 标题]

清单格式（图片路径相对清单文件所在目录）:
    [{"file": "照片裁切件5/IMG_x.jpg", "title": "课程标题", "group": "章 › 节"}, ...]

书签:
    顶层 = group（连续相同的 group 自动归为一组），二级 = title。
    A4 版心 10pt 留白，图片按比例居中。
"""
import argparse
import json
import os
import sys

A4W, A4H = 595.28, 841.89
MARGIN = 10


def jpeg_size(path):
    with open(path, 'rb') as f:
        data = f.read()
    o, n = 2, len(data)
    while o < n - 1:
        if data[o] != 0xFF:
            o += 1
            continue
        m = data[o + 1]
        while m == 0xFF:
            o += 1
            m = data[o + 1]
        if 0xD0 <= m <= 0xD9:
            o += 2
            continue
        length = (data[o + 2] << 8) | data[o + 3]
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            h = (data[o + 5] << 8) | data[o + 6]
            w = (data[o + 7] << 8) | data[o + 8]
            return w, h, data
        o += 2 + length
    raise ValueError('no SOF marker: ' + path)


def pdf_string(s):
    return b'<FEFF' + s.encode('utf-16-be').hex().upper().encode('ascii') + b'>'


def content_stream(iw, ih):
    aw, ah = A4W - MARGIN * 2, A4H - MARGIN * 2
    s = min(aw / iw, ah / ih)
    dw, dh = iw * s, ih * s
    x, y = (A4W - dw) / 2, (A4H - dh) / 2
    return f'q {dw:.2f} 0 0 {dh:.2f} {x:.2f} {y:.2f} cm /Im0 Do Q'.encode('latin-1')


def build(list_path, out_path, title='课件整理'):
    base = os.path.dirname(os.path.abspath(list_path))
    with open(list_path, encoding='utf-8') as fp:
        items = json.load(fp)

    objects, page_refs, outlines = [], [], []

    def add(obj):
        objects.append(obj)
        return len(objects)

    catalog, pages_obj = add(None), add(None)
    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')

    for it in items:
        w, h, data = jpeg_size(os.path.join(base, it['file']))
        img = add((
            (f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} '
             f'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>'
             ).encode('latin-1'),
            data,
        ))
        cont = content_stream(w, h)
        cont_obj = add((f'<< /Length {len(cont)} >>'.encode('latin-1'), cont))
        page = add(None)
        objects[page - 1] = (
            f'<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {A4W} {A4H}] '
            f'/Resources << /XObject << /Im0 {img} 0 R >> /Font << /F1 {font} 0 R >> >> '
            f'/Contents {cont_obj} 0 R >>'
        ).encode('latin-1')
        page_refs.append(page)
        outlines.append({'title': it.get('title') or os.path.splitext(it['file'])[0],
                         'group': it.get('group') or '课件', 'page': page})

    objects[pages_obj - 1] = (
        f'<< /Type /Pages /Count {len(page_refs)} /Kids [' +
        ' '.join(f'{p} 0 R' for p in page_refs) + '] >>'
    ).encode('latin-1')

    groups = []
    for o in outlines:
        if not groups or groups[-1]['name'] != o['group']:
            groups.append({'name': o['group'], 'items': []})
        groups[-1]['items'].append(o)

    root = add(None)
    group_objs = [add(None) for _ in groups]
    for o in outlines:
        o['obj'] = add(None)

    for gi, g in enumerate(groups):
        parts = [f'/Title ' + pdf_string(g['name']).decode('latin-1') + f' /Parent {root} 0 R',
                 f'/First {g["items"][0]["obj"]} 0 R /Last {g["items"][-1]["obj"]} 0 R '
                 f'/Count {len(g["items"])}']
        if gi > 0:
            parts.append(f'/Prev {group_objs[gi-1]} 0 R')
        if gi < len(groups) - 1:
            parts.append(f'/Next {group_objs[gi+1]} 0 R')
        objects[group_objs[gi] - 1] = ('<< ' + ' '.join(parts) + ' >>').encode('latin-1')

    for i, o in enumerate(outlines):
        gi = next(k for k, g in enumerate(groups) if o in g['items'])
        parts = ['/Title ' + pdf_string(o['title']).decode('latin-1'),
                 f'/Parent {group_objs[gi]} 0 R']
        if i > 0:
            parts.append(f'/Prev {outlines[i-1]["obj"]} 0 R')
        if i < len(outlines) - 1:
            parts.append(f'/Next {outlines[i+1]["obj"]} 0 R')
        parts.append(f'/Dest [{o["page"]} 0 R /XYZ 0 {A4H} 0]')
        objects[o['obj'] - 1] = ('<< ' + ' '.join(parts) + ' >>').encode('latin-1')

    objects[root - 1] = (
        f'<< /Type /Outlines /First {group_objs[0]} 0 R /Last {group_objs[-1]} 0 R '
        f'/Count {len(group_objs) + len(outlines)} >>'
    ).encode('latin-1')
    objects[catalog - 1] = (
        f'<< /Type /Catalog /Pages {pages_obj} 0 R /Outlines {root} 0 R /PageLayout /SinglePage >>'
    ).encode('latin-1')

    info = add(('<< /Title ' + pdf_string(title).decode('latin-1') +
                ' /Producer (study-intake/build_pdf.py) /Creator (DeepSeek Harness) >>'
                ).encode('latin-1'))

    out = bytearray(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0] * len(objects)
    for idx, obj in enumerate(objects):
        offsets[idx] = len(out)
        out += f'{idx + 1} 0 obj\n'.encode('latin-1')
        if isinstance(obj, tuple):
            d, stream = obj
            out += d + b'\nstream\n' + stream + b'\nendstream'
        elif isinstance(obj, bytes):
            out += obj
        else:
            raise RuntimeError(f'object {idx + 1} unfilled')
        out += b'\nendobj\n'

    xref_pos = len(out)
    out += f'xref\n0 {len(objects) + 1}\n'.encode('latin-1')
    out += b'0000000000 65535 f \n'
    for off in offsets:
        out += f'{off:010d} 00000 n \n'.encode('latin-1')
    out += (f'trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\n'
            ).encode('latin-1')
    out += f'startxref\n{xref_pos}\n%%EOF\n'.encode('latin-1')

    with open(out_path, 'wb') as fp:
        fp.write(out)
    print('OK  pages=%d  objects=%d  size=%.1f MB' % (
        len(page_refs), len(objects), len(out) / 1048576))
    print('->', out_path)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('list')
    ap.add_argument('out')
    ap.add_argument('--title', default='课件整理')
    a = ap.parse_args()
    build(a.list, a.out, a.title)
