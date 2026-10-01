#!/usr/bin/env python3
"""番茄专项 T-A' 音频生成 - 并行3 worker"""
import subprocess, os, json, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

VAULT = "/Users/wanglingwei/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault"
AUDIO_FILE = os.path.join(VAULT, "data/tomato_audio.json")
MMX = "/Users/wanglingwei/Library/Application Support/remio/Users/SharedData/runtime/npm-global/bin/mmx"
MMX_ENV = os.environ.copy()
MMX_ENV["PATH"] = "/Users/wanglingwei/.nvm/versions/node/v22.18.0/bin:" + MMX_ENV["PATH"]

DURATION_THRESHOLD = {"dance": 150, "viral_pop": 150, "hometown": 150, "sad": 170, "guofeng": 170}

with open(AUDIO_FILE) as f:
    data = json.load(f)

print(f"[{datetime.now().strftime('%H:%M:%S')}] 读取 {len(data['songs'])} 首歌")

# ---- 准备阶段 ----
tasks = []
for song in data["songs"]:
    song_dir = song["song_dir"]
    os.makedirs(song_dir, exist_ok=True)
    lyrics_path = os.path.join(song_dir, "lyrics.txt")
    with open(lyrics_path, "w") as f:
        f.write(song["lyrics"])
    out_path = os.path.join(song_dir, f"{song['title']}_v1.mp3")
    if os.path.exists(out_path):
        size_mb = round(os.path.getsize(out_path) / 1024 / 1024, 1)
        print(f"⏭️ {song['title']} 已存在 ({size_mb}MB)，跳过")
        continue
    tasks.append(song)
    print(f"📋 待生成: {song['title']} ({song['genre_code']}) → {song_dir}")

def check_duration(path, title, genre_code, attempt=1):
    if not os.path.exists(path):
        print(f"❌ {title}: 文件不存在")
        return False
    try:
        af = subprocess.run(['afinfo', path], capture_output=True, text=True, timeout=5)
        for line in af.stdout.split('\n'):
            if 'estimated duration' in line:
                parts = line.split(':')
                secs = round(float(parts[-1].strip().replace('sec', '').strip()))
                threshold = DURATION_THRESHOLD.get(genre_code, 170)
                ok = secs >= threshold
                icon = "✅" if ok else "⚠️"
                print(f"{icon} {title} → {secs//60}:{secs%60:02d} (阈值 {threshold}s, 尝试 {attempt}/2)")
                return ok
    except Exception as e:
        print(f"❌ {title}: afinfo失败 {e}")
    return False

def generate_one_song(song):
    song_dir = song["song_dir"]
    lyrics_path = os.path.join(song_dir, "lyrics.txt")
    out_path = os.path.join(song_dir, f"{song['title']}_v1.mp3")
    title = song['title']
    genre_code = song['genre_code']
    prompt = song['mmx_prompt']

    # 第 1 次生成
    print(f"🎵 [{datetime.now().strftime('%H:%M:%S')}] {title} 开始生成 (第1次)...")
    try:
        result = subprocess.run([
            MMX, "music", "generate",
            "--prompt", prompt,
            "--lyrics-file", lyrics_path,
            "--model", "music-3.0",
            "--out", out_path
        ], capture_output=True, text=True, timeout=600, env=MMX_ENV)
    except subprocess.TimeoutExpired:
        print(f"⏰ {title} 第1次超时(>600s)")
        result = None

    if result is None or result.returncode != 0:
        err = result.stderr[:200] if result else "timeout"
        print(f"⚠️ {title} mmx 第1次失败: {err}")
        print(f"   等 30s 后重试...")
        time.sleep(30)
        try:
            result2 = subprocess.run([
                MMX, "music", "generate",
                "--prompt", prompt,
                "--lyrics-file", lyrics_path,
                "--model", "music-3.0",
                "--out", out_path
            ], capture_output=True, text=True, timeout=600, env=MMX_ENV)
        except subprocess.TimeoutExpired:
            print(f"⏰ {title} 重试超时")
            return (title, False, "重试超时")
        if result2.returncode != 0:
            print(f"❌ {title} mmx 重试后仍失败: {result2.stderr[:200]}")
            return (title, False, f"mmx失败: {result2.stderr[:100]}")
        else:
            print(f"✅ {title} mmx 重试成功")
            result = result2

    ok = check_duration(out_path, title, genre_code, attempt=1)
    if not ok:
        # 重试时长
        try:
            os.remove(out_path)
        except: pass
        try:
            result2 = subprocess.run([
                MMX, "music", "generate",
                "--prompt", prompt,
                "--lyrics-file", lyrics_path,
                "--model", "music-3.0",
                "--out", out_path
            ], capture_output=True, text=True, timeout=600, env=MMX_ENV)
        except subprocess.TimeoutExpired:
            return (title, os.path.exists(out_path), "重试超时")
        ok = check_duration(out_path, title, genre_code, attempt=2)
        if not ok:
            print(f"   ⚠️ {title} 重试后仍偏短，接受当前版本")

    return (title, os.path.exists(out_path), "ok")

# ---- 并行生成 ----
print(f"\n🎵 并行生成 {len(tasks)} 首音频 (max_workers=3)...")
results = []
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(generate_one_song, song): song for song in tasks}
    for future in as_completed(futures):
        try:
            title, success, msg = future.result()
            results.append((title, success, msg))
            status = "✅" if success else "❌"
            print(f"{status} {title} 完成 ({msg})")
        except Exception as e:
            print(f"❌ Future exception: {e}")

# 汇总
success_count = sum(1 for _, s, _ in results if s)
print(f"\n📊 汇总: {success_count}/{len(results)} 首成功")
for title, success, msg in results:
    print(f"  {'✅' if success else '❌'} {title}: {msg}")
