#!/usr/bin/env python3
"""
番茄音乐 — Make 触发脚本
=======================
用法:
  python3 trigger_make.py --title "歌名" --lyrics-file lyrics.txt --genre "民谣" --prompt "民谣风格 BPM 80"
  python3 trigger_make.py --title "歌名" --lyrics "歌词内容" --genre "流行" --prompt "流行"
  python3 trigger_make.py --batch songs.json   # 批量，JSON 数组

通过 Make Webhook 触发 → Mac mini 本地调 MiniMax + BizyAir 生成 MP3 + 封面。
"""

import argparse
import json
import sys
import requests

# Make Webhook URL
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/9udt2idy1j5txhspfw660w91lt54gnlg"
PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


def trigger_single(title, lyrics, prompt, genre="流行", mood="梦幻", date=None):
    payload = {
        "title": title,
        "lyrics": lyrics,
        "prompt": prompt,
        "genre": genre,
        "mood": mood,
    }
    if date:
        payload["date"] = date

    r = requests.post(MAKE_WEBHOOK_URL, json=payload, proxies=PROXY, timeout=30)
    print(f"✅ 已触发 Make: {title}")
    print(f"   Make 回复: {r.text}")
    print(f"   ⏳ MP3 + 封面正在后台生成中（约 2-5 分钟）")
    print(f"   📁 输出: /tmp/tomato_music/  → 同步到 ~/Music/番茄音乐/")


def trigger_batch(songs_file):
    with open(songs_file, "r", encoding="utf-8") as f:
        songs = json.load(f)
    payload = {"songs": songs}
    r = requests.post(MAKE_WEBHOOK_URL, json=payload, proxies=PROXY, timeout=30)
    print(f"✅ 已批量触发 {len(songs)} 首歌")
    print(f"   Make 回复: {r.text}")


def main():
    p = argparse.ArgumentParser(description="番茄音乐 Make 触发器")
    p.add_argument("--title", help="歌名")
    p.add_argument("--lyrics", help="歌词文本")
    p.add_argument("--lyrics-file", help="歌词文件路径")
    p.add_argument("--prompt", default="流行风格", help="MiniMax prompt（风格描述）")
    p.add_argument("--genre", default="流行", help="音乐类型")
    p.add_argument("--mood", default="梦幻", help="情绪氛围（影响封面）")
    p.add_argument("--date", help="日期 YYYY-MM-DD")
    p.add_argument("--batch", help="批量 JSON 文件路径")
    args = p.parse_args()

    if args.batch:
        trigger_batch(args.batch)
        return

    if not args.title:
        print("❌ 需要 --title")
        sys.exit(1)

    lyrics = args.lyrics or ""
    if args.lyrics_file:
        with open(args.lyrics_file, "r", encoding="utf-8") as f:
            lyrics = f.read()

    trigger_single(args.title, lyrics, args.prompt, args.genre, args.mood, args.date)


if __name__ == "__main__":
    main()
