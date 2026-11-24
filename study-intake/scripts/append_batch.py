# -*- coding: utf-8 -*-
"""把一批新照片追加进两个清单：主版（裁切件）+ 未裁剪版（原件）。

用法:
    python append_batch.py --manifest 课件清单.json --raw-manifest 课件清单_未裁剪.json \
        --crop-dir 照片裁切件5 --src-dir 照片原件5 --seg seg.json [--dry-run]

seg.json（时间段 → 分组名，看完缩略图墙后才定）:
    [["080136", "第四章 晶体缺陷 › 点缺陷与缺陷团簇（11-04 续）"],
     ["080354", "第四章 晶体缺陷 › 线缺陷：位错"]]

时间段取文件名里的 HHMMSS：IMG_20261104_080136.jpg → 080136。
新条目标题先写「第 0 页」，随后只在本批范围内改成真实页号；
老条目的真标题绝不会被覆盖。

安全:
    - 写之前自动备份成 <清单>.bak_<时间戳>
    - 两目录张数不一致、或有裁切件在原件里找不到对应 → 直接中止
    - 本批照片已在主清单里（同批跑了两次）→ 直接中止，确认要重复才加 --allow-dup
    - --dry-run 只打印分组分布，不写盘
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime

TS_RE = re.compile(r'_(\d{6})\.\w+$')


def stamp(name):
    m = TS_RE.search(name)
    return m.group(1) if m else ''


def group_of(name, seg):
    key = stamp(name)
    label = seg[0][1]
    for mark, lab in seg:
        if key >= mark:
            label = lab
    return label


def load_list(path, label, create=True):
    """清单不存在就建空清单——首次运行不该 FileNotFoundError。

    create=False（--dry-run）只返回空列表，绝不写盘。
    """
    if not os.path.exists(path):
        if create:
            json.dump([], open(path, 'w', encoding='utf-8'), ensure_ascii=False)
            print('新建空清单: %s（%s）' % (path, label))
        else:
            print('清单不存在（dry-run 不建）: %s（%s）' % (path, label))
        return []
    return json.load(open(path, encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True, help='主版清单（裁切件路径）')
    ap.add_argument('--raw-manifest', required=True, help='未裁剪版清单（原件路径）')
    ap.add_argument('--crop-dir', required=True, help='裁切件目录（相对清单所在目录或绝对路径）')
    ap.add_argument('--src-dir', required=True, help='原件目录')
    ap.add_argument('--seg', required=True, help='分段表 JSON：[[ "HHMMSS", "分组名" ], ...]')
    ap.add_argument('--dry-run', action='store_true', help='只打印分组，不写清单')
    ap.add_argument('--allow-dup', action='store_true',
                    help='允许本批照片已在主清单里（默认中止，防同批跑两次静默重复）')
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(a.manifest))
    crop_dir = a.crop_dir if os.path.isabs(a.crop_dir) else os.path.join(base, a.crop_dir)
    src_dir = a.src_dir if os.path.isabs(a.src_dir) else os.path.join(base, a.src_dir)
    seg_path = a.seg if os.path.isabs(a.seg) else os.path.join(base, a.seg)
    seg = json.load(open(seg_path, encoding='utf-8'))
    seg.sort(key=lambda x: x[0])
    if not seg:
        sys.exit('分段表为空')

    crop_files = sorted(f for f in os.listdir(crop_dir) if f.lower().endswith('.jpg'))
    raw_files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith('.jpg'))
    print('裁切件: %d 张 / 原件: %d 张' % (len(crop_files), len(raw_files)))
    if len(crop_files) != len(raw_files):
        sys.exit('⚠ 数量不一致，中止（先查有没有漏裁/漏拷）')
    missing = [f for f in crop_files if f not in set(raw_files)]
    if missing:
        sys.exit('⚠ %d 张裁切件在原件里找不到对应，中止：%s' % (len(missing), missing[:5]))

    main_list = load_list(a.manifest, '主清单', create=not a.dry_run)
    raw_list = load_list(a.raw_manifest, '未裁剪清单', create=not a.dry_run)
    n0m, n0r = len(main_list), len(raw_list)
    print('追加前: 主清单 %d 条 / 未裁剪 %d 条' % (n0m, n0r))

    # 主清单重叠检测：同批照片已在清单里，多半是同一批跑了两次
    have = set()
    for it in main_list:
        f = it.get('file', '')
        if isinstance(f, str) and f:
            have.add(f)
            have.add(f.replace('\\', '/'))
    dup = [f for f in crop_files
           if ('%s/%s' % (a.crop_dir, f)) in have or ('%s/%s' % (a.crop_dir.rstrip('/'), f)) in have]
    if dup:
        msg = '⚠ 本批有 %d 张已在主清单里（多半是同一批跑了两次）：%s' % (len(dup), dup[:5])
        if a.allow_dup:
            print(msg + '\n  --allow-dup 已指定，继续追加')
        else:
            sys.exit(msg + '\n  确认要重复追加才加 --allow-dup；否则先查 .bak_<时间戳> 并回滚')

    for f in crop_files:
        g = group_of(f, seg)
        main_list.append({'file': '%s/%s' % (a.crop_dir, f), 'title': '第 0 页', 'group': g})
        raw_list.append({'file': '%s/%s' % (a.src_dir, f), 'title': '第 0 页', 'group': g})

    for lst, n0 in ((main_list, n0m), (raw_list, n0r)):
        for i in range(n0, len(lst)):
            if lst[i]['title'] == '第 0 页':
                lst[i]['title'] = '第 %d 页' % (i + 1)

    groups = Counter(it['group'] for it in main_list[n0m:])
    print('\n=== 本批分组（共 %d 条）===' % (len(main_list) - n0m))
    for g, n in groups.items():
        print('  %-52s %d 页' % (g, n))
    if a.dry_run:
        print('\n[dry-run] 未写盘。确认分组无误后去掉 --dry-run 重跑。')
        return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    for p in (a.manifest, a.raw_manifest):
        shutil.copy2(p, p + '.bak_' + ts)
    json.dump(main_list, open(a.manifest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(raw_list, open(a.raw_manifest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n已备份 .bak_%s' % ts)
    print('追加后: 主清单 %d 条 / 未裁剪 %d 条' % (len(main_list), len(raw_list)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
