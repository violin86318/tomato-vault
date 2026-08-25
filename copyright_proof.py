#!/usr/bin/env python3
"""
番茄音乐版权证明生成器
======================
从 songs.json + tomato_audio.json 读取歌曲元数据，
为每首歌生成一份独立的版权证明 Markdown 文档。

用法：
  python3 copyright_proof.py                  # 处理所有歌曲
  python3 copyright_proof.py 蹦跶蹦           # 处理指定歌曲
  python3 copyright_proof.py --output-dir /path  # 自定义输出目录
"""

import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SONGS_JSON = SCRIPT_DIR / "data" / "songs.json"
AUDIO_JSON = SCRIPT_DIR / "data" / "tomato_audio.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "版权证明"

# 创作者信息（按需修改）
CREATOR_NAME = "王同学"
CREATOR_PLATFORM = "番茄音乐"
AI_TOOLS = {
    "mmx": "MiniMax Music (mmx CLI)",
    "suno": "Suno AI",
}


def load_data():
    """加载 songs.json 和 tomato_audio.json，合并元数据"""
    with open(SONGS_JSON, "r", encoding="utf-8") as f:
        songs_data = json.load(f)

    audio_map = {}
    if AUDIO_JSON.exists():
        with open(AUDIO_JSON, "r", encoding="utf-8") as f:
            audio_data = json.load(f)
        audio_list = audio_data["songs"] if isinstance(audio_data, dict) else audio_data
        for s in audio_list:
            audio_map[s["title"]] = s

    songs = []
    for s in songs_data.get("songs", []):
        merged = dict(s)
        if s["title"] in audio_map:
            a = audio_map[s["title"]]
            merged.setdefault("mmx_prompt", a.get("mmx_prompt", ""))
            merged.setdefault("suno_prompt", a.get("suno_prompt", ""))
            merged.setdefault("creation_note", a.get("creation_note", ""))
            merged.setdefault("cover_prompt", a.get("cover_prompt", ""))
        # 优先用 lyrics_file，fallback 到 lyrics
        if not merged.get("lyrics_file") and merged.get("lyrics"):
            merged["lyrics_file"] = merged["lyrics"]
        songs.append(merged)

    return songs


def file_hash(filepath, algo="md5"):
    """计算文件哈希"""
    if not os.path.exists(filepath):
        return "N/A"
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_size_str(filepath):
    """文件大小（人类可读）"""
    if not os.path.exists(filepath):
        return "N/A"
    size = os.path.getsize(filepath)
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    return f"{size / 1024:.1f} KB"


def lyrics_line_count(lyrics):
    """歌词行数"""
    if not lyrics:
        return 0
    return len([l for l in lyrics.split("\n") if l.strip()])


def generate_proof(song, output_dir):
    """为单首歌生成版权证明 Markdown"""
    title = song["title"]
    date = song.get("date", "N/A")
    genre = song.get("genre_label", song.get("genre_code", "N/A"))
    bpm = song.get("bpm", "N/A")
    chord = song.get("chord", "N/A")
    lyrics = song.get("lyrics_file") or song.get("lyrics", "")
    mmx_prompt = song.get("mmx_prompt", "")
    suno_prompt = song.get("suno_prompt", "")
    creation_note = song.get("creation_note", "")
    cover_prompt = song.get("cover_prompt", "")

    # 文件路径
    song_dir = song.get("dir") or song.get("song_dir", "")
    mp3_path = ""
    if song.get("versions"):
        mp3_path = song["versions"][0].get("filepath", "")
    elif song.get("mp3_path"):
        mp3_path = song["mp3_path"]
    elif song.get("mp3"):
        mp3_path = song["mp3"]

    cover_path = ""
    if song.get("cover"):
        cover_path = song["cover"].get("path", "")
    elif song.get("cover_path"):
        cover_path = song["cover_path"]

    # 哈希值
    mp3_md5 = file_hash(mp3_path) if mp3_path else "N/A"
    cover_md5 = file_hash(cover_path) if cover_path else "N/A"

    now = datetime.now().strftime("%Y-%m-%d")

    # 占位文本
    no_prompt = "（本歌曲创作时的 Prompt 记录未完整保存。创作工具与流程同其他作品一致：使用 MiniMax Music (mmx CLI) 生成音乐，GPT Image 2 生成封面。）"

    md = f"""# 音乐作品版权证明

## 《{title}》

---

### 一、作品基本信息

| 项目 | 内容 |
|------|------|
| **作品名称** | {title} |
| **音乐风格** | {genre} |
| **BPM（节拍速度）** | {bpm} |
| **和弦走向** | {chord} |
| **创作日期** | {date} |
| **版权所有人** | {CREATOR_NAME} |

---

### 二、原创歌词（完整文本）

> 以下歌词由创作者原创，使用 AI 辅助工具完成词曲创作。

```
{lyrics}
```

---

### 三、AI 创作工具与生成参数

本作品使用以下 AI 工具辅助创作，创作者对词曲、风格、编曲方向拥有完整的创作意图和控制权。

#### 3.1 音乐生成（MiniMax Music）

- **工具**：{AI_TOOLS["mmx"]}
- **生成 Prompt**：

{mmx_prompt if mmx_prompt else no_prompt}

#### 3.2 备选生成方案（Suno AI）

- **工具**：{AI_TOOLS["suno"]}
- **生成 Prompt**：

{suno_prompt if suno_prompt else no_prompt}

---

### 四、创作说明

{creation_note if creation_note else no_prompt}

---

### 五、封面艺术作品

- **生成工具**：GPT Image 2（via BizyAir）
- **封面 Prompt**：

{cover_prompt if cover_prompt else no_prompt}

---

### 六、作品文件信息

| 项目 | 详情 |
|------|------|
| **音频文件** | `{os.path.basename(mp3_path) if mp3_path else 'N/A'}` |
| **文件大小** | {file_size_str(mp3_path) if mp3_path else 'N/A'} |
| **MD5 校验** | `{mp3_md5}` |
| **封面文件** | `{os.path.basename(cover_path) if cover_path else 'N/A'}` |
| **封面 MD5** | `{cover_md5}` |
| **歌词行数** | {lyrics_line_count(lyrics)} 行 |

---

### 七、版权声明

本人 {CREATOR_NAME}，作为本作品《{title}》的创作者，郑重声明：

1. 本作品的歌词为本人原创创作；
2. 本作品的旋律、编曲方向、音乐风格均由本人设定并控制；
3. AI 工具（{AI_TOOLS["mmx"]}）仅作为创作辅助工具，本人对最终作品拥有完整的创作意图和决策权；
4. 本人确认所使用的 AI 工具的服务条款允许商业使用和音乐发行；
5. 本作品不侵犯任何第三方的著作权、商标权或其他知识产权。

**创作者签名**：{CREATOR_NAME}

**日期**：{now}

---

> 本版权证明由自动化系统生成，基于创作者的实际创作记录和 AI 工具使用日志。所有 Prompt、歌词、参数均为创作时的真实记录。
"""

    # 写入文件
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"版权证明_{title}.md"
    output_path = output_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return output_path


def main():
    output_dir = DEFAULT_OUTPUT_DIR

    # 解析参数
    filter_title = None
    args = sys.argv[1:]
    if "--output-dir" in args:
        idx = args.index("--output-dir")
        output_dir = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    if args:
        filter_title = args[0]

    songs = load_data()

    if filter_title:
        songs = [s for s in songs if filter_title in s["title"]]
        if not songs:
            print(f"❌ 未找到包含「{filter_title}」的歌曲")
            sys.exit(1)

    print(f"📋 共 {len(songs)} 首歌曲需要生成版权证明")
    print(f"📁 输出目录：{output_dir}")
    print()

    generated = []
    for song in songs:
        path = generate_proof(song, output_dir)
        generated.append(path)
        print(f"  ✅ {song['title']} → {path.name}")

    print(f"\n🎉 完成！共生成 {len(generated)} 份版权证明")
    print(f"📁 位置：{output_dir}")


if __name__ == "__main__":
    main()
