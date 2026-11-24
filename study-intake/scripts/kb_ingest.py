# -*- coding: utf-8 -*-
r"""kb_ingest.py — 把一份 PDF 灌进 `_kb\kb.sqlite`（study-intake 技能 §4 入库段）。

两条路自动分派：
  · 有文字层 → pypdfium2 逐页直抽（快，几秒）
  · 无文字层（扫描/照片）→ 读 doc_ocr 的逐页缓存（需要先让会话对切分件跑 doc_ocr）

为什么要有这个脚本：`doc_ocr` 单文件上限是 **200 MB 字节**（不是页数），
六百多 MB 的照片课件必须按 ~100 页切；缓存落在
`%DSH_HOME%\storages\pdf-reader\<sha256前16位>\ocr\pNNN.json`（正文在 text 字段）；
手工 INSERT items 之后必须重建 FTS，否则 `kb.py find` 一条也搜不到。

用法
----
# 1) 先看要不要切、缓存齐不齐（不写库）
python kb_ingest.py split  --pdf "<成品.pdf>" --out "<切的临时目录>"

# 2) 对列出的每份未缓存切分件，在会话里调 doc_ocr（见输出里的提示）

# 3) 灌库（--dry-run 先看，--go 真写）
python kb_ingest.py ingest --pdf "<成品.pdf>" --course 固体理论 \
    --rel "固体理论/固体理论_课件整理.pdf" [--parts-dir "<切的临时目录>"] \
    [--titles "<课件清单.json>"] [--go]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KB_DB = os.environ.get("STUDY_KB_DB", r"C:\deepseek\study\_kb\kb.sqlite")
CACHE_ROOT = os.path.join(os.environ.get("DSH_HOME", r"C:\Users\ZQY\.dsh"), "storages", "pdf-reader")
LIMIT_BYTES = 190 * 1024 * 1024          # doc_ocr 实际阈值 200 MB，留余量
CHUNK_PAGES = 100                        # 照片类约 1.6 MB/页，100 页 ≈ 160 MB


# ---------------------------------------------------------------- 工具函数

def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def cache_dir(path: str) -> str:
    return os.path.join(CACHE_ROOT, sha256_file(path)[:16])


def cached_page_count(path: str) -> int:
    ocr = os.path.join(cache_dir(path), "ocr")
    if not os.path.isdir(ocr):
        return 0
    return len([f for f in os.listdir(ocr) if re.fullmatch(r"p\d{3}\.json", f)])


def has_text_layer(path: str, probe: int = 3) -> bool:
    """抽首/中/尾三页，平均字符数 > 60 视为有文字层。"""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print("!! pypdfium2 未安装，无法判断文字层，一律按扫描件处理（"
              "pip install pypdfium2）；有文字层的 PDF 会被误判，别在这台机器上信这条路径判断")
        return False
    pdf = pdfium.PdfDocument(path)
    n = len(pdf)
    picks = sorted({0, n // 2, n - 1})
    total = 0
    for i in picks:
        page = pdf[i]
        total += len(page.get_textpage().get_text_bounded() or "")
    pdf.close()
    return total / max(len(picks), 1) > 60


def split_pdf(path: str, out_dir: str) -> list[str]:
    import pypdf

    os.makedirs(out_dir, exist_ok=True)
    reader = pypdf.PdfReader(path)
    parts, start = [], 0
    while start < len(reader.pages):
        end = min(start + CHUNK_PAGES, len(reader.pages))
        writer = pypdf.PdfWriter()
        for p in range(start, end):
            writer.add_page(reader.pages[p])
        dst = os.path.join(out_dir, f"part_{start + 1}-{end}.pdf")
        with open(dst, "wb") as fh:
            writer.write(fh)
        parts.append(dst)
        start = end
    return parts


def pdf_pages(path: str) -> int:
    import pypdf
    return len(pypdf.PdfReader(path).pages)


def clean_text(text: str) -> str:
    """pypdfium2 直抽会带 \\r 与公式字体的私用区字符（U+E000–U+F8FF），先洗一遍。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def text_via_pdfium(path: str) -> list[str]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(path)
    out = []
    for i in range(len(pdf)):
        raw = pdf[i].get_textpage().get_text_bounded() or ""
        out.append(clean_text(raw))
    pdf.close()
    return out


def text_via_cache(parts: list[str]) -> list[str] | None:
    pages: list[str] = []
    for part in parts:
        ocr = os.path.join(cache_dir(part), "ocr")
        if not os.path.isdir(ocr):
            print(f"!! 没有缓存：{os.path.basename(part)}（要先对这份跑 doc_ocr）")
            return None
        files = sorted(f for f in os.listdir(ocr) if re.fullmatch(r"p\d{3}\.json", f))
        for f in files:
            data = json.load(io.open(os.path.join(ocr, f), encoding="utf-8"))
            pages.append(data.get("text") or data.get("markdown") or "")
    return pages


def load_titles(path: str | None) -> list[dict]:
    if not path:
        return []
    data = json.loads(io.open(path, encoding="utf-8-sig").read())
    if isinstance(data, dict):
        for key in ("items", "pages", "list"):
            if key in data:
                data = data[key]
                break
    return data if isinstance(data, list) else []


def rebuild_fts(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
    con.commit()


# ---------------------------------------------------------------- 子命令

def cmd_split(args) -> int:
    size = os.path.getsize(args.pdf)
    print(f"{os.path.basename(args.pdf)}  {size / 1024 / 1024:.1f} MB  {pdf_pages(args.pdf)} 页")
    if has_text_layer(args.pdf):
        print("有文字层 → 不需要 OCR，直接 ingest 即可")
        return 0
    if size <= LIMIT_BYTES:
        print(f"无文字层，但 {size / 1024 / 1024:.1f} MB ≤ 190 MB → 整份跑 doc_ocr：")
        print(f"  doc_ocr path={args.pdf}")
        return 0
    parts = split_pdf(args.pdf, args.out)
    print(f"已切 {len(parts)} 份 → {args.out}")
    todo = []
    for p in parts:
        n = cached_page_count(p)
        total = pdf_pages(p)
        mark = "已缓存" if n >= total else f"缺 {total - n} 页"
        print(f"  {os.path.basename(p):<22} {total:>4} 页  {os.path.getsize(p) / 1024 / 1024:>6.1f} MB  {mark}")
        if n < total:
            todo.append(p)
    for p in todo:
        print(f"  doc_ocr path={p} pages=1-{pdf_pages(p)}")
    return 0


def cmd_ingest(args) -> int:
    con = sqlite3.connect(KB_DB)
    cur = con.cursor()
    row = cur.execute("select id from courses where name=?", (args.course,)).fetchone()
    # dry-run 不落库：建课程带 commit，必须在写库分支之后（2026-11-22 bugintake 审出）
    if not row and args.go:
        cur.execute("insert or ignore into courses(name) values (?)", (args.course,))
        con.commit()
        row = cur.execute("select id from courses where name=?", (args.course,)).fetchone()
        print(f"课程不存在，已自动建：{args.course}")
    course_id = row[0] if row else None
    if not args.go:
        print(f"课程{'存在' if row else '不存在（--go 时自动建）'}：{args.course}")
    if cur.execute("select id from docs where rel_path=?", (args.rel,)).fetchone():
        print(f"!! rel_path 已存在：{args.rel}")
        return 1

    if has_text_layer(args.pdf):
        print("路径：文字层直抽")
        pages = text_via_pdfium(args.pdf)
    else:
        if not args.go:
            print("路径：OCR 缓存（dry-run 不切分、不写盘；加 --go 才切片并核对缓存）")
            return 0
        parts = split_pdf(args.pdf, args.parts_dir)
        print(f"路径：OCR 缓存（{len(parts)} 份切分件）")
        pages = text_via_cache(parts)
        if pages is None:
            print("!! 缓存不全，先对上面列出的切分件跑 doc_ocr，再回来 ingest")
            return 1

    titles = load_titles(args.titles)
    print(f"页数 {len(pages)}，标题源 {len(titles)} 条")
    if titles and len(titles) != len(pages):
        print("!! 页数与标题条数不一致，标题改为按页序截断/补空")
        titles = (titles + [{}] * len(pages))[: len(pages)]
    if not pages:
        print("!! 没有任何正文")
        return 1

    st = os.stat(args.pdf)
    stamp = __import__("datetime").date.today().isoformat()
    meta = json.dumps({"ocr": None if has_text_layer(args.pdf) else "mineru", "pages": len(pages)},
                      ensure_ascii=False)

    if not args.go:
        print("[dry-run] 将写入：")
        for i in (0, len(pages) // 2, len(pages) - 1):
            title = (titles[i].get("title") if titles else "") or f"第{i + 1}页"
            print(f"  p{i + 1}  {title[:36]!r}  {pages[i][:44].replace(chr(10), ' ')!r}")
        print(f"  共 {len(pages)} 条；confirm 后加 --go")
        return 0

    cur.execute(
        "insert into docs(course_id,kind,rel_path,bytes,sha256,mtime,meta) values(?,?,?,?,?,?,?)",
        (course_id, "pdf", args.rel, st.st_size, sha256_file(args.pdf), stamp, meta),
    )
    doc_id = cur.lastrowid
    for i, text in enumerate(pages, start=1):
        title = ((titles[i - 1].get("title") if titles else "") or "").strip() or f"第{i}页"
        section = ((titles[i - 1].get("group") if titles else "") or "").strip() or None
        cur.execute(
            "insert into items(doc_id,seq,title,section,text,markdown) values(?,?,?,?,?,?)",
            (doc_id, i, title, section, text, text),
        )
    con.commit()
    rebuild_fts(con)
    n = cur.execute("select count(*) from items where doc_id=?", (doc_id,)).fetchone()[0]
    print(f"已写入 doc id={doc_id} items={n}，FTS 已重建")
    print(f"验证：kb.cmd find <关键词> --course {args.course}（kb.cmd 是 _kb 根下入口，转发到 app\\kb.py）")
    con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="把 PDF 灌进 _kb\\kb.sqlite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("split", help="体检：要不要切、缓存齐不齐")
    sp.add_argument("--pdf", required=True)
    sp.add_argument("--out", default=r"C:\deepseek\study\work\_tmp\ingest_split")
    sp.set_defaults(func=cmd_split)

    ip = sub.add_parser("ingest", help="灌库（默认 dry-run）")
    ip.add_argument("--pdf", required=True)
    ip.add_argument("--course", required=True)
    ip.add_argument("--rel", required=True, help="如 固体理论/固体理论_课件整理.pdf")
    ip.add_argument("--parts-dir", default=r"C:\deepseek\study\work\_tmp\ingest_split")
    ip.add_argument("--titles", default=None, help="按页序给 title/group 的 JSON（如课件清单.json）")
    ip.add_argument("--go", action="store_true", help="真的写库")
    ip.set_defaults(func=cmd_ingest)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
