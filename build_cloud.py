#!/usr/bin/env python3
"""
Build Cloud (tomato) — 生成番茄音乐报云端版静态站点

从 data/songs.json + data/lrc_data.json 生成纯云端 index.html：
mp3/cover/poster URL 优先取 youmind_*_cdn（卡46 回填），输出到 site_cloud/。
HTML 模板直接复用 vault.py 的 generate_html（零模板漂移）。

用法:
  python build_cloud.py                          # 默认 base=https://tomato-vault.1986318.xyz
  python build_cloud.py --base-url https://tomato.1986318.xyz
  python build_cloud.py --keep-versionlrcs       # 兜底开关：保留 versionLrcs（默认剥离，省 ~32%）

自检（失败即 exit≠0）:
  1. 产物 > 1,500,000 B
  2. 产物内不得出现 '/music/'（有 URL 没换成 CDN = 必杀）
  3. https://cdn.youmindassets.com/ 出现次数 >= 歌数x3 x 90%
  4. 打印三类 URL 的 CDN 条数 / 回退条数
"""

import json, os, re, sys, base64, importlib.util
from pathlib import Path

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
SONGS_JSON = DATA_DIR / "songs.json"
LRC_JSON = DATA_DIR / "lrc_data.json"

DEFAULT_BASE_URL = "https://tomato-vault.1986318.xyz"

GENRE_MAP = {
    'dance': {'label': '广场舞', 'icon': '💃', 'color': '#e74c5e', 'order': 1},
    'viral_pop': {'label': '洗脑情歌', 'icon': '🍬', 'color': '#f39c12', 'order': 2},
    'sad': {'label': '伤感情绪', 'icon': '🌧️', 'color': '#3498db', 'order': 3},
    'guofeng': {'label': '国风古风', 'icon': '🏮', 'color': '#9b59b6', 'order': 4},
    'hometown': {'label': '家乡励志', 'icon': '🏠', 'color': '#27ae60', 'order': 5},
}


def load_vault_module():
    """按路径加载 vault.py（不走 `import vault`：规避自动化环境的本地/PyPI 模块名冲突扫描）。"""
    spec = importlib.util.spec_from_file_location("tomato_vault_mod", str(BASE / "vault.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_cloud(base_url: str = "", keep_versionlrcs: bool = False):
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    print(f"🔨 番茄音乐报 Cloud 构建中...")
    print(f"   Base URL: {base_url}")
    print(f"   versionLrcs: {'保留' if keep_versionlrcs else '剥离（-32%）'}")

    vault = load_vault_module()  # 复用 _to_url + generate_html，语义与 vault.build() 完全一致

    with open(SONGS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    songs = data.get('songs', [])

    lrc_data = {}
    if LRC_JSON.exists():
        with open(LRC_JSON, 'r', encoding='utf-8') as f:
            lrc_data = json.load(f)

    stats = {"mp3_cdn": 0, "mp3_fb": 0, "cover_cdn": 0, "cover_fb": 0,
             "poster_cdn": 0, "poster_fb": 0, "no_mp3": 0}

    song_entries = []
    for song in songs:
        if song.get('exclude'):
            continue

        slug = song['slug']
        title = song['title']

        # Best version audio —— 与 vault.build() 同款打分
        versions = song.get('versions', [])
        best = None
        if versions:
            scored = []
            for v in versions:
                tag = v.get('version_tag', 'v1')
                num = int(re.search(r'(\d+)', tag).group(1)) if re.search(r'(\d+)', tag) else 1
                scored.append((num, v.get('size_mb', 0), v))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            best = scored[0][2]

        # mp3：youmind 优先，无则回退本地路径 URL（回退出现会在自检 2 被击杀）
        mp3_url = song.get('youmind_mp3_cdn', '')
        if mp3_url:
            stats["mp3_cdn"] += 1
        elif best:
            mp3_url = vault._to_url(best.get('filepath', ''))
            stats["mp3_fb"] += 1
        else:
            stats["no_mp3"] += 1

        # Cover：youmind 优先
        cover_url = song.get('youmind_cover_cdn', '')
        if not cover_url:
            cover = song.get('cover', {})
            cover_path = cover.get('path', '') if isinstance(cover, dict) else cover
            if cover_path:
                cover_url = vault._to_url(cover_path)
                stats["cover_fb"] += 1
        if cover_url and song.get('youmind_cover_cdn'):
            stats["cover_cdn"] += 1

        # Poster：youmind 优先
        poster_url = song.get('youmind_poster_cdn', '')
        if not poster_url and song.get('poster'):
            poster_url = vault._to_url(song['poster'])
            stats["poster_fb"] += 1
        if poster_url and song.get('youmind_poster_cdn'):
            stats["poster_cdn"] += 1

        # LRC —— 与 vault.build() 逐字同款匹配/转换逻辑
        version_lrcs = {}
        synced_lyrics = ''
        for k, v in lrc_data.items():
            if k == title or k.startswith(f"{title}__"):
                ver_tag = k.split('__', 1)[1] if '__' in k else 'v1'
                if isinstance(v, list) and v:
                    lrc_lines = []
                    for entry in v:
                        t = entry.get('time', 0)
                        txt = entry.get('text', '')
                        mins = int(t // 60)
                        secs = t % 60
                        lrc_lines.append(f"[{mins:02d}:{secs:05.2f}]{txt}")
                    version_lrcs[ver_tag] = '\n'.join(lrc_lines)
                else:
                    version_lrcs[ver_tag] = v if isinstance(v, str) else ''
        if version_lrcs:
            first_key = list(version_lrcs.keys())[0]
            synced_lyrics = version_lrcs[first_key]

        # Lyrics text（tomato 的 lyrics_file 存的是歌词文本）
        lyrics_text = song.get('lyrics_file', '') or song.get('lyrics', '')

        if keep_versionlrcs:
            entry_version_lrcs = version_lrcs
        else:
            entry_version_lrcs = {}

        song_entries.append({
            'slug': slug,
            'title': title,
            'mp3': mp3_url,
            'cover': cover_url,
            'poster': poster_url,
            'genre_code': song.get('genre_code', ''),
            'genre_label': song.get('genre_label', GENRE_MAP.get(song.get('genre_code', ''), {}).get('label', '')),
            'genre_icon': song.get('genre_icon', GENRE_MAP.get(song.get('genre_code', ''), {}).get('icon', '🍅')),
            'genre_color': song.get('genre_color', GENRE_MAP.get(song.get('genre_code', ''), {}).get('color', '#c41e1e')),
            'date': song.get('date', ''),
            'duration': song.get('duration', 0),
            'chord': song.get('chord', ''),
            'bpm': song.get('bpm', 0),
            'lyrics': lyrics_text,
            'syncedLyrics': synced_lyrics,
            'versionLrcs': entry_version_lrcs,
            'versions': [{'filename': v.get('filename', ''), 'version_tag': v.get('version_tag', 'v1'),
                          'platform': v.get('platform', 'mmx'), 'size_mb': v.get('size_mb', 0)} for v in versions],
        })

    song_entries.sort(key=lambda s: (s['date'] or '0000', s['title']), reverse=True)

    songs_json_str = json.dumps(song_entries, ensure_ascii=False)
    html = vault.generate_html(song_entries, songs_json_str)

    # 防止 CDN Referer 拦截（与灵感线 build_cloud 同款后处理）
    html = html.replace('<head>', '<head>\n<meta name="referrer" content="no-referrer">')

    # favicon 内联为 data URI（云端无本地静态文件，避免头部图标 404）
    fav_path = BASE / "favicon.svg"
    if fav_path.exists():
        fav_uri = "data:image/svg+xml;base64," + base64.b64encode(fav_path.read_bytes()).decode()
        html = html.replace("/favicon.svg", fav_uri)

    out_dir = BASE / "site_cloud"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")

    # ─── 自检（失败 exit≠0）────────────────────────────────────────
    size = os.path.getsize(out_file)
    print(f"\n✅ Built {len(song_entries)} 首 → {out_file}")
    print(f"   Size: {size / 1024:.0f} KB ({size} B)")

    ok = True

    # 1. 体积
    if size <= 1_500_000:
        print(f"   ❌ 自检1 失败: 产物 {size} B <= 1,500,000 B")
        ok = False
    else:
        print(f"   ✅ 自检1: 体积 {size:,} B > 1,500,000 B")

    # 2. 不得出现 /music/（比任务卡的 `"/music/` 更严：绝对 URL 形式的回退也击杀）
    n_music = html.count("/music/")
    if n_music:
        print(f"   ❌ 自检2 失败: 产物内出现 /music/ x{n_music}（有 URL 没换成 CDN）")
        for m in re.finditer(r".{60}/music/.{60}", html):
            print(f"      …{m.group(0)}…")
            break
        ok = False
    else:
        print("   ✅ 自检2: 无 /music/ 残留")

    # 3. CDN URL 占比
    n_cdn = html.count("https://cdn.youmindassets.com/")
    need = int(len(song_entries) * 3 * 0.9)
    if n_cdn < need:
        print(f"   ❌ 自检3 失败: youmind CDN URL {n_cdn} < 阈值 {need}（{len(song_entries)}首x3x90%）")
        ok = False
    else:
        print(f"   ✅ 自检3: CDN URL {n_cdn} >= {need}")

    # 4. 三类 URL 明细
    print(f"   ✅ 自检4 明细: mp3 CDN {stats['mp3_cdn']} / 回退 {stats['mp3_fb']} / 无mp3 {stats['no_mp3']}")
    print(f"                 cover CDN {stats['cover_cdn']} / 回退 {stats['cover_fb']}")
    print(f"                 poster CDN {stats['poster_cdn']} / 回退 {stats['poster_fb']}")

    if not ok:
        sys.exit(1)
    return out_file


if __name__ == "__main__":
    base_url = DEFAULT_BASE_URL
    keep = "--keep-versionlrcs" in sys.argv
    if "--base-url" in sys.argv:
        idx = sys.argv.index("--base-url")
        if idx + 1 < len(sys.argv):
            base_url = sys.argv[idx + 1]
    build_cloud(base_url, keep_versionlrcs=keep)
