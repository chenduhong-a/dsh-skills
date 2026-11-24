r"""Render a quiz / after-class exercise sheet from Markdown.

The sheet is meant to be written on: every question is followed by blank space
of `--blank` millimetres.  Answers are never printed on the question sheet; pass
`--answers` to get a second XeLaTeX file with the answer key on its own pages.

Markdown contract
-----------------
    ## 一、选择题                 -> section heading
    **1.** 题干                  -> question (also accepts `1. 题干`)
    ## 答案                      -> everything below is the answer key
    - 附加说明                   -> bullet
    # 文档标题                    -> ignored (卷头已由 --course / --lesson 呈现)

Compile the produced .tex with xelatex (twice).
"""

from __future__ import annotations

import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import datetime as dt
import re
from pathlib import Path

from render_study_pdf import PREAMBLE, inline

QUESTION = re.compile(r"^\*\*((?:[A-Z]?\d+|题\s*\d+))[.．:：]\*\*\s*(.*)$")
ORDERED = re.compile(r"^(\d+)[.．]\s+(.*)$")
HEADING = re.compile(r"^(#{2,3})\s+(.*)$")
DOC_TITLE = re.compile(r"^#\s+\S")
ANSWER_MARK = re.compile(r"^#{2,3}\s*答案")

SHEET = r"""
\newcommand{\quizhead}[3]{%
  \thispagestyle{plain}%
  \noindent{\sffamily\footnotesize #1}\hfill{\sffamily\footnotesize #2}\par
  \vspace{2mm}\noindent{\LARGE\bfseries\sffamily #3}\par
  \vspace{1mm}\noindent{\sffamily\footnotesize 姓名\rule{3.6cm}{.4pt}\quad 学号\rule{3cm}{.4pt}\quad 日期\rule{2.6cm}{.4pt}}\par
  \vspace{3mm}\noindent\rule{\linewidth}{.85pt}\par\vspace{4mm}}
\newcommand{\sheetnote}[1]{\noindent{\sffamily\footnotesize #1}\par\vspace{2mm}}
\newcommand{\answerhead}[2]{\thispagestyle{plain}\noindent{\sffamily\footnotesize #1}\hfill{\sffamily\footnotesize #2}\par\vspace{2mm}\noindent{\LARGE\bfseries\sffamily 参考答案}\par\vspace{3mm}\noindent\rule{\linewidth}{.85pt}\par\vspace{4mm}}
"""


def split_answers(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if ANSWER_MARK.match(line.strip()):
            return "\n".join(lines[:index]), "\n".join(lines[index + 1 :])
    return markdown, ""


def meaningful(text: str) -> str:
    """去掉会被 DOC_TITLE 丢掉的 `# 一级标题` 行与空白后，剩下的正文。

    判空必须看渲染后的结果：只写了一行 `# 答案` 的答案节原文非空，
    排出来却一个字都没有。
    """
    kept = [line for line in text.splitlines() if not DOC_TITLE.match(line.strip())]
    return "\n".join(kept).strip()


def question_tex(prompt: str, label: str, blank_mm: int) -> str:
    return (
        r"\par\Needspace{5\baselineskip}\noindent"
        + r"\begin{minipage}{\linewidth}\textbf{"
        + inline(label)
        + r".}\ "
        + inline(prompt)
        + r"\par\noindent\rule{0pt}{"
        + str(blank_mm)
        + r"mm}\par\end{minipage}\par\vspace{1.2em}"
    )


def body_tex(markdown: str, blank_mm: int | None) -> list[str]:
    out: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def flush() -> None:
        nonlocal paragraph
        if paragraph:
            # 每个空行分隔的段独立成段（答案一步一行靠这个）；不加 \par 时
            # 相邻段会被 LaTeX 当成同一段连排，步骤就挤成一大块
            out.append(r"\par\noindent " + inline(" ".join(paragraph)))
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(r"\end{itemize}")
            in_list = False

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            close_list()
            continue
        if DOC_TITLE.match(line):
            # 一行 `# 文档标题` 不进正文：卷头已由 --course / --lesson 呈现
            flush()
            close_list()
            continue
        heading = HEADING.match(line)
        if heading:
            flush()
            close_list()
            level, title = heading.groups()
            command = "section" if len(level) == 2 else "subsection"
            out.append("\\" + command + "{" + inline(title) + "}")
            continue
        question = QUESTION.match(line)
        if question:
            flush()
            close_list()
            label, prompt = question.groups()
            if blank_mm is None:
                out.append(
                    r"\par\noindent\textbf{"
                    + inline(label)
                    + r".}\ "
                    + inline(prompt)
                    + r"\par\vspace{.8em}"
                )
            else:
                out.append(question_tex(prompt, label, blank_mm))
            continue
        ordered = ORDERED.match(line)
        if ordered:
            flush()
            close_list()
            label, prompt = ordered.groups()
            if blank_mm is None:
                out.append(
                    r"\par\noindent\textbf{"
                    + inline(label)
                    + r".}\ "
                    + inline(prompt)
                    + r"\par\vspace{.8em}"
                )
            else:
                out.append(question_tex(prompt, label, blank_mm))
            continue
        if line.startswith("- "):
            flush()
            if not in_list:
                out.append(r"\begin{itemize}")
                in_list = True
            out.append(r"\item " + inline(line[2:]))
            continue
        close_list()
        paragraph.append(line.strip())
    flush()
    close_list()
    return out


def build(
    markdown: str,
    course: str,
    lesson: str,
    blank_mm: int | None,
    answers: bool,
    mention_key: bool = False,
) -> str:
    today = dt.date.today().isoformat()
    questions, key = split_answers(markdown)
    head = SHEET
    if answers:
        # 答案册不印姓名/学号/日期——那三栏只有答卷才用
        parts = [PREAMBLE, head, r"\answerhead{" + inline(course) + "}{" + today + "}"]
    else:
        parts = [
            PREAMBLE,
            head,
            r"\quizhead{"
            + inline(course)
            + "}{"
            + today
            + "}{"
            + inline(lesson or "练习")
            + "}",
        ]
        if mention_key:
            parts.append(
                r"\sheetnote{每小题下方留 "
                + str(blank_mm)
                + r" mm 作答空间；答案见单独文件。}"
            )
    parts.extend(body_tex(questions if not answers else key, None if answers else blank_mm))
    parts.append(r"\end{document}")
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Markdown with questions")
    parser.add_argument("output", type=Path, help="Question sheet .tex")
    parser.add_argument("--course", required=True)
    parser.add_argument("--lesson", default="")
    parser.add_argument("--blank", type=int, default=30, help="blank space per question, mm")
    parser.add_argument("--answers", type=Path, help="answer key .tex (from the ## 答案 section)")
    args = parser.parse_args()

    # 三道闸门：参数边界 + 路径互斥 + 空内容
    if args.blank < 0:
        parser.error(f"--blank 要 ≥ 0（单位 mm），收到 {args.blank}；负值会让题目与题目挤在一起")
    if args.blank > 200:
        parser.error(f"--blank 太大了（{args.blank} mm），一页放不下一题；A4 高度才 297 mm，改小一点")
    paths = {"源文件": args.source, "题卷": args.output}
    if args.answers:
        paths["答案册"] = args.answers
    seen = {}
    for role, p in paths.items():
        real = p.resolve()
        if real in seen:
            parser.error(f"{role}与{seen[real]}是同一个文件（{real}），会互相覆盖；换一个输出路径")
        seen[real] = role

    markdown = args.source.read_text(encoding="utf-8")
    questions, key = split_answers(markdown)
    # 判空要看「渲染后还剩什么」：只有一行 `# 标题` 的答案节会被 DOC_TITLE 丢掉，
    # 原文非空却排出来是空的——这种「以为写了答案、其实一个字没印」的情况必须拦住
    if args.answers and not meaningful(key):
        parser.error(
            "答案节是空的：`## 答案` 下面只有标题，没有正文。"
            "把每题的答案写进去（一到四步，每步之间空一行）再生成答案册"
        )
    if not meaningful(questions):
        parser.error("这道卷子里没有题目：`## 一、…` 下面至少要有一道 `**1.** 题干`")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        build(questions, args.course, args.lesson, args.blank, answers=False, mention_key=bool(args.answers)),
        encoding="utf-8",
    )
    if args.answers:
        args.answers.parent.mkdir(parents=True, exist_ok=True)
        args.answers.write_text(
            build(markdown, args.course, args.lesson, None, answers=True),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
