r"""Compile self-contained TeX into PDF using an ASCII build name.

Some Windows TeX installations cannot create log files whose names contain
Chinese characters. Build as study.tex in a temporary directory while keeping
the delivered TeX and PDF names descriptive.

A directory can be given as source: every *.tex in it is compiled to a PDF of
the same stem under the output directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


def find_compiler(name: str) -> str | None:
    """PATH 优先，其次读技能目录下 config.json 的 texlive_bin。"""
    exe = shutil.which(name)
    if exe:
        return exe
    config = Path(__file__).resolve().parent.parent / "config.json"
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    bin_dir = (data or {}).get("texlive_bin") or ""
    if not bin_dir:
        return None
    cand = Path(bin_dir) / (name + (".exe" if os.name == "nt" else ""))
    return str(cand) if cand.exists() else None


def keep_build(build: Path, output: Path) -> Path:
    """编译失败时把 TeX 源与完整日志复制到输出目录旁的 <名字>.build\。"""
    target = output.parent / (output.stem + ".build")
    target.mkdir(parents=True, exist_ok=True)
    for item in ("study.tex", "study.log", "study.aux"):
        path = build / item
        if path.is_file():
            shutil.copyfile(path, target / item)
    return target


def compile_one(
    compiler: str, name: str, source: Path, output: Path, keep_aux: bool = False
) -> None:
    with tempfile.TemporaryDirectory(prefix="study-flow-") as directory:
        build = Path(directory)
        tex = build / "study.tex"
        shutil.copyfile(source, tex)
        for extra in source.parent.iterdir():
            if extra.name == source.name:
                continue
            if extra.is_file() and extra.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".bib", ".sty", ".cls"}:
                shutil.copyfile(extra, build / extra.name)
            elif extra.is_dir() and extra.name.lower() in {"figures", "fig", "images", "img", "assets", "图", "插图"}:
                try:
                    shutil.copytree(extra, build / extra.name, dirs_exist_ok=True)
                except Exception:  # noqa: BLE001
                    pass
        # TeX 里引用的图（含任意相对子目录）按原相对路径带进临时目录，
        # 固定目录名白名单兜不住 sub/fig.png 这类写法。
        import re as _re
        try:
            body = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
        for m in _re.finditer(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^}]+)\}", body):
            rel = m.group(1).strip()
            if not rel or rel.startswith("/") or ".." in rel or _re.match(r"[A-Za-z]:[\\/]", rel):
                continue  # 绝对路径的图本来就在原地，拷进来反而会 SameFileError
            cand = source.parent / rel
            if not cand.is_file():
                continue
            target = build / rel
            if target.resolve() == tex.resolve():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cand, target)

        command = [compiler, "-interaction=nonstopmode", "-halt-on-error", tex.name]
        for pass_number in (1, 2):
            result = subprocess.run(
                command, cwd=build, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", check=False,
            )
            if result.returncode:
                hint = ""
                if keep_aux:
                    saved = keep_build(build, output)
                    hint = f"\n完整日志已留：{saved}"
                raise SystemExit(
                    f"{name} pass {pass_number} failed:\n"
                    + "\n".join(result.stdout.splitlines()[-30:])
                    + hint
                )
        pdf = build / "study.pdf"
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise SystemExit(f"{name} 编译完成但没有产出 PDF")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, output)
        print(f"compiled: {output}")


def main() -> None:
    _configure_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="自包含的 .tex 文件，或装着 .tex 的目录")
    parser.add_argument("output", type=Path, help="输出的 .pdf 文件（源是目录时当成输出目录）")
    parser.add_argument("--compiler", choices=["xelatex", "lualatex"], default="xelatex")
    parser.add_argument(
        "--keep-aux",
        action="store_true",
        help="编译失败时把 .tex 与完整 .log 留在输出旁的 <名字>.build\\ 里；成功不留任何中间件",
    )
    args = parser.parse_args()

    compiler = find_compiler(args.compiler)
    if compiler is None:
        raise SystemExit(
            f"{args.compiler} 不可用：PATH 与 config.json 的 texlive_bin 都没找到。"
            "先跑 init.py，或 check_env.py 看缺什么。没有 XeLaTeX 就出不了 PDF，"
            "也没有降级替代——先装 TeX Live 或 MiKTeX。"
        )

    if args.source.is_dir():
        sources = sorted(p for p in args.source.glob("*.tex"))
        if not sources:
            raise SystemExit(f"{args.source} 里没有 .tex")
        args.output.mkdir(parents=True, exist_ok=True)
        for tex in sources:
            compile_one(
                compiler, tex.name, tex, args.output / (tex.stem + ".pdf"), args.keep_aux
            )
        print(f"done: {len(sources)} file(s) -> {args.output}")
        return

    if args.source.suffix.lower() != ".tex" or args.output.suffix.lower() != ".pdf":
        raise SystemExit("单文件模式要求 .tex 源与 .pdf 输出")
    compile_one(compiler, args.source.name, args.source, args.output, args.keep_aux)


if __name__ == "__main__":
    main()
