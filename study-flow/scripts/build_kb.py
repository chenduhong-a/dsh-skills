#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""建最小知识库：有文字层的 PDF → courses/docs/items + FTS5。

用法：
  python build_kb.py --db kb.sqlite --course 课程名 --pdf "教材.pdf"
  python build_kb.py --db kb.sqlite --course 课程名 --dir 课件_pdf --pattern "第*.pdf"
  python build_kb.py --db kb.sqlite --course 课程名 --pdf a.pdf --pages 1-120
  python build_kb.py --db kb.sqlite --list
  python build_kb.py --db kb.sqlite --check 声子 --course 课程名

只处理**有文字层**的 PDF；扫描件会报「需要先 OCR」并跳过——OCR 见 references/05-materials.md。
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import sqlite3
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

SCHEMA = """
create table if not exists courses (id integer primary key, name text unique);
create table if not exists docs (
  id integer primary key, course_id integer, rel_path text unique,
  pages integer, source text
);
create table if not exists items (
  id integer primary key, doc_id integer, page integer,
  title text, section text, text text
);
create virtual table if not exists items_fts using fts5(
  text, title, section, content='items', content_rowid='id'
);
"""
PRIVATE = re.compile(r"[\ue000-\uf8ff]")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECTION = re.compile(r"(第[一二三四五六七八九十百零\d]+章[^\n]{0,30}|§\s*\d+(?:\.\d+)*[^\n]{0,30})")


def clean(text: str) -> str:
    text = text.replace("\r", "\n")
    text = PRIVATE.sub("", text)
    text = CTRL.sub("", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def page_text_pdfium(path: str) -> list[str] | None:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    pdf = pdfium.PdfDocument(path)
    out = []
    for i in range(len(pdf)):
        page = pdf[i]
        if hasattr(page, "get_textpage"):
            out.append(page.get_textpage().get_text_range() or "")
        else:
            out.append(page.get_text_range() or "")
    return out


def page_text_pypdf(path: str) -> list[str] | None:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    reader = PdfReader(path)
    return [(p.extract_text() or "") for p in reader.pages]


def extract_pages(path: str) -> list[str]:
    pages = page_text_pdfium(path)
    if pages is None:
        pages = page_text_pypdf(path)
    if pages is None:
        raise RuntimeError("没有可用的 PDF 文本库：请 pip install pypdfium2 或 pypdf")
    return pages


def guess_title(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        return ""
    for line in lines[:6]:
        if 2 <= len(line) <= 80 and not re.fullmatch(r"[\d\s\-—.]+", line):
            return line
    return lines[0][:80]


def guess_section(text: str) -> str:
    m = SECTION.search(text[:600])
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse_pages(spec: str, total: int) -> tuple[int, int]:
    if not spec:
        return 1, total
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", spec.strip())
    if not m:
        raise SystemExit(f"--pages 格式应为 1-120 或 5：{spec}")
    a = int(m.group(1))
    b = int(m.group(2) or a)
    if a < 1 or b < a:
        raise SystemExit(f"--pages 范围不合法：{spec}")
    return a, min(b, total)


def connect(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    con.commit()
    return con


def course_id(con: sqlite3.Connection, name: str) -> int:
    row = con.execute("select id from courses where name=?", (name,)).fetchone()
    if row:
        return row[0]
    cur = con.execute("insert into courses(name) values(?)", (name,))
    con.commit()
    return cur.lastrowid


def ingest(con: sqlite3.Connection, path: Path, rel: str, course: str, pages_spec: str) -> int:
    try:
        pages = extract_pages(str(path))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {path.name}: 抽不出文本（{exc}）")
        return 0
    start, end = parse_pages(pages_spec, len(pages))
    sample = "".join(pages[start - 1:end])[:2000]
    if len(clean(sample)) < 20:
        print(f"  ! {path.name}: 看起来没有文字层（需要先 OCR，见 05-materials.md）")
        return 0
    cid = course_id(con, course)
    con.execute("delete from items where doc_id in (select id from docs where rel_path=?)", (rel,))
    doc_row = con.execute("select id from docs where rel_path=?", (rel,)).fetchone()
    if doc_row:
        doc_id = doc_row[0]
        con.execute(
            "update docs set course_id=?, pages=?, source='pdf' where id=?",
            (cid, end - start + 1, doc_id),
        )
    else:
        cur = con.execute(
            "insert into docs(course_id, rel_path, pages, source) values(?,?,?, 'pdf')",
            (cid, rel, end - start + 1),
        )
        doc_id = cur.lastrowid
    n = 0
    for pno in range(start, end + 1):
        body = clean(pages[pno - 1])
        title = guess_title(body)
        section = guess_section(body)
        con.execute(
            "insert into items(doc_id, page, title, section, text) values(?,?,?,?,?)",
            (doc_id, pno, title, section, body),
        )
        n += 1
    con.commit()
    print(f"  + {rel}  p{start}-{end}  写入 {n} 条")
    return n


def rebuild(con: sqlite3.Connection) -> None:
    con.execute("insert into items_fts(items_fts) values('rebuild')")
    con.commit()


def show_list(con: sqlite3.Connection) -> None:
    rows = con.execute(
        """select c.name, d.rel_path, d.pages, count(i.id)
             from docs d join courses c on c.id=d.course_id
             left join items i on i.doc_id=d.id
            group by d.id order by c.name, d.id"""
    ).fetchall()
    if not rows:
        print("库里还没有文档。")
        return
    w = max(len(r[0]) for r in rows) + 2
    for name, rel, pages, n in rows:
        print(f"{name:<{w}} {rel:<50} {pages:>4} 页  {n:>4} 条")


def do_check(con: sqlite3.Connection, words: list[str], course: str) -> int:
    """验收：直接用 LIKE 找中文子串——FTS5 的 unicode61 不切中文词，
    两三个字的词在上面查不到，这里用 LIKE 保证「说得出的词都找得到」。"""
    bad = 0
    for word in words:
        sql = """select c.name, d.rel_path, i.page, i.title
                   from items i join docs d on d.id=i.doc_id
                   join courses c on c.id=d.course_id
                  where (i.text like ? or i.title like ?)"""
        like = "%" + word + "%"
        args: list[str] = [like, like]
        if course:
            sql += " and c.name=?"
            args.append(course)
        sql += " order by i.page limit 5"
        rows = con.execute(sql, args).fetchall()
        mark = "OK" if rows else "MISS"
        print(f"[{mark}] {word}: {len(rows)} 条")
        if not rows:
            bad += 1
        for name, rel, page, title in rows[:3]:
            print(f"       {name} · {Path(rel).name} p{page}  {(title or '')[:40]}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="建最小知识库（SQLite + FTS5）")
    ap.add_argument("--db", required=True)
    ap.add_argument("--course", default="")
    ap.add_argument("--pdf", action="append", default=[])
    ap.add_argument("--dir", default="")
    ap.add_argument("--pattern", default="*.pdf")
    ap.add_argument("--pages", default="", help="1-120 或 5")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", nargs="+", default=[], help="验收：检索这些词")
    ap.add_argument("--no-rebuild", action="store_true")
    args = ap.parse_args()

    if args.list:
        if not Path(args.db).exists():
            print(f"库不存在：{args.db}（先入库再列：--pdf 或 --dir）", file=sys.stderr)
            return 2
        show_list(connect(args.db))
        return 0

    if args.check:
        if not Path(args.db).exists():
            print(f"库不存在：{args.db}（先入库再验收）", file=sys.stderr)
            return 2
        return 1 if do_check(connect(args.db), args.check, args.course) else 0

    con = connect(args.db)

    if not args.course:
        print("入库需要 --course", file=sys.stderr)
        return 2

    files: list[Path] = [Path(p) for p in args.pdf]
    base: Path | None = None
    if args.dir:
        base = Path(args.dir)
        if not base.is_dir():
            print(f"目录不存在：{base}", file=sys.stderr)
            return 2
        files += [p for p in sorted(base.iterdir()) if p.is_file() and fnmatch.fnmatch(p.name, args.pattern)]
    if not files:
        print("没有要入库的文件（用 --pdf 或 --dir）", file=sys.stderr)
        return 2

    total = 0
    for f in files:
        if not f.exists():
            print(f"  ! 不存在：{f}")
            continue
        print(f"处理 {f.name}")
        rel = f.name
        if base is not None:
            try:
                rel = f.relative_to(base).as_posix()
            except ValueError:
                rel = f.name
        total += ingest(con, f, rel, args.course, args.pages)

    if total and not args.no_rebuild:
        rebuild(con)
        print(f"已重建 FTS 索引（共 {total} 条新增）。")
    print("验收：python build_kb.py --db <库> --course <课> --check 词1 词2 词3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
