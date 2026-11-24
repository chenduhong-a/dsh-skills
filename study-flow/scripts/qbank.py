#!/usr/bin/env python3
r"""qbank.py —— 本地题库、作答记录与排期（FSRS-6 四档评分版）。

数据放在 <progress_dir>/<课程名>/ 下：
    题库.jsonl   每题一行
    作答.jsonl   每次作答一行（对错 + 断在第几步 + 信心 + 是否计入）
    排期.json    qid -> {due, stability, difficulty, interval, ...}；"_meta" 存考试日等课程级设置

排期口径（FSRS-6，与 ts-fsrs 标准实现同一组权重、同一条曲线）：
    四档评分  again=1 / hard=2 / good=3 / easy=4
    遗忘曲线  R = (1 + FACTOR * t / S) ^ DECAY
    首次      S = w[g-1]，D = w4 - e^(w5*(g-1)) + 1
    答对      S' = S * (1 + e^w8*(11-D)*S^-w9*(e^(w10*(1-R))-1)*hard*easy)
    答错      S' = min(S, w11*D^-w12*((S+1)^w13-1)*e^((1-R)*w14))
    难度      D' = D - w6*(g-3)*(10-D)/9，再向 D0(4) 回归 w7
    下次间隔  interval = clamp(round(S'), 1, 36500)
与标准实现的差别只剩两处：公式相同，但那些实现通常把 enable_short_term / enable_fuzz 设为 false，
这里同样不做短期步骤与随机抖动——间隔天数应当逐项对得上。
"""

import argparse
import json
import math
import os
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS = "学习进度"

# FSRS-6 默认权重（前 21 个），只用到其中 8 个
W = [
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
    1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
    1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
]
DECAY = -W[20]
FACTOR = math.exp(math.log(0.9) / DECAY) - 1
MIN_S, MAX_S = 0.1, 36500.0
MIN_D, MAX_D = 1.0, 10.0
MAX_INTERVAL = 36500
GRADES = {"again": 1, "hard": 2, "good": 3, "easy": 4}
GRADE_LABEL = {1: "again 忘了", 2: "hard 提示后想起", 3: "good 独立做对", 4: "easy 秒答"}


def grade_of(args) -> int:
    """四档评分；--correct/--wrong 作为兼容别名。"""
    raw = getattr(args, "grade", None)
    if raw:
        return GRADES[raw]
    return 3 if getattr(args, "correct", False) else 1

# 不计入掌握与错题本的作答类型
EXCLUDED = ("retry", "self_reported", "implicit", "simulated")


# ---------------------------------------------------------------- 配置与路径

def load_config() -> dict:
    p = SKILL_DIR / "config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"config.json 解析失败（{p}）：{exc}\n"
            "先修好它再跑——带着坏配置写盘会落到错误的目录。"
        ) from exc


def progress_root() -> Path:
    env = os.environ.get("QBANK_PROGRESS")
    if env:
        return Path(env)
    cfg = load_config()
    raw = cfg.get("progress_dir") or DEFAULT_PROGRESS
    p = Path(raw)
    if not p.is_absolute():
        study_dir = cfg.get("study_dir")
        if not study_dir:
            raise SystemExit(
                "progress_dir 是相对路径，但 config.json 里没有 study_dir。\n"
                "先跑 init.py，或把 study_dir 补上——别让它回落到当前目录写题库。"
            )
        p = Path(study_dir) / p
    return p


def course_dir(course: str, create: bool = False) -> Path:
    p = progress_root() / course
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def require_course(course: str) -> Path:
    """读命令用：课程目录不存在就报错，别静默返回空。"""
    p = course_dir(course)
    if not p.is_dir():
        root = progress_root()
        names = sorted(x.name for x in root.iterdir() if x.is_dir()) if root.is_dir() else []
        raise SystemExit(
            f"没有这门课：{p}\n现有课程：{'、'.join(names) if names else '（空）'}\n"
            "课程名要与 学习进度\\ 下的目录名一致。"
        )
    return p


def bank_path(course: str) -> Path:
    return course_dir(course) / "题库.jsonl"


def attempts_path(course: str) -> Path:
    return course_dir(course) / "作答.jsonl"


def schedule_path(course: str) -> Path:
    return course_dir(course) / "排期.json"


# ---------------------------------------------------------------- 读写

def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(
                    f"{path.name} 第 {lineno} 行不是合法 JSON（{exc.msg}）。\n"
                    f"  多半是手工编辑时改坏了，或写盘中断。这一行原文：\n"
                    f"  {line[:120]}\n"
                    f"  修法：改好这一行；或用 qbank.py restore 从 backup\\ 里的 zip 恢复。"
                ) from None
    return out


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except PermissionError as exc:
        raise SystemExit(
            f"写不了 {path.name}：{exc}\n"
            "  文件可能是只读，或被别的程序占用。关掉打开它的编辑器再试。"
        ) from None


@contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    """抢一个 <path>.lock 独占文件，把「读-改-写」关进临界区。

    Windows 上两个进程同时以追加模式打开同一文件会互相覆盖写指针，
    实测两个进程各加 5 题只落下 7 题、id 还撞号。加锁后串行化。
    """
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    fd = None
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise SystemExit(
                    f"另一个 qbank 正在写 {path.name}，等了 {timeout:.0f} 秒还没放手。\n"
                    f"  等它写完再试；确认没有 qbank 在跑的话，删掉这个文件后重来：\n  {lock}"
                ) from None
            time.sleep(0.02)
        except PermissionError as exc:
            raise SystemExit(
                f"写不了 {path}：{exc}\n  文件可能是只读，或被别的程序占用。"
            ) from None
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock.unlink()
        except OSError:
            pass


def load_schedule(course: str) -> dict:
    p = schedule_path(course)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"排期文件解析失败（{p}）：{exc}\n"
            "先修好或从备份恢复——它一旦被当成空排期写回，其它题的复习进度就没了。"
        ) from exc


def save_schedule(course: str, sched: dict) -> None:
    p = schedule_path(course)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.tmp{os.getpid()}")
    try:
        tmp.write_text(json.dumps(sched, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)  # 原子替换：写到一半崩了也不会留半截排期
    except PermissionError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise SystemExit(
            f"写不了 {p.name}：{exc}\n  文件可能是只读，或被别的程序占用。"
        ) from None


# ---------------------------------------------------------------- 排期核心

def clamp(x: float, lo: float = MIN_S, hi: float = MAX_S) -> float:
    return max(lo, min(hi, x))


def init_difficulty(grade: int) -> float:
    """D0(g) = w4 - e^(w5*(g-1)) + 1，夹在 1–10。"""
    return min(MAX_D, max(MIN_D, W[4] - math.exp(W[5] * (grade - 1)) + 1))


def next_difficulty(difficulty: float, grade: int) -> float:
    """FSRS-6 难度更新：先按偏差线性推进，再向 D0(easy) 均值回归 w7。"""
    moved = difficulty - W[6] * (grade - 3) * (MAX_D - difficulty) / 9.0
    regressed = W[7] * init_difficulty(4) + (1 - W[7]) * moved
    return min(MAX_D, max(MIN_D, regressed))


def retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    r = (1 + FACTOR * elapsed_days / stability) ** DECAY
    return max(0.0, min(1.0, r))


def next_stability(stability: float, difficulty: float, grade: int, elapsed_days: float) -> float:
    r = retrievability(elapsed_days, stability)
    if grade == 1:
        forget = (
            W[11] * difficulty ** (-W[12]) * ((stability + 1) ** W[13] - 1)
            * math.exp((1 - r) * W[14])
        )
        return clamp(min(stability, forget))
    hard_penalty = W[15] if grade == 2 else 1.0
    easy_bonus = W[16] if grade == 4 else 1.0
    grow = (
        1
        + math.exp(W[8]) * (11 - difficulty) * stability ** (-W[9])
        * (math.exp(W[10] * (1 - r)) - 1) * hard_penalty * easy_bonus
    )
    return clamp(stability * grow)


def review(entry: dict, grade: int, today: date, exam: date | None = None) -> dict:
    """推进一条排期。首次用 S0(g)/D0(g)；之后按 FSRS-6 双状态更新。"""
    stability = entry.get("stability")
    difficulty = entry.get("difficulty")
    last_raw = entry.get("last")
    lapses = int(entry.get("lapses") or 0)
    reps = int(entry.get("reps") or 0)
    correct = grade >= 2

    if last_raw:
        try:
            elapsed = max(0, (today - date.fromisoformat(last_raw)).days)
        except ValueError:
            elapsed = 0
    else:
        elapsed = 0

    if stability is None:
        legacy_interval = float(entry.get("interval") or 0)
        if legacy_interval > 0 and difficulty is not None:
            # 旧记录：用已存的间隔与难度接着推，不重新初始化
            new_s = next_stability(
                clamp(legacy_interval), float(difficulty), grade, elapsed
            )
            new_d = next_difficulty(float(difficulty), grade)
        else:
            new_s = clamp(float(W[grade - 1]))
            new_d = init_difficulty(grade)
    else:
        used_d = float(difficulty) if difficulty is not None else init_difficulty(grade)
        new_s = next_stability(float(stability), used_d, grade, elapsed)
        new_d = next_difficulty(used_d, grade)
    interval = max(1, min(MAX_INTERVAL, int(round(new_s))))

    if correct:
        reps += 1
    else:
        reps = 0
        lapses += 1

    due = today + timedelta(days=interval)
    out = {
        "due": due.isoformat(),
        "stability": round(new_s, 4),
        "difficulty": round(new_d, 4),
        "grade": grade,
        "interval": interval,
        "reps": reps,
        "lapses": lapses,
        "last": today.isoformat(),
    }
    if exam and date.fromisoformat(out["due"]) > exam:
        out["unaligned_due"] = out["due"]
        out["due"] = exam.isoformat()
    return out


# ---------------------------------------------------------------- 子命令

def cmd_init(args) -> int:
    d = course_dir(args.course, create=True)
    for f in (bank_path(args.course), attempts_path(args.course)):
        f.touch(exist_ok=True)
    if not schedule_path(args.course).exists():
        save_schedule(args.course, {})
    print(f"已备好：{d}")
    print(f"  题库 {bank_path(args.course).name} / 作答 {attempts_path(args.course).name} / 排期 {schedule_path(args.course).name}")
    return 0


def cmd_exam(args) -> int:
    if not args.date:
        sched = load_schedule(args.course)
        exam = sched.get("_meta", {}).get("exam_date")
        print(f"考试日：{exam or '未设置'}")
        return 0
    sched = load_schedule(args.course)
    meta = sched.setdefault("_meta", {})
    meta["exam_date"] = args.date.isoformat()
    save_schedule(args.course, sched)
    print(f"考试日已设为 {args.date}；排期时到期日不晚于这一天，原始到期日另存 unaligned_due")
    return 0


VAGUE = ("如上图", "如下图", "如图", "由上图", "前面提到的", "由上可知", "同上题", "见上文")


def check_quote(quote, corpus):
    """引文是否真的在原文里（去掉全部空白与换行后按子串比）。None 表示没法判。"""
    if not quote or not corpus:
        return None
    norm = lambda s: "".join(str(s).split())
    return norm(quote) in norm(corpus)


def audit_row(item, items=None, corpus=None) -> list:
    """收题六问里能自动判的那几条。返回提示列表，空表示没发现问题。

    corpus 给了就在原文里逐字核对引文；没给但带了引文，就提示还没校验。
    """
    warns = []
    prompt = (item.get("prompt") or "").strip()
    answer = (item.get("answer") or "").strip()
    source = (item.get("source") or "").strip()
    options = item.get("options") or []

    if len(prompt) < 8:
        warns.append("题干太短，可能说不清问的是什么")
    for word in VAGUE:
        if word in prompt:
            warns.append(f"题干里有「{word}」：不配图或上文时答不了，换成本题自带的描述")
            break
    if not answer:
        warns.append("没有答案：判分时无从对照")
    if not source:
        warns.append("没有出处：以后核对不了，也说不清考的是哪一段")
    if options:
        if len(options) < 2:
            warns.append("选项少于两个：选择题至少要能排除")
        clean = [o.strip() for o in options]
        if len(set(clean)) != len(clean):
            warns.append("选项有重复")
    quote = (item.get("quote") or "").strip()
    if quote:
        hit = check_quote(quote, corpus) if corpus else None
        if hit is False:
            warns.append("引文在原文里找不到：逐字核对一遍，或换一段能对上的")
        elif hit is None:
            warns.append("引文还没和原文比对过（加 --verify <原文文件> 让它查）")
    if items:
        key = "".join(prompt.split())[:40]
        for old in items:
            if key and "".join((old.get("prompt") or "").split())[:40] == key:
                warns.append(f"可能和 {old.get('id')} 重复")
                break
    return warns


def cmd_add(args) -> int:
    with file_lock(bank_path(args.course)):
        return _add_locked(args)


def _add_locked(args) -> int:
    items = read_jsonl(bank_path(args.course))
    n = len(items) + 1
    qid = args.id or f"q-{n:04d}"
    while any(it.get("id") == qid for it in items):
        n += 1
        qid = f"q-{n:04d}"
    options = None
    if args.options:
        options = [s.strip() for s in args.options.split("|")]
    item = {
        "id": qid,
        "course": args.course,
        "chapter": args.chapter or "",
        "topic": args.topic or "",
        "kind": args.kind,
        "prompt": args.prompt,
        "options": options,
        "answer": args.answer,
        "rubric": args.rubric or "",
        "source": args.source or "",
        "quote": (getattr(args, "quote", "") or ""),
        "created": date.today().isoformat(),
    }
    corpus = None
    vf = getattr(args, "verify", "") or ""
    if vf:
        try:
            corpus = open(vf, encoding="utf-8").read()
        except OSError as e:
            print(f"  ! 读不到原文文件 {vf}：{e}")
    if not getattr(args, "no_check", False):
        warns = audit_row(item, items, corpus)
        for w in warns:
            print(f"  ! {w}")
        if warns and getattr(args, "strict", False):
            print("收题检查没过（--strict），没有写入。去掉 --strict 可强制加入。")
            return 1
        if warns:
            print("（以上只是提示，仍然写入了；改好可以 add 一遍再删旧的）")

    append_jsonl(bank_path(args.course), item)
    print(f"已加入 {qid}：{args.prompt[:40]}")
    return 0


def _filter(items, chapter=None, topic=None):
    out = items
    if chapter:
        out = [it for it in out if it.get("chapter") == chapter]
    if topic:
        out = [it for it in out if it.get("topic") == topic]
    return out


def cmd_list(args) -> int:
    require_course(args.course)
    items = _filter(read_jsonl(bank_path(args.course)), args.chapter, args.topic)
    if not items:
        print("题库里没有符合条件的题。")
        return 0
    sched = load_schedule(args.course)
    for it in items:
        s = sched.get(it["id"], {})
        tail = f"到期 {s['due']} / 间隔 {s['interval']}d" if s else "未作答"
        print(f"{it['id']} [{it.get('chapter') or '-'}·{it.get('topic') or '-'}] {it['prompt'][:50]}  ({tail})")
    print(f"共 {len(items)} 题")
    return 0


def cmd_pick(args) -> int:
    require_course(args.course)
    items = _filter(read_jsonl(bank_path(args.course)), args.chapter, args.topic)
    if not items:
        print("没有可抽的题。")
        return 1
    sched = load_schedule(args.course)
    today = args.date if args.date else date.today()
    due, fresh, later = [], [], []
    broken = 0
    for it in items:
        s = sched.get(it["id"])
        if not s:
            fresh.append(it)
            continue
        try:
            due_on = date.fromisoformat(s.get("due") or "")
        except ValueError:
            broken += 1
            fresh.append(it)  # 排期坏了当新题，不整条链崩
            continue
        if due_on <= today:
            due.append((s["due"], it))
        else:
            later.append((s["due"], it))
    if broken:
        print(f"!! 排期里有 {broken} 条缺 due 或格式不对，已当新题处理", file=sys.stderr)
    due.sort(key=lambda x: x[0])
    order = [it for _, it in due] + fresh + [it for _, it in later]
    picked = order[: args.n]
    for it in picked:
        s = sched.get(it["id"], {})
        mark = "到期" if it in [x for _, x in due] else ("新题" if it in fresh else f"未到期 {s.get('due')}")
        print(f"--- {it['id']} · {mark} · {it.get('chapter') or '-'} / {it.get('topic') or '-'}")
        print(it["prompt"])
        if it.get("options"):
            for i, o in enumerate(it["options"]):
                print(f"  {chr(65 + i)}. {o}")
        if args.with_answer and it.get("answer"):
            print(f"  〔答案〕{it['answer']}")
    return 0


def _flags(args) -> list:
    return [k for k in EXCLUDED if getattr(args, k.replace("_", "-").replace("-", "_"), False)]


def cmd_grade(args) -> int:
    with file_lock(bank_path(args.course)):
        return _grade_locked(args)


def _grade_locked(args) -> int:
    items = {it["id"]: it for it in read_jsonl(bank_path(args.course))}
    it = items.get(args.qid)
    if not it:
        print(f"题库里没有 {args.qid}")
        return 1
    grade = grade_of(args)
    correct = grade >= 2
    flags = [k for k in EXCLUDED if getattr(args, k, False)]
    counted = not flags
    today = date.today()
    sched = load_schedule(args.course)
    exam_raw = sched.get("_meta", {}).get("exam_date")
    exam = date.fromisoformat(exam_raw) if exam_raw else None

    if counted:
        old = sched.get(args.qid, {})
        sched[args.qid] = {**old, **review(old, grade, today, exam)}
        save_schedule(args.course, sched)

    append_jsonl(attempts_path(args.course), {
        "qid": args.qid,
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "correct": correct,
        "grade": grade,
        "step_break": args.step,
        "confidence": args.confidence or "",
        "note": args.note or "",
        "counted": counted,
        "excluded_as": ",".join(flags) if flags else "",
    })

    if not counted:
        print(
            f"{args.qid} 记 {GRADE_LABEL[grade]}"
            f"（{'/'.join(flags)}，不计入掌握，不动排期）"
        )
        return 0
    s = sched[args.qid]
    print(
        f"{args.qid} 记 {GRADE_LABEL[grade]}；下次 {s['due']}"
        f"（间隔 {s['interval']} 天，S={s['stability']}，D={s['difficulty']}）"
    )
    if s.get("unaligned_due"):
        print(f"  原始到期 {s['unaligned_due']}，因考试日 {exam_raw} 提前")
    return 0


def cmd_due(args) -> int:
    require_course(args.course)
    items = {it["id"]: it for it in read_jsonl(bank_path(args.course))}
    sched = load_schedule(args.course)
    today = args.date if args.date else date.today()
    rows, broken = [], 0
    for qid, s in sched.items():
        if qid == "_meta":
            continue
        try:
            due_on = date.fromisoformat(s.get("due") or "")
        except ValueError:
            broken += 1
            continue
        if due_on <= today:
            rows.append((s["due"], qid))
    rows.sort()
    if broken:
        print(f"!! 排期里有 {broken} 条缺 due 或格式不对，已跳过", file=sys.stderr)
    if not rows:
        print("今天没有到期的题。")
        return 0
    for due, qid in rows:
        it = items.get(qid, {})
        print(f"{due}  {qid}  {it.get('prompt', '(题库里已删)')[:50]}")
    print(f"共 {len(rows)} 道到期")
    return 0


def count_failures(attempts: list, qid: str) -> tuple:
    """顽固题判据：总失败数、最近 5 次失败率、最近 5 条、是否已解除、是否算顽固。

    解除条件：最近连续 3 次全对——重新做对就不再挂着，不需要手工清。
    顽固判据（至少作答 3 次，两条满足一条）：累计失败 >= 3 次，或最近 5 次里错 >= 60%。
    判据只在这里定义一份，stats 与 errors 都调它——两处各写一套就会「同一道题
    在统计里算顽固、在错题本里不标」。
    """
    mine = [a for a in attempts if a.get("qid") == qid and a.get("counted", True)]
    fails = sum(1 for a in mine if not a.get("correct"))
    recent = mine[-5:]
    rate = (sum(1 for a in recent if not a.get("correct")) / len(recent)) if recent else 0.0
    last3 = mine[-3:]
    cleared = len(last3) >= 3 and all(a.get("correct") for a in last3)
    stubborn = (not cleared) and len(recent) >= 3 and (fails >= 3 or rate >= 0.6)
    return fails, rate, recent, cleared, stubborn


def _print_self_assessment(attempts: list) -> None:
    """自评四档的分布与「事后翻车率」。

    注意：本工具里 correct 就是 grade >= 2，所以「自评 good 占比」与「客观正确率」
    永远同向（good/easy 是 correct 的子集），拿两者比是空转——早先那版
    「good/easy 八成以上而正确率不到六成」在数学上不可能成立，已废弃。
    真正能验自评准不准的只有一件事：判了 good/easy 之后，同一题下次还错不错。
    """
    graded = [a for a in attempts if a.get("grade") in (1, 2, 3, 4)]
    if not graded:
        return
    n = len(graded)
    good = sum(1 for a in graded if a["grade"] >= 3)
    again = sum(1 for a in graded if a["grade"] == 1)
    hard = n - good - again
    print(
        f"  自评：good/easy {good / n:.0%} · hard {hard / n:.0%} · again {again / n:.0%}"
        f"（{n} 次带评分记录）"
    )

    by_qid = {}
    for a in attempts:
        by_qid.setdefault(a.get("qid"), []).append(a)
    judged = relapsed = 0
    for rows in by_qid.values():
        rows.sort(key=lambda x: x.get("ts", ""))
        for prev, nxt in zip(rows, rows[1:]):
            if prev.get("grade", 0) >= 3:
                judged += 1
                if not nxt.get("correct"):
                    relapsed += 1
    rate = relapsed / judged if judged else 0.0
    if (judged >= 2 and rate >= 0.5) or (judged >= 4 and rate >= 0.25):
        print(
            f"  评得偏松：判过 good/easy 的 {judged} 次里，同题下一次又错 {relapsed} 次"
            f"（{rate:.0%}）。要么把 good 压成 hard——只把「不用想就能写出来」判 good；"
            "要么是隔得太久忘了，那就把间隔调短。"
        )
    if n >= 6 and hard / n >= 0.4:
        print(
            f"  hard 占 {hard / n:.0%}：多数题要提示才想得起，说明还在理解阶段，"
            "先把这一章的推导讲一遍再刷题，别急着往下走。"
        )


def cmd_stats(args) -> int:
    require_course(args.course)
    items = read_jsonl(bank_path(args.course))
    all_attempts = read_jsonl(attempts_path(args.course))
    attempts = [a for a in all_attempts if a.get("counted", True)]
    since = getattr(args, "since", None)
    if since:
        lo = since.isoformat()
        attempts = [a for a in attempts if str(a.get("ts", ""))[:10] >= lo]
    sched = load_schedule(args.course)
    today = date.today()
    due, bad_due = 0, 0
    for k, s in sched.items():
        if k == "_meta":
            continue
        raw = s.get("due") if isinstance(s, dict) else None
        try:
            if date.fromisoformat(str(raw)) <= today:
                due += 1
        except (TypeError, ValueError):
            bad_due += 1
    if bad_due:
        print(f"!! 排期里有 {bad_due} 条缺 due 或格式不对，已跳过（不写回，修不修由你）。")
    n_att = len(attempts)
    n_ok = sum(1 for a in attempts if a.get("correct"))
    rate = f"{n_ok / n_att:.0%}" if n_att else "-"
    by_topic = {}
    for a in attempts:
        it = next((x for x in items if x["id"] == a["qid"]), None)
        if not it:
            continue
        t = it.get("topic") or "(未标知识点)"
        d = by_topic.setdefault(t, [0, 0])
        d[0] += 1
        if not a.get("correct"):
            d[1] += 1
    weak = sorted(((t, v[0], v[1]) for t, v in by_topic.items() if v[1]), key=lambda x: -x[2])[:5]
    stubborn = []
    for it in items:
        fails, rate5, recent, cleared, is_stub = count_failures(all_attempts, it["id"])
        if is_stub:
            stubborn.append((it["id"], it.get("topic") or "-", fails, f"{rate5:.0%}"))
    print(f"课程 {args.course}")
    print(f"  题 {len(items)} 道 · 已作答 {n_att} 次 · 正确率 {rate} · 今天到期 {due} 道")
    print(f"  从未作答 {len([i for i in items if i['id'] not in sched])} 道")
    skipped = len(all_attempts) - n_att
    if skipped:
        print(f"  不计入掌握 {skipped} 次（重试 / 自报 / 隐式 / 模拟）")
    if weak:
        print("  错得最多：")
        for t, n, bad in weak:
            print(f"    {t}  错 {bad}/{n}")
    if stubborn:
        print("  顽固题（失败 ≥3 次 或 最近 5 次错 ≥60%）：")
        for qid, topic, fails, rate5 in stubborn[:8]:
            print(f"    {qid}  {topic}  累计错 {fails} 次 · 近 5 次错 {rate5}")
    _print_self_assessment(attempts)
    return 0


def cmd_audit(args) -> int:
    require_course(args.course)
    items = _filter(read_jsonl(bank_path(args.course)), args.chapter, args.topic)
    if not items:
        print("题库里没有符合条件的题。")
        return 0
    flagged = 0
    for it in items:
        warns = audit_row(it, [x for x in items if x.get("id") != it.get("id")])
        if not warns:
            continue
        flagged += 1
        print(f"{it.get('id')}  {it.get('topic') or it.get('chapter') or ''}")
        for w in warns:
            print(f"    - {w}")
    print(f"\n共 {len(items)} 题，{flagged} 题有提示。")
    return 1 if flagged else 0


def cmd_export(args) -> int:
    require_course(args.course)
    items = read_jsonl(bank_path(args.course))
    lines = [f"# {args.course} 题库", "", f"共 {len(items)} 题", ""]
    for it in items:
        lines.append(f"## {it['id']} · {it.get('chapter') or '-'} / {it.get('topic') or '-'}")
        lines.append("")
        lines.append(it["prompt"])
        lines.append("")
        if it.get("options"):
            for i, o in enumerate(it["options"]):
                lines.append(f"- {chr(65 + i)}. {o}")
            lines.append("")
        lines.append(f"答案：{it.get('answer') or '（见 rubric）'}")
        if it.get("rubric"):
            lines.append(f"评分：{it['rubric']}")
        if it.get("source"):
            lines.append(f"出处：{it['source']}")
        lines.append("")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"已导出 {len(items)} 题 -> {out}")
    return 0


def _course_files(course: str) -> list:
    d = course_dir(course)
    names = ["题库.jsonl", "作答.jsonl", "排期.json", "进度.md", "能力评价.md"]
    return [d / n for n in names if (d / n).exists()]


def cmd_backup(args) -> int:
    with file_lock(bank_path(args.course)):
        return _backup_locked(args)


def _backup_locked(args) -> int:
    import zipfile
    d = require_course(args.course)
    files = _course_files(args.course)
    if not files:
        print(f"{d} 里没有可备份的文件（题库 / 作答 / 排期 一个都没找到）。")
        return 2
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else d / "backup" / f"{args.course}-{stamp}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "course": args.course,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": len(read_jsonl(bank_path(args.course))),
        "attempts": len(read_jsonl(attempts_path(args.course))),
        "files": [f.name for f in files],
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.name)
        zf.writestr("_meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"已备份 {len(files)} 个文件 -> {out}")
    for f in files:
        print(f"  {f.name}")
    print(f"  含 {meta['items']} 题 · {meta['attempts']} 次作答记录")
    if "题库.jsonl" not in meta["files"]:
        print("  !! 这门课还没有 题库.jsonl——这个包只含进度与评价，恢复出来不会有题目。")
    return 0


def cmd_restore(args) -> int:
    with file_lock(bank_path(args.course)):
        return _restore_locked(args)


def _restore_locked(args) -> int:
    """先解到暂存目录校验，全部成功后才动原目录——失败时一个字节都不改。"""
    import shutil
    import zipfile
    src = Path(args.src)
    if not src.is_file():
        print(f"找不到备份文件：{src}", file=sys.stderr)
        return 2
    d = course_dir(args.course, create=True)
    stage = d.parent / f".restore-{args.course}-{os.getpid()}"
    known = {"题库.jsonl", "作答.jsonl", "排期.json", "进度.md", "能力评价.md"}
    try:
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/") and not n.startswith("_")]
            for n in names:
                if "/" in n.replace("\\", "/").strip("/") or ".." in n:
                    print(f"备份里有越界路径，拒绝解压：{n}", file=sys.stderr)
                    return 2
            if not (set(names) & known):
                print(f"这个 zip 里没有任何课程文件（题库 / 作答 / 排期 / 进度 / 评价），不像课程备份：{src}",
                      file=sys.stderr)
                return 2
            zf.extractall(stage)
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        print(f"这个包解不开（坏包、被截断或某个文件损坏）：{exc}\n  原文件一个都没动。",
              file=sys.stderr)
        return 2
    finally:
        pass
    try:
        meta_raw = (stage / "_meta.json").read_text(encoding="utf-8")
        meta_course = str(json.loads(meta_raw).get("course") or "")
    except (OSError, ValueError):
        meta_course = ""
    if meta_course and meta_course != args.course:
        shutil.rmtree(stage, ignore_errors=True)
        print(f"这个备份是「{meta_course}」的，不是「{args.course}」的——拒绝了，原文件一个都没动。\n"
              f"  确实要恢复到这门课：先解压改 _meta.json 的 course；或换 --course {meta_course}。",
              file=sys.stderr)
        return 2
    keep = d / "backup" / ("pre-restore-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    saved = []
    for existing in _course_files(args.course):
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copy2(existing, keep / existing.name)
        saved.append(existing.name)
    removed = []
    for existing in _course_files(args.course):
        try:
            existing.unlink()
            removed.append(existing)
        except OSError as exc:
            # 删到一半失败：把已经删掉的逐个放回去，保证原数据一个不少
            for back in removed:
                try:
                    shutil.copy2(keep / back.name, back)
                except OSError:
                    pass
            shutil.rmtree(stage, ignore_errors=True)
            print(f"删不掉旧文件 {existing.name}：{exc}\n"
                  f"  已经删掉的 {len(removed)} 个已放回原处，这次恢复没有生效；"
                  f"去掉只读后重试。", file=sys.stderr)
            return 2
    moved = []
    for item in sorted(stage.iterdir()):
        if item.name == "_meta.json":
            continue
        target = d / item.name
        if target.exists():
            shutil.rmtree(target, ignore_errors=True) if target.is_dir() else target.unlink()
        shutil.move(str(item), str(target))
        moved.append(item.name)
    shutil.rmtree(stage, ignore_errors=True)
    print(f"已从 {src.name} 恢复到 {d}")
    for n in moved:
        print(f"  {n}")
    if saved:
        print(f"  恢复前的旧文件（含备份里没有的）整体转存到：{keep}")
        print(f"  共 {len(saved)} 个：{', '.join(saved)}")
    print(f"接着核对：& $PY scripts\\qbank.py stats --course {args.course}")
    return 0


def nonneg_int(text: str) -> int:
    n = int(text)
    if n < 0:
        raise argparse.ArgumentTypeError("要 0（全部）或正整数，负数会切掉题目")
    return n


def positive_int(text: str) -> int:
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("要 ≥1 的整数——0 或负数抽不到题")
    return n


def iso_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"要 YYYY-MM-DD 的真实日期，收到 {text!r}") from None


def cmd_errors(args) -> int:
    """从 作答.jsonl 生错题本 Markdown，直接喂 render_study_pdf.py --kind errors。"""
    require_course(args.course)
    items = {it["id"]: it for it in read_jsonl(bank_path(args.course))}
    all_attempts = read_jsonl(attempts_path(args.course))
    _since = getattr(args, "since", None)
    since_lo = _since.isoformat() if _since else None
    if not items:
        print(f"{args.course} 的题库是空的，没有错题可导。")
        return 0

    rows = []
    for qid, it in items.items():
        fails, rate5, recent, cleared, is_stub = count_failures(all_attempts, qid)
        if not recent or cleared:
            continue
        if since_lo and not any(str(x.get("ts", ""))[:10] >= since_lo
                                for x in all_attempts if x.get("qid") == qid):
            continue
        # 不再按「最后一次做对」跳过：顽固题的定义只有 count_failures 一处，
        # 「错三次后做对一次」还没解除（要最近连续 3 次全对），stats 里仍列着它，
        # 这里也必须在——否则同一门课两份名单对不上，按 stats 复刷会漏题
        last = recent[-1]
        rows.append({
            "item": it,
            "fails": fails,
            "last": last,
            "stubborn": is_stub,
        })
    if not rows:
        atts = all_attempts
        if not items:
            print(f"{args.course} 题库还是空的——先 qbank.py add 录题，或者 qbank.py pick 抽题。")
        elif not atts:
            print(f"{args.course} 还没有任何作答记录——先做题并 qbank.py grade 记一次，错题本才有内容。")
        elif atts and all(not a.get("counted", True) for a in atts):
            print(f"{args.course} 的 {len(atts)} 次作答全被排除（retry / self_reported / implicit / simulated），"
                  "没有一次计入掌握，所以错题本里没有待重做的题。")
        else:
            print(f"{args.course} 没有待重做的错题（错过的都做对了）。")
        return 0

    rows.sort(key=lambda r: (not r["stubborn"], -r["fails"], r["item"].get("topic") or ""))
    if args.limit:
        rows = rows[: args.limit]

    today = date.today().isoformat()
    stubborn_n = sum(1 for r in rows if r["stubborn"])
    out = [
        f"# {args.course} · 错题本",
        "",
        f"> 生成于 {today}；共 {len(rows)} 道待重做，★ 为顽固题。"
        "重做完用 qbank.py grade 记一次，做对后自动从这里消失。",
        "",
    ]
    for i, r in enumerate(rows, 1):
        it = r["item"]
        head = f"## 错题 {i}" + ("（★ 顽固）" if r["stubborn"] else "")
        out += [head, ""]
        if it.get("id"):
            out += [f"题号：`{it['id']}`", ""]
        out += [f"原题：{it['prompt']}"]
        if it.get("options"):
            out += ["", "、".join(f"{chr(65 + k)}. {o}" for k, o in enumerate(it["options"]))]
        last = r["last"]
        bits = [f"错 {r['fails']} 次"]
        if last.get("ts"):
            bits.append(f"最近 {str(last['ts'])[:10]}")
        if last.get("step_break") is not None:
            bits.append(f"断在第 {last['step_break']} 步")
        if last.get("confidence"):
            bits.append(f"信心 {last['confidence']}")
        if last.get("note"):
            bits.append(f"备注 {last['note']}")
        out += ["", "你的记录：" + " · ".join(bits), "", "### 再做一题", "", f"**{i}.** {it['prompt']}", ""]

    if args.with_answers:
        out += ["## 答案", ""]
        for i, r in enumerate(rows, 1):
            it = r["item"]
            out.append(f"{i}. {it.get('answer') or it.get('rubric') or '（题库里没写答案）'}")
        out.append("")

    path = Path(args.out) if args.out else course_dir(args.course) / "错题本.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not args.out and path.exists():
        import shutil as _shutil
        keep = course_dir(args.course) / "backup" / (
            "错题本-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".md")
        keep.parent.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(path, keep)
        print(f"旧错题本已另存：{keep}（你在里面补的笔记不会丢）")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"已生成错题本：{len(rows)} 道（顽固 {stubborn_n} 道）-> {path}")
    print("出 PDF 分两步（渲染脚本只出 tex，不是 pdf）：")
    print("  1) & $PY scripts\\render_study_pdf.py <这份 md> <同名.tex> --kind errors")
    print("  2) & $PY scripts\\compile_study_pdf.py <同名.tex> <同名.pdf>")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="本地题库 / 作答 / FSRS 式排期")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="建课程目录与三个数据文件")
    p.add_argument("--course", required=True)
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("exam", help="查看或设置考试日（排期不外推过考试）")
    p.add_argument("--course", required=True)
    p.add_argument("--date", type=iso_date, help="YYYY-MM-DD；不给则只打印当前值")
    p.set_defaults(fn=cmd_exam)

    p = sub.add_parser("add", help="加一道题")
    p.add_argument("--course", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--answer", default="")
    p.add_argument("--options", help="用 | 分隔的选项")
    p.add_argument("--chapter", default="")
    p.add_argument("--topic", default="")
    p.add_argument("--kind", default="quiz")
    p.add_argument("--rubric", default="")
    p.add_argument("--source", default="", help="出处：书名 + 页码")
    p.add_argument("--quote", default="", help="逐字引文；配 --verify 时会在原文里核对")
    p.add_argument("--verify", default="", help="原文文件（txt/md），用来核对 --quote 是否真实存在")
    p.add_argument("--id", default="")
    p.add_argument("--strict", action="store_true", help="收题检查有提示就拒绝写入")
    p.add_argument("--no-check", dest="no_check", action="store_true", help="跳过收题检查")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list", help="列题")
    p.add_argument("--course", required=True)
    p.add_argument("--chapter")
    p.add_argument("--topic")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("pick", help="抽题（到期优先）")
    p.add_argument("--course", required=True)
    p.add_argument("--n", type=positive_int, default=3)
    p.add_argument("--chapter")
    p.add_argument("--topic")
    p.add_argument("--date", type=iso_date)
    p.add_argument("--with-answer", action="store_true")
    p.set_defaults(fn=cmd_pick)

    p = sub.add_parser("grade", help="记一次作答并推进排期")
    p.add_argument("--course", required=True)
    p.add_argument("--qid", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--grade",
        choices=["again", "hard", "good", "easy"],
        help="again 忘了 / hard 提示后想起 / good 独立做对 / easy 秒答且讲得清",
    )
    g.add_argument("--correct", action="store_true", help="等价 --grade good")
    g.add_argument("--wrong", action="store_true", help="等价 --grade again")
    p.add_argument("--step", type=int, help="断在第几步")
    p.add_argument("--confidence", choices=["sure", "unsure"])
    p.add_argument("--note", default="")
    p.add_argument("--retry", action="store_true", help="重试或重做，不计入掌握")
    p.add_argument("--self-reported", dest="self_reported", action="store_true", help="学习者自报，未经核对")
    p.add_argument("--implicit", action="store_true", help="由前置题隐式推得，不算一次作答")
    p.add_argument("--simulated", action="store_true", help="演示 / 示例作答，只作演示")
    p.set_defaults(fn=cmd_grade)

    p = sub.add_parser("audit", help="按收题六问查一遍题库（题干自足 / 有答案 / 有出处 / 选项 / 重题）")
    p.add_argument("--course", required=True)
    p.add_argument("--chapter")
    p.add_argument("--topic")
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("due", help="列今天到期")
    p.add_argument("--course", required=True)
    p.add_argument("--date", type=iso_date)
    p.set_defaults(fn=cmd_due)

    p = sub.add_parser("stats", help="题量 / 正确率 / 最弱知识点 / 顽固题")
    p.add_argument("--course", required=True)
    p.add_argument("--since", type=iso_date, help="只统计该日期（含）之后的作答（顽固题仍按全历史判）")
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("export", help="导出 Markdown 题库")
    p.add_argument("--course", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("errors", help="从作答记录生错题本 Markdown（喂 render_study_pdf --kind errors）")
    p.add_argument("--course", required=True)
    p.add_argument("--since", type=iso_date, help="只导该日期（含）之后作答过的题")
    p.add_argument("--out", help="输出 .md 路径（默认 <课程目录>\\错题本.md）")
    p.add_argument("--limit", type=nonneg_int, default=0, help="最多几道，0 = 全部")
    p.add_argument("--with-answers", dest="with_answers", action="store_true", help="末尾附答案页")
    p.set_defaults(fn=cmd_errors)

    p = sub.add_parser("backup", help="把一门课打包成 zip（题库 / 作答 / 排期 / 进度 / 能力评价）")
    p.add_argument("--course", required=True)
    p.add_argument("--out", help="输出 .zip（默认 <课程>\\backup\\<课程>-时间.zip）")
    p.set_defaults(fn=cmd_backup)

    p = sub.add_parser("restore", help="从 zip 恢复（覆盖前把旧文件存进 backup\\pre-restore-时间\\）")
    p.add_argument("--course", required=True)
    p.add_argument("--src", required=True, help="备份 zip 路径")
    p.set_defaults(fn=cmd_restore)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
