#!/usr/bin/env python3
"""
assemble_tomato_audio.py — 番茄音乐 T-A 产出组装脚本

agent 只产出创意数据（5 首 × 8 个核心字段），本脚本自动填充所有 boilerplate 字段，
校验必填字段非空，写入 tomato_audio.json。

用法：
    python3 assemble_tomato_audio.py --input agent_output.json
    python3 assemble_tomato_audio.py  # 无参数 = 扫描最新 agent_output 文件

agent_output.json 格式（只有创意字段，无 boilerplate）：
{
  "songs": [
    {
      "title": "歌名",
      "genre_code": "dance",
      "lyrics": "[歌词]",
      "mmx_prompt": "...",
      "suno_prompt": "...",
      "cover_prompt": "...",
      "bpm": 128,
      "chord": "6415"
    },
    ...
  ]
}
"""

import json
import os
import sys
import glob
import argparse
from datetime import datetime, timezone, timedelta

# === 路径 ===
AGENT_ROOT = os.path.expanduser(
    "~/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent"
)
VAULT_DIR = os.path.join(AGENT_ROOT, "tomato-vault")
DATA_DIR = os.path.join(VAULT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "tomato_audio.json")

# === 曲风元数据映射表 ===
GENRE_MAP = {
    "dance": {
        "genre_label": "广场舞/DJ舞曲/车载慢摇",
        "genre_icon": "💃",
        "genre_color": "#e74c3c",
        "duration_threshold": 150,
    },
    "viral_pop": {
        "genre_label": "抖音热歌/口水歌/欢快洗脑",
        "genre_icon": "🎵",
        "genre_color": "#c41e1e",
        "duration_threshold": 150,
    },
    "sad": {
        "genre_label": "失恋/孤独/情感共鸣",
        "genre_icon": "🌧️",
        "genre_color": "#2c3e50",
        "duration_threshold": 170,
    },
    "guofeng": {
        "genre_label": "民族风/古诗词改编/中国风",
        "genre_icon": "🏯",
        "genre_color": "#7f4f24",
        "duration_threshold": 170,
    },
    "hometown": {
        "genre_label": "乡愁/励志/朴实口语",
        "genre_icon": "🏠",
        "genre_color": "#27ae60",
        "duration_threshold": 150,
    },
}

# === 每首歌的必填字段 ===
REQUIRED_FIELDS = ["title", "genre_code", "lyrics", "mmx_prompt", "suno_prompt", "cover_prompt", "bpm", "chord"]

MUSIC_DIR = os.path.expanduser("~/Music/番茄音乐")

CST = timezone(timedelta(hours=8))


def get_today():
    return datetime.now(CST).strftime("%Y-%m-%d")


def find_latest_agent_output():
    """扫描 data/ 目录中 agent_output_*.json 最新文件"""
    pattern = os.path.join(DATA_DIR, "agent_output_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def validate_input(agent_data):
    """校验 agent 输入数据完整"""
    errors = []
    
    if "songs" not in agent_data:
        errors.append("缺少 songs 数组")
        return errors
    
    songs = agent_data["songs"]
    if len(songs) != 5:
        errors.append(f"songs 数组长度={len(songs)}，必须为 5")
    
    for i, song in enumerate(songs):
        prefix = f"第{i+1}首"
        if "title" in song and song["title"]:
            prefix = song["title"]
        
        for field in REQUIRED_FIELDS:
            val = song.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"{prefix}: {field} 为空")
        
        gc = song.get("genre_code")
        if gc and gc not in GENRE_MAP:
            errors.append(f"{prefix}: 未知 genre_code={gc}")
    
    return errors


def assemble(agent_data):
    """把 agent 创意数据组装为完整的 tomato_audio.json"""
    today = get_today()
    songs = agent_data["songs"]
    
    assembled_songs = []
    for song in songs:
        gc = song["genre_code"]
        meta = GENRE_MAP[gc]
        title = song["title"]
        slug = f"{title}_{today}"
        song_dir = os.path.join(MUSIC_DIR, f"{today}_{title}")
        
        assembled = {
            # ── agent 产出（透传）──
            "title": title,
            "genre_code": gc,
            "lyrics": song["lyrics"],
            "mmx_prompt": song["mmx_prompt"],
            "suno_prompt": song["suno_prompt"],
            "cover_prompt": song["cover_prompt"],
            "bpm": song["bpm"],
            "chord": song["chord"],
            # ── 自动填充（boilerplate）──
            "slug": slug,
            "genre_label": meta["genre_label"],
            "genre_icon": meta["genre_icon"],
            "genre_color": meta["genre_color"],
            "song_dir": song_dir,
            "date": today,
            "duration": 0,
            "note_id": song.get("note_id", ""),
            # ── 初始化占位（T-A' 填充）──
            "lyric_lines": len([l for l in song["lyrics"].splitlines() if l.strip()]),
            "model": song.get("model", "manual"),
            "qa": song.get("qa", {"d1_cliche": 0, "d2_vividness": 0, "d3_hook": 0, "d4_rhyme": 0}),
            "versions": [],
            "cover": {"path": "", "all_covers": []},
            "poster": "",
            "lyrics_file": "",
            "has_lrc": False,
            "has_poster": False,
        }
        assembled_songs.append(assembled)
    
    return {
        "version": "1.0",
        "platform": "番茄音乐",
        "date": today,
        "total_songs": 5,
        "songs": assembled_songs,
    }


def main():
    parser = argparse.ArgumentParser(description="番茄音乐 T-A 产出组装脚本")
    parser.add_argument("--input", help="agent 输出 JSON 路径（默认扫描最新）")
    parser.add_argument("--dry-run", action="store_true", help="只校验不写入")
    args = parser.parse_args()
    
    input_path = args.input
    if not input_path:
        input_path = find_latest_agent_output()
        if not input_path:
            print("❌ 未找到 agent_output_*.json 文件，请用 --input 指定")
            sys.exit(1)
        print(f"📂 自动选择: {os.path.basename(input_path)}")
    
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)
    
    with open(input_path, encoding="utf-8") as f:
        agent_data = json.load(f)
    
    print(f"\n🔍 校验 agent 输入...")
    errors = validate_input(agent_data)
    if errors:
        print(f"❌ 校验失败 ({len(errors)} 个问题):")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)
    print(f"   ✅ 输入校验通过: 5 首歌，所有必填字段非空")
    
    result = assemble(agent_data)
    
    if args.dry_run:
        print(f"\n🏃 dry-run 模式，不写入文件")
        print(f"   产出: {result['date']}，{result['total_songs']} 首歌")
        for s in result["songs"]:
            print(f"   • {s['title']} ({s['genre_code']}) → {s['song_dir']}")
        sys.exit(0)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 组装完成 → {OUTPUT_FILE}")
    print(f"   日期: {result['date']}")
    print(f"   歌曲: {result['total_songs']} 首")
    for s in result["songs"]:
        print(f"   • {s['title']} ({s['genre_code']}) — {s['genre_label']}")


if __name__ == "__main__":
    main()
