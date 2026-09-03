#!/usr/bin/env python3
"""
歌词强制对齐 v6.0 — 本地 wav2vec2 CTC Forced Alignment

替换 v5.0 的远程 ForcedAligner (Qwen3-ForcedAligner-0.6B @ M2 Mac mini)。
新引擎: jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn + CTC 动态规划对齐。

原理:
  ForcedAligner / ASR 方案对歌声(带BGM)效果极差(时间戳倒流/归零/堆叠)。
  CTC forced alignment 不依赖"听出歌词"，而是用已知歌词文本做动态规划，
  在 CTC logits 上找到每个字在音频时间轴上的最佳对齐位置。
  数学上保证时间戳严格单调递增。

性能: ~15s/首 (Apple Silicon CPU), 无网络依赖, MIT 许可可商用。

Usage:
    python lrc_align.py              # 增量
    python lrc_align.py --force      # 全部重跑
    python lrc_align.py --auto-deploy  # 完成后自动 git add+commit+push（T-B 后台模式用）
    python lrc_align.py --songs 发芽 你是一条河
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import librosa
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


# ─── Config ───────────────────────────────────────────────────────────────────

MUSIC_DIR = Path("~/Music/番茄音乐").expanduser()
DATA_DIR = Path(__file__).parent / "data"
LRC_JSON = DATA_DIR / "lrc_data.json"
SONGS_JSON = DATA_DIR / "songs.json"

MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
SAMPLE_RATE = 16000
CHUNK_SIZE = SAMPLE_RATE * 30  # 30s chunks
FRAME_DURATION = 0.02  # 20ms per CTC frame
BLANK_ID = 0

# 模型单例（避免重复加载）
_MODEL = None
_PROCESSOR = None


def get_model():
    global _MODEL, _PROCESSOR
    if _MODEL is None:
        print("  📦 加载 wav2vec2 模型...", flush=True)
        t0 = time.time()
        _PROCESSOR = Wav2Vec2Processor.from_pretrained(MODEL_ID)
        _MODEL = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
        _MODEL.eval()
        print(f"     加载完成: {time.time()-t0:.1f}s", flush=True)
    return _PROCESSOR, _MODEL


# ─── CTC Forced Alignment ────────────────────────────────────────────────────

def ctc_align(log_probs: np.ndarray, token_ids: list, blank_id: int = BLANK_ID) -> np.ndarray:
    """
    CTC forced alignment via dynamic programming (numpy vectorized).

    log_probs: (T, V) CTC log probabilities per time step
    token_ids: target token id sequence (with blanks inserted between chars)
    blank_id:  CTC blank token id

    Returns: (T,) aligned token id per frame
    """
    T, V = log_probs.shape
    N = len(token_ids)

    if N == 0 or T == 0:
        return np.full(T, blank_id, dtype=np.int32)

    NEG_INF = -1e10
    dp = np.full((T, N), NEG_INF, dtype=np.float64)
    backptr = np.zeros((T, N), dtype=np.int32)

    token_arr = np.array(token_ids, dtype=np.int32)
    is_blank = (token_arr == blank_id)
    # can_skip[n] = True 表示可以从 dp[t-1][n-2] 跳到 dp[t][n]
    can_skip = np.zeros(N, dtype=bool)
    can_skip[2:] = (~is_blank[2:]) & (~is_blank[1:-1])

    # 初始化
    dp[0, 0] = log_probs[0, blank_id]
    if N > 1:
        dp[0, 1] = log_probs[0, token_ids[1]]

    # 前向 DP（numpy 向量化内循环）
    arange_n = np.arange(N)
    for t in range(1, T):
        prev = dp[t - 1]  # (N,)

        # 三个候选来源
        c_same = prev  # dp[t-1, n]
        c_prev1 = np.full(N, NEG_INF, dtype=np.float64)
        c_prev1[1:] = prev[:-1]  # dp[t-1, n-1]
        c_prev2 = np.full(N, NEG_INF, dtype=np.float64)
        c_prev2[2:] = prev[:-2]  # dp[t-1, n-2]
        c_prev2[~can_skip] = NEG_INF

        # 取最大值
        stacked = np.stack([c_same, c_prev1, c_prev2], axis=0)  # (3, N)
        best_vals = np.max(stacked, axis=0)  # (N,)
        best_idx = np.argmax(stacked, axis=0)  # (N,) 0=same, 1=prev1, 2=prev2

        backptr[t] = arange_n - best_idx
        dp[t] = best_vals + log_probs[t, token_arr]

    # 回溯
    alignment = np.full(T, blank_id, dtype=np.int32)
    n = N - 1
    alignment[T - 1] = token_ids[n]
    for t in range(T - 1, 0, -1):
        n = backptr[t, n]
        alignment[t - 1] = token_ids[n]

    return alignment


def align_song(mp3_path: str, lyrics_lines: list, label: str = "") -> list:
    """
    对齐一首歌，返回 LRC 条目列表。
    [{'time': float, 'text': str}, ...]
    """
    processor, model = get_model()

    # 1. 加载音频
    audio, sr = librosa.load(mp3_path, sr=SAMPLE_RATE, mono=True)

    # 2. 分块推理 → CTC logits
    all_logits = []
    with torch.no_grad():
        for i in range(0, len(audio), CHUNK_SIZE):
            chunk = audio[i:i + CHUNK_SIZE]
            if len(chunk) < 4000:
                continue
            input_values = processor(chunk, sampling_rate=SAMPLE_RATE, return_tensors="pt").input_values
            logits = model(input_values).logits[0].numpy()
            all_logits.append(logits)

    if not all_logits:
        return []

    full_logits = np.vstack(all_logits)

    # 3. log softmax
    log_probs = torch.nn.functional.log_softmax(
        torch.tensor(full_logits, dtype=torch.float32), dim=-1
    ).numpy().astype(np.float64)

    # 4. 歌词文本 → token 序列（每字一 token + blank 间隔）
    all_chars = "".join(lyrics_lines)
    char_tokens = []
    for ch in all_chars:
        ids = processor.tokenizer(ch, add_special_tokens=False).input_ids
        if ids:
            char_tokens.extend(ids)
            char_tokens.append(BLANK_ID)

    if not char_tokens:
        return []

    # 5. CTC 对齐
    alignment = ctc_align(log_probs, char_ids := char_tokens, blank_id=BLANK_ID)

    # 6. 提取非 blank 段的起始时间 → 每个 token 的时间戳
    non_blank_starts = []
    current = None
    start_frame = None
    for t, tid in enumerate(alignment):
        if tid != current:
            if current is not None and current != BLANK_ID:
                non_blank_starts.append(start_frame * FRAME_DURATION)
            current = tid
            start_frame = t
    if current is not None and current != BLANK_ID:
        non_blank_starts.append(start_frame * FRAME_DURATION)

    # 7. 聚合到歌词行
    entries = []
    char_idx = 0
    for line in lyrics_lines:
        line_len = len(line.strip())
        if line_len == 0:
            continue
        if char_idx < len(non_blank_starts):
            t = non_blank_starts[char_idx]
            entries.append({"time": round(t, 2), "text": line.strip()})
        else:
            # 超出对齐范围，用最后一个时间戳
            last_t = non_blank_starts[-1] if non_blank_starts else 0.0
            entries.append({"time": round(last_t, 2), "text": line.strip()})
        char_idx += line_len

    return entries


# ─── Helpers (保留 v5.0 逻辑) ─────────────────────────────────────────────────

def find_lyrics_file(song_dir: str) -> str:
    d = Path(song_dir)
    for f in sorted(d.iterdir()):
        if 'lyrics_clean' in f.name.lower() and f.suffix == '.txt':
            return str(f)
    for f in sorted(d.iterdir()):
        if 'lyrics' in f.name.lower() and f.suffix == '.txt':
            return str(f)
    for f in sorted(d.iterdir()):
        if f.suffix == '.txt' and not f.name.startswith('.'):
            return str(f)
    return ""


def load_lyrics(path: str) -> list:
    for enc in ['utf-8', 'utf-8-sig', 'gbk']:
        try:
            with open(path, 'r', encoding=enc) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        return []
    # 过滤已有的 LRC 标签行和时间戳
    lines = []
    for l in text.split('\n'):
        l = l.strip()
        if not l:
            continue
        # 跳过 [Verse], [Chorus] 等结构标签
        if re.match(r'^\[(Intro|Verse|Pre-Chorus|Chorus|Bridge|Outro|Hook)', l, re.IGNORECASE):
            continue
        lines.append(l)
    return lines


def find_best_mp3(song_dir: Path) -> str:
    mp3s = sorted(song_dir.glob('*.mp3'))
    if not mp3s:
        return ""
    best = mp3s[0]
    best_ver = 0
    for mp3 in mp3s:
        m = re.search(r'_v(\d+)', mp3.name)
        ver = int(m.group(1)) if m else 0
        if ver > best_ver:
            best_ver = ver
            best = mp3
    return str(best)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    force = '--force' in sys.argv
    auto_deploy = '--auto-deploy' in sys.argv
    specified = []
    if '--songs' in sys.argv:
        idx = sys.argv.index('--songs')
        specified = sys.argv[idx + 1:]

    with open(SONGS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_lrc = {}
    if LRC_JSON.exists() and not force:
        with open(LRC_JSON, 'r', encoding='utf-8') as f:
            existing_lrc = json.load(f)

    targets = []
    for song in data['songs']:
        title = song.get('title', '')
        if song.get('exclude'):
            continue
        if specified and title not in specified:
            continue

        song_dir = Path(song.get('dir', MUSIC_DIR / title))
        if not song_dir.is_dir():
            continue

        mp3 = find_best_mp3(song_dir)
        if not mp3:
            continue

        lyrics_path = find_lyrics_file(str(song_dir))
        if not lyrics_path:
            continue

        m = re.search(r'_v(\d+)', Path(mp3).name)
        version_tag = f"v{m.group(1)}" if m else "v1"
        lrc_key = f"{title}__{version_tag}"

        if not force and lrc_key in existing_lrc and existing_lrc[lrc_key]:
            continue

        targets.append({
            'title': title, 'dir': song_dir, 'mp3': mp3,
            'lyrics': lyrics_path, 'lrc_key': lrc_key, 'version_tag': version_tag,
        })

    print(f"📊 需要对齐: {len(targets)} 首歌")
    print(f"   引擎: wav2vec2 CTC Forced Alignment (本地)")

    if not targets:
        print("   ✅ 全部已有 LRC，无需对齐")
        return

    stats = {'ok': 0, 'fail': 0, 'total_time': 0}

    for i, t in enumerate(targets):
        print(f"\n[{i+1}/{len(targets)}] 🎵 {t['title']}")

        lyrics_lines = load_lyrics(t['lyrics'])
        if not lyrics_lines:
            print(f"   ❌ 无歌词")
            stats['fail'] += 1
            continue

        print(f"   🔧 CTC 对齐中 ({len(lyrics_lines)} 行歌词)...")
        t0 = time.time()
        try:
            lrc_entries = align_song(t['mp3'], lyrics_lines, t['title'])
            elapsed = time.time() - t0

            if lrc_entries:
                existing_lrc[t['lrc_key']] = lrc_entries
                # 质量检查
                times = [e['time'] for e in lrc_entries]
                monotonic = all(times[j] >= times[j-1] for j in range(1, len(times)))
                print(f"   ✅ {len(lrc_entries)} 行 ({elapsed:.1f}s) 单调={'✓' if monotonic else '✗'}")
                stats['ok'] += 1
                stats['total_time'] += elapsed
            else:
                print(f"   ❌ 对齐失败（空结果）")
                stats['fail'] += 1

        except Exception as e:
            elapsed = time.time() - t0
            print(f"   ❌ 异常: {e}")
            stats['fail'] += 1

        # 每 20 首保存一次（防止中途崩溃）
        if (i + 1) % 20 == 0:
            with open('/tmp/lrc_data_new_tomato.json', 'w', encoding='utf-8') as f:
                json.dump(existing_lrc, f, ensure_ascii=False, indent=2)
            print(f"   💾 已保存进度 ({i+1}/{len(targets)})")

    # 保存 LRC 索引
    with open(LRC_JSON, 'w', encoding='utf-8') as f:
        json.dump(existing_lrc, f, ensure_ascii=False, indent=2)
    print(f"\n💾 LRC 数据已写回 {LRC_JSON}")
    # 同步备份一份到 /tmp 供调试
    tmp_lrc = '/tmp/lrc_data_new_tomato.json'
    with open(tmp_lrc, 'w', encoding='utf-8') as f:
        json.dump(existing_lrc, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"📊 结果: ✅ {stats['ok']}  ❌ {stats['fail']}")
    print(f"   引擎: wav2vec2 CTC (本地)")
    if stats['ok'] > 0:
        avg = stats['total_time'] / stats['ok']
        print(f"   平均: {avg:.1f}s/首")
    print(f"   LRC 索引: {LRC_JSON} ({len(existing_lrc)} 个版本)")

    if stats['ok'] > 0:
        print(f"\n🔨 重建网站...")
        vault_py = Path(__file__).parent / "vault.py"
        result = subprocess.run(
            [sys.executable, str(vault_py), "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(Path(__file__).parent)
        )
        if result.returncode == 0:
            print(f"   ✅ 网站已重建")
        else:
            print(f"   ❌ 重建失败: {result.stderr[:300]}")

    if auto_deploy:
        print(f"\n🚀 自动部署 (git push)...")
        repo = Path(__file__).parent
        def _git(*args):
            return subprocess.run(['git', '-C', str(repo)] + list(args),
                                  capture_output=True, text=True, timeout=60)
        _git('add', 'index.html', 'data/songs.json', 'data/lrc_data.json')
        r_cmt = _git('commit', '-m', f'chore: LRC auto-deploy {time.strftime("%Y-%m-%d %H:%M")}')
        if 'nothing to commit' in (r_cmt.stdout or ''):
            print(f"   ℹ️ 无变更，跳过 push")
        elif r_cmt.returncode == 0:
            r_push = _git('push', 'origin', 'main')
            print(f"   ✅ push {'成功' if r_push.returncode == 0 else '失败: ' + (r_push.stderr or '')[:200]}")
        else:
            print(f"   ⚠️ commit 失败: {(r_cmt.stderr or '')[:200]}")


if __name__ == '__main__':
    main()
