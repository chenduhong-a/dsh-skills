#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""asr.py — 视频音频转录（faster-whisper，支持 CPU/GPU）。

用法:
    python asr.py --video results/live.mp4 --out results/transcript.jsonl \
        --model small --lang zh --device auto

输出 JSONL 每行（句级）:
    {"start": 12.3, "end": 15.1, "text": "...", "words": [[w, ws, we], ...]}

设备选择:
    - auto: 自动检测 (cuda > mps > cpu)
    - cuda: NVIDIA GPU
    - mps: Apple Silicon GPU
    - cpu: CPU
"""
import argparse
import glob
import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

# 把 pip 安装的 NVIDIA DLL 目录前置到 PATH（Windows 上 ctranslate2 按 PATH 找 cublas/cudnn）
for _base in site.getsitepackages():
    for _d in glob.glob(os.path.join(_base, "nvidia", "*", "bin")):
        os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")


def extract_audio(video: Path, wav: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[asr] ffmpeg 未找到", file=sys.stderr)
        return False
    cmd = [ffmpeg, "-y", "-i", str(video), "-vn",
           "-ac", "1", "-ar", "16000", "-f", "wav", str(wav)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not wav.exists():
        print(f"[asr] 音频提取失败: {r.stderr.decode()[-300:]}", file=sys.stderr)
        return False
    return True


def get_auto_device():
    """自动检测最佳可用设备：优先 ctranslate2 的 CUDA 支持，其次 torch，最后 CPU。"""
    try:
        import ctranslate2
        if ctranslate2.get_supported_compute_types("cuda"):
            return "cuda"
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def decode_audio(path: Path, sr: int = 16000):
    """自己解码成 16k 单声道 float32，直接喂 numpy 数组。

    faster-whisper 1.2.x 在 transcribe(文件路径) 时会调 av.open(metadata_errors=...)，
    与 av 19 不兼容（TypeError: open() got an unexpected keyword argument 'metadata_errors'，
    2026-11-24 在 bili-vision-venv 实测）。改成先解码再传数组，就绕开这条路径。
    """
    import av
    import numpy as np

    chunks = []
    with av.open(str(path)) as c:
        stream = c.streams.audio[0]
        res = av.AudioResampler(format="flt", layout="mono", rate=sr)
        for frame in c.decode(stream):
            for f in res.resample(frame):
                chunks.append(f.to_ndarray().reshape(-1))
        for f in res.resample(None):
            chunks.append(f.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype="float32")
    return np.concatenate(chunks).astype("float32")


def transcribe(wav: Path, model_size: str, lang: str, device: str = "cpu"):
    """返回 segments 列表；模型下载失败抛异常由调用方处理。"""
    from faster_whisper import WhisperModel
    compute_type = "float16" if device != "cpu" else "int8"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    audio = decode_audio(wav)
    segs, _info = model.transcribe(audio, language=lang,
                                   word_timestamps=True, vad_filter=False)
    out = []
    for s in segs:
        words = [[w.word, round(w.start, 2), round(w.end, 2)]
                 for w in (s.words or [])]
        out.append({"start": round(s.start, 2), "end": round(s.end, 2),
                    "text": s.text.strip(), "words": words})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", default="results/transcript.jsonl")
    ap.add_argument("--model", default="small", help="tiny/base/small/medium")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--device", default="auto",
                    help="auto/cpu/cuda/mps (auto=自动检测)")
    args = ap.parse_args()

    # 解析设备
    device = args.device
    if device == "auto":
        device = get_auto_device()
        print(f"[asr] Auto-selected device: {device}")

    video = Path(args.video)
    if not video.exists():
        print(f"[asr] 视频不存在: {video}", file=sys.stderr)
        sys.exit(2)
    wav = video.with_suffix(".16k.wav")
    if not extract_audio(video, wav):
        sys.exit(2)
    try:
        segs = transcribe(wav, args.model, args.lang, device=device)
    except Exception as e:
        msg = str(e)
        # bili-vision-venv 里没有 NVIDIA 的 cublas/cudnn（原来那套 2 GB 的 nvidia 包在
        # dsh-video-understand 的 venv 里，2026-11-24 随插件卸载）。ctranslate2 仍会
        # 报告 cuda 可用，于是自动选 cuda 后在这里炸——回退 CPU 即可，base 模型约 14× 实时。
        if device != "cpu" and ("cublas64" in msg or "cudnn" in msg.lower()):
            print(f"[asr] GPU 库缺失（{msg}），回退 CPU", file=sys.stderr)
            device = "cpu"
            segs = transcribe(wav, args.model, args.lang, device="cpu")
        else:
            print(f"[asr] 转录失败（可能是模型下载受限）: {e}", file=sys.stderr)
            sys.exit(2)
    with open(args.out, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"[asr] done: {len(segs)} segments -> {args.out}")


if __name__ == "__main__":
    main()
