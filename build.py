#!/usr/bin/env python3
"""
Tomato Vault Builder - 番茄专项数据扫描器

Scans ~/Music/番茄音乐/ → songs.json

Usage:
    python build.py extract   # Scan & generate songs.json
"""

import json, os, re, sys, hashlib
from datetime import datetime
from pathlib import Path

MUSIC_DIR = Path("~/Music/番茄音乐").expanduser()
OUTPUT_DIR = Path(__file__).parent / "data"
SONGS_JSON = OUTPUT_DIR / "songs.json"

# 番茄曲风映射
GENRE_MAP = {
    'dance': {'label': '广场舞', 'icon': '💃', 'color': '#e74c5e'},
    'viral_pop': {'label': '洗脑情歌', 'icon': '🍬', 'color': '#f39c12'},
    'sad': {'label': '伤感情绪', 'icon': '🌧️', 'color': '#3498db'},
    'guofeng': {'label': '国风古风', 'icon': '🏮', 'color': '#9b59b6'},
    'hometown': {'label': '家乡励志', 'icon': '🏠', 'color': '#27ae60'},
}

def slugify(title: str, date: str = '') -> str:
    """Generate slug with date suffix for uniqueness."""
    slug = re.sub(r'[·\s]+', '-', title.strip())
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '', slug)
    if not slug:
        slug = hashlib.md5(title.encode()).hexdigest()[:12]
    if date:
        slug = f"{slug}_{date}"
    return slug


def scan_music_dir() -> dict:
    """Scan ~/Music/番茄音乐/ and return {song_title: {files}}."""
    songs = {}
    if not MUSIC_DIR.exists():
        print(f"📂 番茄音乐目录不存在: {MUSIC_DIR}（首日运行，无数据）")
        return songs

    for entry in sorted(MUSIC_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith('.'):
            continue

        # 解析日期前缀：YYYY-MM-DD_歌名
        # ⚠️ 只收录符合日期格式的文件夹，其余一律跳过（避免版权证明/测试文件夹混入）
        name = entry.name
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})_(.+)', name)
        if not date_match:
            continue  # 不符合 YYYY-MM-DD_歌名 格式的文件夹跳过
        date_str = date_match.group(1)
        song_title = date_match.group(2)

        song_files = {
            'dir': str(entry), 'title': song_title, 'date': date_str,
            'mp3': [], 'covers': [], 'posters': [], 'lyrics': [], 'lrc': [], 'other': []
        }

        for f in sorted(entry.iterdir()):
            if f.is_dir():
                continue
            nl = f.name.lower()
            if nl.endswith('.mp3'):
                song_files['mp3'].append(str(f))
            elif 'poster' in nl and nl.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                song_files['posters'].append(str(f))
            elif any(kw in nl for kw in ['cover', '_cover', 'album']) and nl.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                if '..' in f.name:
                    continue
                song_files['covers'].append(str(f))
            elif nl.endswith('.lrc'):
                song_files['lrc'].append(str(f))
            elif nl.endswith('.txt'):
                song_files['lyrics'].append(str(f))
            elif not nl.startswith('.'):
                song_files['other'].append(str(f))

        songs[song_title] = song_files

    print(f"📂 扫描到 {len(songs)} 首番茄歌曲")
    return songs


def detect_genre(title: str, lyrics: str) -> str:
    """从歌曲信息推测曲风代号（fallback，优先用 songs.json 已有值）"""
    return ''  # 由 Task T-A 在 tomato_audio.json 中指定


def run_extract():
    print("🍅 番茄专项数据扫描器\n")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fs_songs = scan_music_dir()

    # 读取现有的 tomato_audio.json / tomato_postprocess.json 获取元数据
    tomato_meta = {}
    for jsonfile in ['tomato_audio.json', 'tomato_postprocess.json']:
        p = OUTPUT_DIR / jsonfile
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for s in data.get('songs', []):
                    tomato_meta[s['title']] = s
            except Exception:
                pass

    songs = []
    for song_title, files in fs_songs.items():
        date_str = files.get('date', '')
        meta = tomato_meta.get(song_title, {})
        genre_code = meta.get('genre_code', '')

        song = {
            'slug': slugify(song_title, date_str),
            'title': song_title,
            'dir': files['dir'],
            'date': date_str or meta.get('date', ''),
            'genre_code': genre_code,
            'genre_label': meta.get('genre_label', GENRE_MAP.get(genre_code, {}).get('label', '')),
            'genre_icon': GENRE_MAP.get(genre_code, {}).get('icon', '🎵'),
            'genre_color': GENRE_MAP.get(genre_code, {}).get('color', '#c41e1e'),
            'chord': meta.get('chord', ''),
            'bpm': meta.get('bpm', 0),
            'dimension': '番茄专项',
            'dimensionIcon': '🍅',
        }

        # MP3 versions
        versions = []
        for mp3 in files['mp3']:
            versions.append({
                'filename': Path(mp3).name,
                'filepath': mp3,
                'platform': 'mmx',
                'version_tag': 'v1',
                'size_mb': round(os.path.getsize(mp3) / 1024 / 1024, 1) if os.path.exists(mp3) else 0
            })
        song['versions'] = sorted(versions, key=lambda v: v['version_tag'])

        # LRC (时间轴歌词)
        lrc_files = files.get('lrc', [])
        if lrc_files:
            song['lrc_url'] = lrc_files[0]

        # Cover
        if files['covers']:
            preferred = [c for c in files['covers'] if f'cover_{song_title}' in c]
            song['cover'] = {'path': preferred[0] if preferred else files['covers'][0], 'all_covers': files['covers']}
        else:
            song['cover'] = {'path': None, 'all_covers': []}

        # Poster
        preferred_poster = [p for p in files['posters'] if f'{song_title}_poster' in p]
        song['poster'] = preferred_poster[0] if preferred_poster else (files['posters'][0] if files['posters'] else None)

        # Lyrics
        if files['lyrics']:
            try:
                with open(files['lyrics'][0], 'r', encoding='utf-8') as f:
                    song['lyrics_file'] = f.read().strip()
            except Exception:
                pass

        # Duration (用 afinfo 读取真实时长，mutagen 在 mmx 输出上有 2x bug)
        if versions:
            try:
                mp3_path = versions[0]['filepath']
                if os.path.exists(mp3_path):
                    import subprocess as _sp
                    _r = _sp.run(['afinfo', mp3_path], capture_output=True, text=True, timeout=5)
                    for _line in _r.stdout.split('\n'):
                        if 'estimated duration' in _line:
                            # 格式: "estimated duration: 154.017959 sec"
                            _val = _line.split(':')[-1].strip().replace('sec', '').strip()
                            song['duration'] = round(float(_val))
                            break
                    if 'duration' not in song:
                        song['duration'] = 180
            except Exception:
                song['duration'] = 180
        else:
            song['duration'] = 180

        songs.append(song)

    # Merge with existing songs.json
    if SONGS_JSON.exists():
        try:
            with open(SONGS_JSON, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            old_map = {s['title']: s for s in old_data.get('songs', [])}
            for song in songs:
                old = old_map.get(song['title'])
                if old:
                    for k, v in old.items():
                        if k not in song or not song[k]:
                            song[k] = v
        except Exception:
            pass

    songs.sort(key=lambda s: (s.get('date', '0000'), s.get('title')), reverse=True)

    result = {
        'generated_at': datetime.now().isoformat(),
        'total_songs': len(songs),
        'songs': songs
    }

    with open(SONGS_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 生成 {SONGS_JSON}")
    print(f"   总计: {len(songs)} 首")
    print(f"   有封面: {sum(1 for s in songs if s['cover']['path'])}")
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == 'extract':
        run_extract()
    else:
        print(f"Usage: python build.py [extract]")
