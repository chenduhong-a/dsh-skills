#!/usr/bin/env python3
r"""doc_check.py —— 文档里写的命令，与脚本真有的参数对账。

查四件事：
  1. 文档提到的 xxx.py 在 scripts/ 里都存在；
  2. xxx.py 后面跟的 --flag 在它的 argparse 里真的存在；
  3. 文档引用的 assets\ 、references\ 文件都存在；
  4. map-config.example.json 的顶层键覆盖所有需要地图的 --kind。

只读、不执行脚本、不写任何文件。退出码 = 问题条数 > 0 时为 1。

用法：
    & $PY scripts\doc_check.py
    & $PY scripts\doc_check.py --verbose   # 连通过的引用也打印
    & $PY scripts\doc_check.py --json

（$PY 见 SKILL.md 第六节；本机裸 python 是应用商店占位程序）
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
DOCS = ["SKILL.md", "README.md", *[f"references/{p.name}" for p in sorted((SKILL_DIR / "references").glob("*.md"))]]

# 这些不是本技能自带的脚本：kb.py 是可选的本地知识库工具，config.py 是示例文件名
EXTERNAL = {"kb.py", "config.py"}

PY_REF = re.compile(r"([A-Za-z0-9_]+\.py)")
FLAG = re.compile(r"--[a-z][A-Za-z0-9-]*")
ASSET_REF = re.compile(r"(assets|references)[\\/]([A-Za-z0-9_.\-]+(?:[\\/][A-Za-z0-9_.\-]+)*\.\w+)")
# 裸 python 调用：python scripts/... 或 python -m ...；前面是 $ 或反斜杠的不算
BARE_PY = re.compile(r"(?<![\w$\\])python\s+(scripts[\\/]|-[mM]\s)")
SUBNAME = re.compile(r"^[a-z][a-z0-9-]*$")


def script_model(path: Path) -> tuple[set[str], set[str]]:
    """返回（这个脚本接受的全部 --flag 与位置参数名, 子命令名）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    flags: set[str] = set()
    subs: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not isinstance(fn, ast.Attribute) or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            continue
        value = node.args[0].value
        if fn.attr == "add_argument":
            if value.startswith("--"):
                flags.add(value)
            elif not value.startswith("-"):
                flags.add(value)  # 位置参数：按裸名记
        elif fn.attr == "add_parser":
            subs.add(value)
    return flags, subs


def script_strings(path: Path) -> list[str]:
    """脚本里所有字符串常量——docstring 与 print 提示都算。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


def kind_choices(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--kind"):
            continue
        for kw in node.keywords:
            if kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple)):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        out.add(elt.value)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="文档与脚本参数对账")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    models = {p.name: script_model(p) for p in sorted(SCRIPTS.glob("*.py"))}
    problems: list[str] = []
    passed = 0
    checked_flags = 0

    # 1+2+3：逐篇文档扫
    for rel in DOCS:
        path = SKILL_DIR / rel
        if not path.exists():
            problems.append(f"{rel} 不存在（文档目录被改动过？）")
            continue
        joined, buf, start = [], "", 0
        for i, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not buf:
                start = i
            if raw_line.rstrip().endswith("\\"):
                buf += raw_line.rstrip()[:-1] + " "
            else:
                joined.append((start, buf + raw_line))
                buf = ""
        if buf:
            joined.append((start, buf))
        for lineno, line in joined:  # 反斜杠续行已合并成一个逻辑行
            # 脚本存在性 + 参数归属
            refs = list(PY_REF.finditer(line))
            for idx, m in enumerate(refs):
                name = m.group(1)
                start = m.end()
                end = refs[idx + 1].start() if idx + 1 < len(refs) else len(line)
                if name not in models:
                    if name not in EXTERNAL:
                        problems.append(f"{rel}:{lineno}  提到 {name}，scripts/ 里没有这个脚本")
                    continue
                flags, subs = models[name]
                tail = line[start:end]
                # 子命令名校验：有子命令的脚本，.py 后面第一个词必须是其中之一
                if subs:
                    pieces = tail.strip().split()
                    first = pieces[0].lstrip("&").strip() if pieces else ""
                    if SUBNAME.match(first) and first not in subs:
                        problems.append(
                            f"{rel}:{lineno}  {name} 没有子命令 {first}"
                            f"（它有：{' '.join(sorted(subs))}）"
                        )
                for f in FLAG.findall(line[start:end]):
                    checked_flags += 1
                    if f in flags:
                        passed += 1
                        if args.verbose:
                            print(f"  ok  {rel}:{lineno}  {name} {f}")
                    else:
                        problems.append(
                            f"{rel}:{lineno}  {name} {f} 不在它的参数里（它有：{' '.join(sorted(flags))[:120]}）"
                        )
            # 资源存在性
            for kind, fname in ASSET_REF.findall(line):
                if (SKILL_DIR / kind / fname).exists():
                    passed += 1
                else:
                    problems.append(f"{rel}:{lineno}  引用 {kind}\\{fname}，文件不存在")

    # 4：map-config 覆盖需要地图的 kind
    kinds = kind_choices(SCRIPTS / "render_study_pdf.py")
    mapfile = SKILL_DIR / "assets" / "map-config.example.json"
    if kinds and mapfile.exists():
        need = {k for k in kinds if k != "errors"}
        try:
            keys = set(json.loads(mapfile.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"assets\\map-config.example.json 解析失败：{exc}")
            keys = set()
        miss = need - keys
        if miss:
            problems.append(f"map-config.example.json 缺这些 kind 的配置：{'、'.join(sorted(miss))}")
        else:
            passed += len(need)

    # 5：裸 python 扫描——文档 + 脚本文案（CHANGELOG 是历史证据，跳过）
    for rel in DOCS:
        if Path(rel).name.upper().startswith("CHANGELOG"):
            continue
        path = SKILL_DIR / rel
        if not path.exists():
            continue
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BARE_PY.search(raw) and "$PY" not in raw:
                problems.append(
                    f"{rel}:{lineno}  直接调 python，本机会 exit 9009；"
                    "请写 & $PY，定义见 SKILL.md 第六节"
                )
    for sp in sorted(SCRIPTS.glob("*.py")):
        try:
            strings = script_strings(sp)
        except SyntaxError:
            continue
        for s in strings:
            if BARE_PY.search(s):
                problems.append(
                    f"scripts\\{sp.name}  文案里直接调 python：{s.strip()[:70]}"
                )
                break

    if args.json:
        print(json.dumps({"problems": problems, "passed": passed, "flags": checked_flags},
                         ensure_ascii=False, indent=2))
    else:
        print(f"文档对账：{len(DOCS)} 篇文档 · {len(models)} 个脚本 · {checked_flags} 处参数引用")
        print("-" * 70)
        for p in problems:
            print(f"  ERR  {p}")
        print("-" * 70)
        if problems:
            print(f"{len(problems)} 处对不上。改文档或改脚本，别让它俩各说各话。")
        else:
            print(f"全部对上（{passed} 处引用命中）。")
            print("（只验参数名存在、不验必填；写成可照抄的一行时，--course 这类必填参数自己要带齐）")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
