"""Phase 5: 写 agent_output.json + 调 assemble_tomato_audio.py"""
import os
import json
import subprocess
import sys

VAULT = os.path.expanduser("~/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault")
ASSEMBLE = os.path.join(VAULT, "assemble_tomato_audio.py")
AGENT_OUTPUT = os.path.join(VAULT, "data/agent_output.json")
TOMATO_AUDIO = os.path.join(VAULT, "data/tomato_audio.json")

# 加载 Phase 3 产出
with open(os.path.join(VAULT, "data/_ta_phase3_songs.json"), encoding="utf-8") as f:
    songs_full = json.load(f)

# 加载 note id 映射（按 title）
NOTE_IDS = {
    "摇摆摇":   "mts5rrro50x8yifxv0q",
    "小甜心":   "mts5rrwn73mrj1e7zgb",
    "爱不动了": "mts5rrxjf12mw04h5e",
    "念长安":   "mts5rryo9rq30yt4o1u",
    "麦穗黄":   "mts5rrznq8wxbwcz07s",
}

# agent_output.json：只含 8 个核心创意字段
agent_songs = []
for s in songs_full:
    agent_songs.append({
        "title": s["title"],
        "genre_code": s["genre_code"],
        "lyrics": s["lyrics"],
        "mmx_prompt": s["mmx_prompt"],
        "suno_prompt": s["suno_prompt"],
        "cover_prompt": s["cover_prompt"],
        "bpm": s["bpm"],
        "chord": s["chord"],
    })

with open(AGENT_OUTPUT, "w", encoding="utf-8") as f:
    json.dump({"songs": agent_songs}, f, ensure_ascii=False, indent=2)
print(f"✅ agent_output.json 已写入（{len(agent_songs)} 首歌 × 8 字段）")

# 调 assemble 脚本
print("\n=== 调 assemble_tomato_audio.py ===")
result = subprocess.run(
    [sys.executable, ASSEMBLE, "--input", AGENT_OUTPUT],
    capture_output=True, text=True, timeout=30
)
print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

if result.returncode != 0:
    print(f"\n❌ 组装失败 exit={result.returncode}")
    sys.exit(1)
else:
    print(f"\n✅ 组装成功 exit=0")

# 验证 tomato_audio.json 已写入
if os.path.exists(TOMATO_AUDIO):
    with open(TOMATO_AUDIO, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n=== tomato_audio.json 验证 ===")
    print(f"  version: {data.get('version')}")
    print(f"  platform: {data.get('platform')}")
    print(f"  date: {data.get('date')}")
    print(f"  total_songs: {data.get('total_songs')}")
    print(f"  songs:")
    for s in data["songs"]:
        print(f"    • {s['title']} ({s['genre_code']}) {s['genre_icon']} {s['genre_label']}")
        print(f"      slug={s['slug']}, song_dir={s['song_dir']}, lyric_lines={s['lyric_lines']}")
    print(f"\n🎉 Phase 5 完成")
else:
    print(f"❌ tomato_audio.json 未生成")
    sys.exit(1)
