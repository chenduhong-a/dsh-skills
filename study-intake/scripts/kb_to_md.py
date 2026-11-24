# -*- coding: utf-8 -*-
"""把 kb.sqlite 里的一份课件转成 StudyHub 能收的 markdown 材料。

为什么需要这一步：StudyHub 的单份材料有两条上限——PDF 最多 200 页、文件最多 8 MB。
648 MB 的原图扫描课件两条都过不去，但 OCR 后的正文是按页存在 kb.sqlite 里的，
按章节切成几份 md 就能全部进库，而且每页自带 `PDF p.N` 锚点，回原页图用 kb.py page。

用法：
  python kb_to_md.py --course 固体理论 --rel 固体理论/固体理论_课件整理.pdf --out D:\\tmp\\md
  python kb_to_md.py --doc-id 37 --out D:\\tmp\\md --max-bytes 6000000
  python kb_to_md.py --course 高等量子力学 --list        # 只列这门课有哪些 doc

默认每个 section 一份 md；section 为空、或者一份超过 --max-bytes 时自动按页再切。
"""
import argparse
import io
import os
import re
import sqlite3
import sys

KB_DB = os.environ.get("STUDY_KB_DB", r"C:\deepseek\study\_kb\kb.sqlite")
DEFAULT_MAX_BYTES = 7_500_000  # StudyHub 单份 8 MB，留一点余量
BAD = re.compile(r'[\\/:*?"<>|]')


def bail(msg):
    print("✗ " + msg)
    raise SystemExit(1)


def open_db(path):
    if not os.path.exists(path):
        bail(f"找不到知识库 {path}（用 STUDY_KB_DB 换个路径）")
    return sqlite3.connect(path)


def course_id(con, name):
    row = con.execute("select id from courses where name=?", (name,)).fetchone()
    if not row:
        names = [r[0] for r in con.execute("select name from courses order by id")]
        bail(f"课程「{name}」不在库里。现有：{'、'.join(names) or '（空）'}")
    return row[0]


def list_docs(con, cid):
    rows = con.execute(
        "select d.id, d.rel_path, count(i.id) from docs d "
        "left join items i on i.doc_id=d.id where d.course_id=? group by d.id order by d.id",
        (cid,),
    ).fetchall()
    if not rows:
        bail("这门课在库里还没有任何文档")
    print("本课程下的文档：")
    for doc_id, rel, n in rows:
        print(f"  [{doc_id}] {n:>5} 条  {rel}")
    return rows


def pick_doc(con, cid, doc_id=None, rel=None):
    if doc_id:
        row = con.execute("select id, rel_path from docs where id=?", (doc_id,)).fetchone()
        if not row:
            bail(f"doc id {doc_id} 不存在")
        return row
    if rel:
        row = con.execute(
            "select id, rel_path from docs where rel_path=? and course_id=?", (rel, cid)
        ).fetchone()
        if not row:
            bail(f"课程下找不到 rel_path={rel}；先跑 --list 看准确路径")
        return row
    rows = con.execute("select id, rel_path from docs where course_id=?", (cid,)).fetchall()
    if len(rows) == 1:
        return rows[0]
    bail("这门课有多份文档，请用 --rel 或 --doc-id 指定（先跑 --list）")


def sanitize(name, fallback):
    s = BAD.sub("-", (name or "").strip()) or fallback
    return s[:90]


def chunk_pages(pages, max_bytes):
    """一组页超过 max_bytes 时，按累计字节再切。"""
    out, cur, size = [], [], 0
    for p in pages:
        n = len(p["text"].encode("utf-8")) + 80
        if cur and size + n > max_bytes:
            out.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += n
    if cur:
        out.append(cur)
    return out


def render_block(course, doc_title, pages, span_label):
    buf = [
        f"# {doc_title} · {span_label}\n",
        f"> 来源：{course} 课件（OCR 正文，原 PDF 逐页对应）。"
        "每页标了原 PDF 页码，回原页图用 `kb.py page '<rel_path>' <页>`。\n",
    ]
    cur = object()
    for p in pages:
        if p["section"] != cur:
            cur = p["section"]
            buf.append(f"\n## {cur or '未分组'}\n")
        buf.append(f"\n### PDF p.{p['seq']} · {p['title'] or ''}\n\n{p['text'] or ''}\n")
    return "\n".join(buf)


def main():
    ap = argparse.ArgumentParser(description="kb.sqlite → StudyHub 材料 md")
    ap.add_argument("--course", help="课程名，用来定位 doc")
    ap.add_argument("--doc-id", type=int, help="直接指定 docs.id")
    ap.add_argument("--rel", help="直接指定 docs.rel_path（与 --course 一起用）")
    ap.add_argument("--out", help="输出目录（必需，除非只 --list）")
    ap.add_argument("--list", action="store_true", help="只列这门课的文档")
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                    help=f"单份上限，默认 {DEFAULT_MAX_BYTES}")
    ap.add_argument("--group", choices=["chapter", "full"], default="chapter",
                    help="chapter：按 section 的章级前缀归并（默认）；full：每个完整 section 一份")
    ap.add_argument("--db", default=KB_DB, help="知识库路径")
    args = ap.parse_args()

    con = open_db(args.db)
    if args.list:
        if not args.course:
            bail("--list 需要 --course")
        list_docs(con, course_id(con, args.course))
        return 0

    if not args.out:
        bail("需要 --out 指定输出目录")
    if args.doc_id:
        doc_id = args.doc_id
        row = con.execute("select course_id, rel_path from docs where id=?", (doc_id,)).fetchone()
        if not row:
            bail(f"doc id {doc_id} 不存在")
        cid, rel = row
        course = con.execute("select name from courses where id=?", (cid,)).fetchone()[0]
    else:
        if not args.course:
            bail("需要 --course（或 --doc-id）")
        course = args.course
        cid = course_id(con, course)
        doc_id, rel = pick_doc(con, cid, None, args.rel)
    # docs 表没有 title 列，标题按 rel_path 的文件名推
    doc_title = os.path.splitext(os.path.basename(rel or f"doc{doc_id}"))[0]

    rows = con.execute(
        "select seq, title, section, text from items where doc_id=? order by seq", (doc_id,)
    ).fetchall()
    if not rows:
        bail("这份文档没有任何条目")
    pages = [{"seq": r[0], "title": r[1], "section": r[2], "text": r[3] or ""} for r in rows]

    # 分组键：section 形如「第三章 晶格振动 › §3.1 一维晶格的振动」
    # chapter 模式取第一个「›」之前的章名，full 模式用整段
    def group_key(section):
        s = (section or "").strip()
        if not s:
            return ""
        if args.group == "chapter" and "›" in s:
            return s.split("›", 1)[0].strip()
        return s

    groups, order = {}, []
    for p in pages:
        key = group_key(p["section"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)

    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(rel or doc_title))[0] or f"doc{doc_id}"
    written = []
    for i, key in enumerate(order, 1):
        bucket = groups[key]
        lo, hi = bucket[0]["seq"], bucket[-1]["seq"]
        label = key or f"第{i}部分"
        for part in chunk_pages(bucket, args.max_bytes):
            plo, phi = part[0]["seq"], part[-1]["seq"]
            span = f"（p{plo}-{phi}）" if (plo, phi) != (lo, hi) else f"（p{lo}-{hi}）"
            name = sanitize(f"{course} {base} {label}{span}", f"part{i}") + ".md"
            text = render_block(course, f"{doc_title} · {label}", part, f"p{plo}-{phi}")
            path = os.path.join(args.out, name)
            io.open(path, "w", encoding="utf-8", newline="\n").write(text)
            size = os.path.getsize(path)
            written.append((name, len(part), size))
            flag = "  !! 超过上限" if size > args.max_bytes else ""
            print(f"{len(written):>2}. {len(part):>4} 页  {size/1024:>7.1f} KB  {name}{flag}")

    total = sum(w[2] for w in written)
    print(f"\n共 {len(written)} 份 / {len(pages)} 页 / {total/1024/1024:.2f} MB → {args.out}")
    print("下一步：逐份 document.import（course 同名），md 每份只会生成 1 个 source。")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
