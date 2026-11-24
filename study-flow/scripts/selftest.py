#!/usr/bin/env python3
r"""selftest.py —— 用 assets/demo 的素材把整条链跑一遍，出一张通过表。

它不碰真实数据：所有写入都落在临时目录，并通过 QBANK_PROGRESS 改道。
xelatex 不在就标 SKIP（渲染步骤照样验，只跳编译）。

用法：
    & $PY scripts\selftest.py            # 跑完删临时目录
    & $PY scripts\selftest.py --keep     # 留下临时目录，方便看产物
    & $PY scripts\selftest.py --verbose  # 每步都打完整输出
    & $PY scripts\selftest.py --json     # 机器可读结果

（$PY 见 SKILL.md 第六节；本机裸 python 是应用商店占位程序）
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
PY = sys.executable
COURSE = "自测课"

RESULTS: list[dict] = []


def base_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cfg = SKILL_DIR / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        bin_dir = data.get("texlive_bin")
        if bin_dir and Path(bin_dir).is_dir():
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    return env


ENV = base_env()
HAVE_TEX = shutil.which("xelatex", path=ENV.get("PATH")) is not None


def py(script: str, *args, timeout: int = 240) -> tuple[subprocess.CompletedProcess, float]:
    t0 = time.time()
    cmd = [PY, str(SCRIPTS / script), *[str(a) for a in args]]
    cp = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
        timeout=timeout,
    )
    return cp, time.time() - t0


def record(name: str, ok: bool, note: str = "", secs: float = 0.0, status: str = "") -> None:
    RESULTS.append({
        "step": name,
        "status": status or ("OK" if ok else "FAIL"),
        "secs": round(secs, 2),
        "note": note,
    })
    if not ok and not status:
        print(f"  ! {name} 失败：{note}", file=sys.stderr)


def check(name: str, cp: subprocess.CompletedProcess, secs: float, ok: bool, note: str = "") -> bool:
    if not ok:
        tail = (cp.stderr or cp.stdout or "").strip().splitlines()
        note = note or (tail[-1] if tail else f"rc={cp.returncode}")
    record(name, ok, note, secs)
    return ok


def skip(name: str, why: str) -> None:
    record(name, True, why, 0.0, status="SKIP")


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


KNOWLEDGE_MD = """# 数列极限 · 知识卡

**K1.** ε-N 定义

任意给 ε>0，都存在 N，使 n>N 时 |a_n-a|<ε。

**K2.** 四则运算

先让出界的那一项变小，再估另一项。

**K3.** 夹逼定理

$b_n \\le a_n \\le c_n$ 且两端同归 $L$。
"""

PLAN_MD = """# 数列极限 · 备考计划

## 阶段一（第 1–2 周）

定义、记号、四则运算。每天 30 分钟，做完 10 道基础题。

## 阶段二（第 3–4 周）

夹逼定理与单调有界。每周一套限时卷，订正当天的错题。

## 阶段三（第 5–6 周）

跨章综合。只做错题重做与薄弱的两个题型。
"""

DAY_MD = """# 第 1 讲 · 今日课

**今天的目标**：把 ε-N 定义说清楚，会做两道估计题。**预计用时**：45 分钟。

## 一、先猜

不用查书——「lim 1/n = 0」这句话里，哪个量词写在前面？

## 二、讲一段

任意给 ε>0，先取 N，再让 n>N。顺序反了就说不通。

## 三、例题

证明 lim 1/n = 0。取 $N=\\lceil 1/\\varepsilon \\rceil$，当 $n>N$ 时 $0<1/n<\\varepsilon$。

## 四、练习

用同一套写法证明 lim 2/n = 0。

## 五、答案

取 $N=\\lceil 2/\\varepsilon \\rceil$ 即可，其余同上。
"""

QUIZ_MD = """# 第 1 讲 随堂卷

## 一、选择题

**1.** 数列收敛定义里，量词顺序是？

**2.** 若 $a_n\\to a$，则 $|a_n|\\to|a|$ 对任何数列都成立吗？

## 二、计算题

**3.** 求 $\\lim \\sqrt[n]{n}$，说明用了什么定理。

## 答案

1. 任意 ε 在前，存在 N 在后。

2. 成立，用三角不等式 $||a_n|-|a|| \\le |a_n-a|$。

3. 夹逼：下界 1，上界 $1+\\sqrt{2/(n-1)}$。
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="study-flow 全链自测")
    ap.add_argument("--keep", action="store_true", help="保留临时目录")
    ap.add_argument("--verbose", action="store_true", help="打印每步完整输出")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="studyflow-selftest-"))
    if not args.keep:  # 中途抛异常也清掉，别在 %TEMP% 里留 studyflow-selftest-*
        atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    progress = tmp / "学习进度"
    progress.mkdir(parents=True, exist_ok=True)
    ENV["QBANK_PROGRESS"] = str(progress)

    if not args.json:
        print(f"临时目录 {tmp}")
        print(f"解释器   {PY}")
        print(f"xelatex  {'有' if HAVE_TEX else '没有（编译步骤会跳过）'}")
        print()

    # ---- 1 建课
    cp, s = py("qbank.py", "init", "--course", COURSE)
    ok = cp.returncode == 0 and (progress / COURSE / "题库.jsonl").exists()
    check("init 建课", cp, s, ok)
    if args.verbose:
        print(cp.stdout, cp.stderr)

    # ---- 2 加题
    bank = [
        ("用定义证明 lim 1/n = 0。", "取 N=⌈1/ε⌉。", "第1讲", "ε-N定义"),
        ("若 a_n→a，证明 |a_n|→|a|。", "三角不等式逆用。", "第1讲", "绝对值极限"),
        ("求 lim n^(1/n)，说明用了什么定理。", "夹逼，上界 1+√(2/(n−1))。", "第3讲", "夹逼定理"),
    ]
    all_ok, total = True, 0.0
    for prompt, ans, chap, topic in bank:
        cp, s = py(
            "qbank.py", "add", "--course", COURSE,
            "--prompt", prompt, "--answer", ans,
            "--chapter", chap, "--topic", topic,
            "--source", "assets/demo/demo-material.md",
        )
        total += s
        all_ok = all_ok and cp.returncode == 0
    cp_last = cp
    check("add 加三道题", cp_last, total, all_ok)

    # ---- 3 列题
    cp, s = py("qbank.py", "list", "--course", COURSE)
    check("list 列题", cp, s, cp.returncode == 0 and "共 3 题" in cp.stdout, "应显示共 3 题")

    # ---- 4 抽题
    cp, s = py("qbank.py", "pick", "--course", COURSE, "--n", "2")
    check("pick 抽题", cp, s, cp.returncode == 0 and cp.stdout.strip() != "")

    # ---- 4b 按章抽题（题带 --chapter 时才抽得到）
    cp, s = py("qbank.py", "pick", "--course", COURSE, "--n", "1", "--chapter", "第1讲")
    check("pick --chapter 按章抽题", cp, s, cp.returncode == 0 and cp.stdout.strip() != "",
          "题带 --chapter 时应该抽得到；抽不到说明 add 时漏了章节")

    # ---- 5/6 作答
    cp, s = py("qbank.py", "grade", "--course", COURSE, "--qid", "q-0001",
               "--wrong", "--step", "2", "--confidence", "unsure")
    check("grade 记错（断在第 2 步）", cp, s, cp.returncode == 0 and "下次" in cp.stdout)

    cp, s = py("qbank.py", "grade", "--course", COURSE, "--qid", "q-0002", "--grade", "good")
    check("grade 记对", cp, s, cp.returncode == 0)

    # ---- 7 stats
    cp, s = py("qbank.py", "stats", "--course", COURSE)
    ok = cp.returncode == 0 and "已作答 2 次" in cp.stdout
    check("stats 统计", cp, s, ok, "应显示已作答 2 次")

    # ---- 8 due
    cp, s = py("qbank.py", "due", "--course", COURSE)
    check("due 到期列表", cp, s, cp.returncode == 0)

    # ---- 8b 考试日（--date 走 argparse 的 iso_date，防「已转成 date 又 fromisoformat」回归）
    cp, s = py("qbank.py", "exam", "--course", COURSE, "--date", "2026-12-26")
    check("exam 设考试日", cp, s, cp.returncode == 0 and "2026-12-26" in cp.stdout,
          "--date 应被接受并回显")
    cp, s = py("qbank.py", "exam", "--course", COURSE)
    check("exam 读回考试日", cp, s, cp.returncode == 0 and "2026-12-26" in cp.stdout)
    cp, s = py("qbank.py", "pick", "--course", COURSE, "--n", "1", "--date", "2026-12-01")
    check("pick --date", cp, s, cp.returncode == 0)

    # ---- 9 错题本 md
    err_md = tmp / "错题本.md"
    cp, s = py("qbank.py", "errors", "--course", COURSE, "--out", err_md)
    text = err_md.read_text(encoding="utf-8") if err_md.exists() else ""
    ok = cp.returncode == 0 and "## 错题 1" in text and "### 再做一题" in text
    check("errors 生错题本", cp, s, ok, "应含「## 错题 1」与「### 再做一题」")

    # ---- 9b 错题本要带题号（复刷时要用它去 grade）
    qid_ok = cp.returncode == 0 and "题号：`q-" in text
    check("errors 带题号", cp, s, qid_ok, "「题号：`q-xxxx`」缺了就没法用 grade 复刷这道题")

    # ---- 10/11 错题本 tex + pdf
    err_tex = tmp / "错题本.tex"
    cp, s = py("render_study_pdf.py", err_md, err_tex, "--kind", "errors", "--layout", "loose")
    tex = err_tex.read_text(encoding="utf-8") if err_tex.exists() else ""
    check("render errors", cp, s, cp.returncode == 0 and "PracticeQuestionColon" in tex,
          "errors 应走带冒号那套题纸宏")

    if HAVE_TEX and err_tex.exists():
        err_pdf = tmp / "错题本.pdf"
        cp, s = py("compile_study_pdf.py", err_tex, err_pdf)
        ok = cp.returncode == 0 and err_pdf.exists() and err_pdf.stat().st_size > 5000
        check("compile 错题本 PDF", cp, s, ok, "编译后 PDF 应存在且大于 5 KB")
    else:
        skip("compile 错题本 PDF", "没有 xelatex")

    # ---- 12/13 知识卡 tex + pdf
    kn_md = write(tmp / "知识卡.md", KNOWLEDGE_MD)
    kn_tex = tmp / "知识卡.tex"
    mapcfg = SKILL_DIR / "assets" / "map-config.example.json"
    cp, s = py("render_study_pdf.py", kn_md, kn_tex, "--kind", "knowledge",
               "--layout", "compact", "--map-config", mapcfg)
    tex = kn_tex.read_text(encoding="utf-8") if kn_tex.exists() else ""
    check("render knowledge", cp, s, cp.returncode == 0 and "知识地图示例" in tex,
          "应把 map-config 的标题渲进去")

    if HAVE_TEX and kn_tex.exists():
        kn_pdf = tmp / "知识卡.pdf"
        cp, s = py("compile_study_pdf.py", kn_tex, kn_pdf)
        ok = cp.returncode == 0 and kn_pdf.exists() and kn_pdf.stat().st_size > 5000
        check("compile 知识卡 PDF", cp, s, ok)
    else:
        skip("compile 知识卡 PDF", "没有 xelatex")

    # ---- 13b/13c 计划与每日课：同一套地图机制的两个 kind，少了它们等于这两种产出没测过
    for kind, source, expect in (("plan", PLAN_MD, "备考路径示例"), ("day", DAY_MD, "每日课程示例")):
        md_kind = write(tmp / ("%s.md" % kind), source)
        tex_kind = tmp / ("%s.tex" % kind)
        cp, s = py("render_study_pdf.py", md_kind, tex_kind,
                   "--kind", kind, "--map-config", mapcfg)
        body = tex_kind.read_text(encoding="utf-8") if tex_kind.exists() else ""
        check("render %s" % kind, cp, s, cp.returncode == 0 and expect in body,
              "应把 map-config 里 %s 的标题渲进去" % kind)
        if HAVE_TEX and tex_kind.exists():
            pdf_kind = tmp / ("%s.pdf" % kind)
            cp, s = py("compile_study_pdf.py", tex_kind, pdf_kind)
            ok = cp.returncode == 0 and pdf_kind.exists() and pdf_kind.stat().st_size > 5000
            check("compile %s PDF" % kind, cp, s, ok)
        else:
            skip("compile %s PDF" % kind, "没有 xelatex")

    # ---- 14/15 试卷 tex（题 + 答案册）
    quiz_md = write(tmp / "试卷.md", QUIZ_MD)
    quiz_tex = tmp / "试卷.tex"
    key_tex = tmp / "试卷_答案.tex"
    cp, s = py("render_quiz_pdf.py", quiz_md, quiz_tex,
               "--course", COURSE, "--lesson", "第1讲", "--answers", key_tex)
    q_tex = quiz_tex.read_text(encoding="utf-8") if quiz_tex.exists() else ""
    ok = cp.returncode == 0 and key_tex.exists() and "三角不等式" not in q_tex
    check("render quiz（题卷不含答案）", cp, s, ok, "题卷不该出现答案文本")

    # md 第一行是 `# 文档标题`，卷头已有课程与讲次，它不该带井号漏进正文
    ok = cp.returncode == 0 and "随堂卷" not in q_tex
    check("render quiz（文档标题不进正文）", cp, s, ok,
          "md 第一行的 `# 标题` 该被忽略，不该渲染成正文")

    # 答案里空行分隔的每一段要各排成一段（一步一行靠这个）；连排成一整块就是退化了
    k_tex = key_tex.read_text(encoding="utf-8") if key_tex.exists() else ""
    ok = cp.returncode == 0 and k_tex.count(r"\par\noindent") >= 3
    check("render quiz（答案分段）", cp, s, ok,
          "答案 md 里空行分隔的三段该各排成一段，不该连排成一整块")

    if HAVE_TEX and quiz_tex.exists():
        quiz_pdf = tmp / "试卷.pdf"
        cp, s = py("compile_study_pdf.py", quiz_tex, quiz_pdf)
        ok = cp.returncode == 0 and quiz_pdf.exists() and quiz_pdf.stat().st_size > 5000
        check("compile 试卷 PDF", cp, s, ok)
    else:
        skip("compile 试卷 PDF", "没有 xelatex")

    # ---- 16 环境检查
    cp, s = py("check_env.py", "--json")
    try:
        payload = json.loads(cp.stdout)
        ok = cp.returncode == 0 and isinstance(payload, list) and len(payload) >= 5
    except Exception:  # noqa: BLE001
        ok = False
    check("check_env --json", cp, s, ok, "应输出可解析的 JSON 列表")

    # ---- 17 负向：课程名打错
    cp, s = py("qbank.py", "stats", "--course", "不存在的课")
    check("负向：课程名打错要报错", cp, s, cp.returncode != 0, "应 exit 非 0，而不是静默 0 道")

    # ---- 18 负向：缺 §答案
    noans = write(tmp / "无答案.md", "# 无答案卷\n\n**1.** 只有题目没有答案。\n")
    bad_tex = tmp / "不该出现.tex"
    cp, s = py("render_quiz_pdf.py", noans, bad_tex, "--course", COURSE, "--answers", tmp / "k.tex")
    check("负向：缺答案节不落盘", cp, s, cp.returncode != 0 and not bad_tex.exists(),
          "应 exit 非 0 且不写任何文件")

    # ---- 19 文档与脚本对账
    if (SCRIPTS / "doc_check.py").exists():
        cp, s = py("doc_check.py")
        check("doc_check 文档对账", cp, s, cp.returncode == 0,
              (cp.stdout or "").strip().splitlines()[-1] if cp.stdout.strip() else "见上")
    else:
        skip("doc_check 文档对账", "脚本还没装")

    # ---- 汇总
    fails = [r for r in RESULTS if r["status"] == "FAIL"]
    skips = [r for r in RESULTS if r["status"] == "SKIP"]
    total_secs = sum(r["secs"] for r in RESULTS)

    if args.json:
        print(json.dumps({"ok": not fails, "steps": RESULTS}, ensure_ascii=False, indent=2))
    else:
        print()
        print(f"{'步骤':<28}{'结果':<6}{'秒':>7}  说明")
        print("-" * 78)
        for r in RESULTS:
            note = r["note"][:34]
            print(f"{r['step']:<28}{r['status']:<6}{r['secs']:>7.2f}  {note}")
        print("-" * 78)
        print(f"{len(RESULTS)} 步：{len(RESULTS) - len(fails) - len(skips)} OK，"
              f"{len(fails)} FAIL，{len(skips)} SKIP · 共 {total_secs:.1f}s")
        if fails:
            print("\n整条链没跑通，别急着用。先修上面的 FAIL。")
        elif skips:
            why = "、".join(sorted({r["note"] for r in skips if r["note"]}))
            print(f"\n链是通的（跳过：{why}）。")
        else:
            print("\n整条链跑通了。")

    if args.keep:
        print(f"\n产物留在 {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
