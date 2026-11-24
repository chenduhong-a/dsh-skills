#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""首次运行：问清路径，写 config.json，建进度目录。

用法：
  python init.py                     # 交互问三个问题（目录 / 知识库 / 编译器）
  python init.py --study-dir D:\\study --yes
  python init.py --study-dir D:\\study --progress-dir D:\\study\\学习进度 --kb-db D:\\study\\kb.sqlite --yes
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG = SKILL_DIR / "config.json"


def ask(prompt: str, default: str = "") -> str:
    tip = f"[{default}] " if default else ""
    try:
        raw = input(f"{prompt}{tip}").strip()
    except EOFError:
        raw = ""
    return raw or default


def find_xelatex() -> str:
    """找 XeLaTeX 所在目录：先 PATH，再几个常见安装位置。"""
    found = shutil.which("xelatex")
    if found:
        return str(Path(found).parent)
    exe = "xelatex.exe" if os.name == "nt" else "xelatex"
    bases = [Path.home() / "texlive", Path("C:/texlive"), Path("/usr/local/texlive")]
    for base in bases:
        if not base.is_dir():
            continue
        for year in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
            for sub in ("bin/windows", "bin/x86_64-linux", "bin/universal-darwin"):
                cand = year / sub / exe
                if cand.exists():
                    return str(cand.parent)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="study-flow 初始化")
    ap.add_argument("--study-dir", help="课程资料根目录")
    ap.add_argument("--progress-dir", help="学习进度根目录（默认 <study-dir>\\学习进度）")
    ap.add_argument("--kb-db", default="", help="可选：知识库 sqlite 路径")
    ap.add_argument("--kb-cli", default="", help="可选：知识库命令行入口")
    ap.add_argument("--texlive-bin", default="", help="可选：XeLaTeX 所在目录（不填就自动找）")
    ap.add_argument("--force", action="store_true", help="覆盖已有 config.json")
    ap.add_argument("--yes", action="store_true", help="不问，直接用参数与默认值")
    args = ap.parse_args()

    if CONFIG.exists() and not args.force:
        print(f"config.json 已存在，本次没有改动任何东西：{CONFIG}")
        print("要重写请加 --force；只想改个别键，直接编辑它（键说明见 references/07-environment.md）。")
        return 1

    study = args.study_dir
    if not study and not args.yes:
        print("三个问题，回车用默认值。\n")
        study = ask("课程资料放哪个目录（教材 / 课件 / 成品 PDF）？", str(Path.home() / "study"))
    study = study or os.environ.get("STUDY_DIR", "")

    progress = args.progress_dir
    if not progress and not args.yes and study:
        progress = ask("学习进度放哪？", str(Path(study) / "学习进度"))
    progress = progress or (str(Path(study) / "学习进度") if study else "")

    kb_db = args.kb_db
    if not kb_db and not args.yes:
        kb_db = ask("有自建知识库吗？有就填 sqlite 路径，没有直接回车：", "")

    if not study:
        print("必须给 --study-dir（或交互填写）。", file=sys.stderr)
        return 2

    texlive = args.texlive_bin or find_xelatex()
    if args.texlive_bin:
        cand = Path(args.texlive_bin) / ("xelatex.exe" if sys.platform.startswith("win") else "xelatex")
        if not cand.exists():
            print(f"--texlive-bin 指向的目录里没有 xelatex：{cand}", file=sys.stderr)
            return 2

    kb_cli = args.kb_cli
    if kb_db and not kb_cli:
        guess = Path(kb_db).parent / "kb.py"
        kb_cli = str(guess) if guess.exists() else ""

    cfg = {
        "study_dir": str(Path(study).resolve()),
        "progress_dir": str(Path(progress).resolve()),
        "kb": {"enabled": bool(kb_db), "db": kb_db, "cli": kb_cli},
        "pdf_engine": "auto",
        "texlive_bin": texlive,
        "scripts_dir": "scripts",
    }
    for key in ("study_dir", "progress_dir"):
        try:
            Path(cfg[key]).mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # noqa: BLE001
            print(f"建不了目录 {cfg[key]}：{exc}", file=sys.stderr)
            print("config.json 没有写入——换一个可写的路径再跑，别留下半配置。", file=sys.stderr)
            return 2

    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n已写入 {CONFIG}")
    for k, v in cfg.items():
        print(f"  {k:<14} {v}")
    if not texlive:
        print("\n!! 没找到 XeLaTeX——建课没问题，但试卷 / 总结 / 清单都出不了 PDF，")
        print("   而公式只有 LaTeX 排得出来，没有降级替代（md、HTML 顶替的产物不算产物）。")
        print("   装 TeX Live 或 MiKTeX 后重跑：& $PY scripts\\init.py --texlive-bin <xelatex 所在目录>")
        print("   或把该目录填进 config.json 的 texlive_bin。")
    print("\n下一步：& $PY scripts\\check_env.py 看环境；开课就说「从头学一门课」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
