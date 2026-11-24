#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""环境自检：打印「有什么、缺什么、缺了影响哪一步」。

用法：python check_env.py
退出码：0 = 必备项齐；1 = 缺必备项（python / config / 可写目录）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG = SKILL_DIR / "config.json"
OK, NO, WARN = "OK", "--", "!!"

rows: list[tuple[str, str, str]] = []
required_fail: list[str] = []


def add(name: str, mark: str, detail: str) -> None:
    rows.append((name, mark, detail))


def check_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        add("python", OK, f"{v.major}.{v.minor}.{v.micro}  {sys.executable}")
    else:
        add("python", NO, f"{v.major}.{v.minor}（需要 3.10+）")
        required_fail.append("python")


def load_cfg():
    if not CONFIG.exists():
        add("config.json", NO, f"不存在：{CONFIG}（先跑 init.py）")
        required_fail.append("config.json")
        return None
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        add("config.json", NO, f"解析失败：{exc}")
        required_fail.append("config.json")
        return None
    if not isinstance(cfg, dict):
        add("config.json", NO, f"顶层应是一个对象（{{...}}），现在读到 {type(cfg).__name__}")
        required_fail.append("config.json")
        return None
    add("config.json", OK, str(CONFIG))
    return cfg


def check_path(cfg: dict) -> None:
    for key in ("study_dir", "progress_dir"):
        p = cfg.get(key, "")
        if not p:
            add(key, NO, "未配置")
            required_fail.append(key)
            continue
        if not isinstance(p, str):
            add(key, NO, f"类型不对（应是字符串路径），现在是 {type(p).__name__}：{p!r}")
            required_fail.append(key)
            continue
        path = Path(p)
        if not path.exists():
            add(key, WARN, f"不存在，init.py 会建；也可手动 mkdir：{path}")
            continue
        try:
            with tempfile.NamedTemporaryFile(dir=str(path), delete=True):
                pass
            add(key, OK, str(path))
        except Exception as exc:  # noqa: BLE001
            add(key, NO, f"不可写：{path}（{exc}）")
            required_fail.append(key)


def check_xelatex(cfg: dict) -> None:
    bin_dir = cfg.get("texlive_bin", "")
    exe = ""
    if bin_dir and not isinstance(bin_dir, str):
        add("xelatex", NO, f"config 里的 texlive_bin 应是字符串路径，现在是 {type(bin_dir).__name__}")
        required_fail.append("xelatex")
        return
    if bin_dir:
        cand = Path(bin_dir) / ("xelatex.exe" if os.name == "nt" else "xelatex")
        if cand.exists():
            exe = str(cand)
    if not exe:
        exe = shutil.which("xelatex") or ""
    if not exe:
        add("xelatex", NO, "未找到（出不了 PDF，先装 TeX；没有降级替代）")
        required_fail.append("xelatex")
        return
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20).stdout
        ver = (out.splitlines() or ["?"])[0][:48]
        add("xelatex", OK, f"{ver}  {exe}")
    except Exception as exc:  # noqa: BLE001
        add("xelatex", WARN, f"找到但跑不起来：{exe}（{exc}）")


PIP_HINT = "& $PY -m pip install pypdfium2 pypdf -i https://pypi.tuna.tsinghua.edu.cn/simple"


def check_pdf_libs() -> None:
    """PDF 库。注意 DSH 运行时升级会重置 site-packages——装过的也可能整批消失。"""
    for mod in ("pypdfium2", "pypdf", "fitz"):
        try:
            __import__(mod)
            add(f"py: {mod}", OK, "可导入")
        except Exception:  # noqa: BLE001
            if mod == "fitz":
                add(f"py: {mod}", NO, "未装（可选，不影响主链）")
            else:
                add(f"py: {mod}", NO, f"未装或已被运行时升级重置——重装：{PIP_HINT}")


def check_kb(cfg: dict) -> None:
    kb = cfg.get("kb") or {}
    if not isinstance(kb, dict):
        add("知识库", NO, f"config 里的 kb 应是对象（{{enabled, db, cli}}），现在是 {type(kb).__name__}")
        return
    if not kb.get("enabled"):
        add("知识库", NO, "未启用（查原文降级为 doc_text / doc_render）")
        return
    db = kb.get("db", "")
    if db and not isinstance(db, str):
        add("知识库", NO, f"config 里的 kb.db 应是字符串路径，现在是 {type(db).__name__}")
        return
    if not db or not Path(db).exists():
        add("知识库", NO, f"库文件不存在：{db or '（空）'}")
        return
    try:
        con = sqlite3.connect(db)
        tables = {r[0] for r in con.execute("select name from sqlite_master where type in ('table','view')")}
        n = con.execute("select count(*) from items").fetchone()[0]
        con.close()
        need = {"courses", "docs", "items"}
        if need <= tables:
            add("知识库", OK, f"{db}（items {n} 条）")
        else:
            add("知识库", WARN, f"{db}（缺表：{', '.join(sorted(need - tables))}）")
    except Exception as exc:  # noqa: BLE001
        add("知识库", NO, f"打不开：{db}（{exc}）")
    # cli 是查原文的入口，配错了不报会让「查不到原文」看起来像库的问题
    cli = kb.get("cli", "")
    if not isinstance(cli, str):
        add("知识库 CLI", WARN, f"config 里的 kb.cli 应是字符串路径，现在是 {type(cli).__name__}")
    elif not cli:
        add("知识库 CLI", WARN, "没配 kb.cli（查原文走 04-kb.md 第七节的 SQL）")
    elif not Path(cli).exists():
        add("知识库 CLI", WARN, f"指向不存在的文件：{cli}（查原文前先修它）")
    else:
        add("知识库 CLI", OK, cli)


def check_remote_tools() -> None:
    add("pdf 解析 / OCR", WARN, "脚本测不到（会话里试 doc_info 一次）")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="探测环境：有什么、缺什么、缺了影响哪一步。")
    ap.add_argument("--json", action="store_true", help="输出 JSON（name / mark / detail），便于自动化")
    ap.add_argument("--quiet", action="store_true", help="只打印缺的项（mark 不是 OK 的）")
    args = ap.parse_args(argv)

    check_python()
    cfg = load_cfg()
    if cfg is not None:
        check_path(cfg)
        check_xelatex(cfg)
        check_kb(cfg)
    check_pdf_libs()
    check_remote_tools()

    if args.json:
        print(json.dumps([{"name": n, "mark": m, "detail": d} for n, m, d in rows], ensure_ascii=False))
        return 1 if required_fail else 0

    shown = [r for r in rows if not args.quiet or r[1] != OK]
    if shown:
        w = max(len(r[0]) for r in shown) + 2
        print("=" * 72)
        for name, mark, detail in shown:
            print(f"{name:<{w}} {mark:<3} {detail}")
        print("=" * 72)
    if required_fail:
        print("缺必备项：" + "、".join(required_fail))
        print("按 references/07-environment.md 第二节处理。")
        return 1
    print("必备项齐。缺的选装项按 references/07-environment.md 第三节降级——"
          "但 XeLaTeX 缺了没有降级路径：出不了 PDF 就先装 TeX。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
