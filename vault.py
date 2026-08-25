#!/usr/bin/env python3
"""
Tomato Vault — 番茄音乐报 v1.0
报纸风音乐展示站 + 管理后台

Usage:
  python vault.py           # Build site + start server on port 8893
  python vault.py build     # Build only
  python vault.py serve     # Serve only
"""

import json, os, re, sys, time, urllib.parse, webbrowser, shutil, hashlib
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
SONGS_JSON = DATA_DIR / "songs.json"
LRC_JSON = DATA_DIR / "lrc_data.json"
SITE_DIR = BASE
MUSIC_DIR = Path("~/Music/番茄音乐").expanduser()
PORT = 8896

GENRE_MAP = {
    'dance': {'label': '广场舞', 'icon': '💃', 'color': '#e74c5e', 'order': 1},
    'viral_pop': {'label': '洗脑情歌', 'icon': '🍬', 'color': '#f39c12', 'order': 2},
    'sad': {'label': '伤感情绪', 'icon': '🌧️', 'color': '#3498db', 'order': 3},
    'guofeng': {'label': '国风古风', 'icon': '🏮', 'color': '#9b59b6', 'order': 4},
    'hometown': {'label': '家乡励志', 'icon': '🏠', 'color': '#27ae60', 'order': 5},
}


def _safe_write(filepath, content):
    """Sandbox-safe write via tmp + shutil.copy2."""
    tmp = '/tmp/_tomato_tmp_write.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(content)
    shutil.copy2(tmp, str(filepath))
    try:
        os.unlink(tmp)
    except OSError:
        pass


def _to_url(path):
    """Convert absolute path to /music/ URL."""
    if not path:
        return ''
    real = os.path.realpath(str(path))
    music_real = os.path.realpath(str(MUSIC_DIR))
    if real.startswith(music_real + '/'):
        return '/music/' + urllib.parse.quote(real[len(music_real)+1:])
    return path


def build():
    """Generate the newspaper-style site."""
    print("🔨 番茄音乐报构建中...\n")

    # ⚠️ 每次都先扫描，确保今日新歌被收入后再重建
    import subprocess
    print("   📂 扫描音乐目录...")
    subprocess.run([sys.executable, str(BASE / "build.py"), "extract"], cwd=str(BASE), capture_output=True, text=True)

    with open(SONGS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    songs = data.get('songs', [])

    # Load LRC data
    lrc_data = {}
    if LRC_JSON.exists():
        with open(LRC_JSON, 'r', encoding='utf-8') as f:
            lrc_data = json.load(f)

    song_entries = []
    for song in songs:
        if song.get('exclude'):
            continue

        slug = song['slug']
        title = song['title']

        # Best version audio
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

        mp3_rel = ''
        if best:
            mp3_rel = _to_url(best.get('filepath', ''))

        # Cover
        cover_rel = ''
        cover = song.get('cover', {})
        cover_path = cover.get('path', '') if isinstance(cover, dict) else cover
        if cover_path:
            cover_rel = _to_url(cover_path)

        # Poster
        poster_rel = ''
        if song.get('poster'):
            poster_rel = _to_url(song['poster'])

        # LRC — 先按歌名匹配（lrc_data.json 的 key 是纯歌名，值为 [{time,text}]）
        version_lrcs = {}
        synced_lyrics = ''
        for k, v in lrc_data.items():
            # lrc_data key = 歌名 或 歌名__verTag
            if k == title or k.startswith(f"{title}__"):
                ver_tag = k.split('__', 1)[1] if '__' in k else 'v1'
                # 将 [{time,text}] 数组转 LRC 字符串 [mm:ss.xx]text
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

        # Lyrics text
        lyrics_text = song.get('lyrics_file', '') or song.get('lyrics', '')

        song_entries.append({
            'slug': slug,
            'title': title,
            'mp3': mp3_rel,
            'cover': cover_rel,
            'poster': poster_rel,
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
            'versionLrcs': version_lrcs,
            'versions': [{'filename': v.get('filename', ''), 'version_tag': v.get('version_tag', 'v1'),
                          'platform': v.get('platform', 'mmx'), 'size_mb': v.get('size_mb', 0)} for v in versions],
        })

    song_entries.sort(key=lambda s: (s['date'] or '0000', s['title']), reverse=True)

    songs_json_str = json.dumps(song_entries, ensure_ascii=False)
    html = generate_html(song_entries, songs_json_str)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    out = SITE_DIR / "index.html"
    _safe_write(out, html)

    print(f"✅ 构建完成: {len(song_entries)} 首 → {out}")
    print(f"   大小: {os.path.getsize(out) / 1024:.0f} KB")
    return True


# ═══ HTML 生成 ═════════════════════════════════════════════════════════════════

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --bg: #fdfcf8; --bg-soft: #f5f0e6; --bg-dark: #1a1a2e;
  --text: #111; --text-muted: #555; --text-light: #888;
  --red: #c41e1e; --dark-blue: #1f2d4a; --gold: #b8443c;
  --serif: "Noto Serif SC","Songti SC","STSong",serif;
  --sans: "Noto Sans SC","PingFang SC",sans-serif;
  --display: "Playfair Display","Georgia",serif;
  --r: 4px;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:#e8e5df;font-family:var(--sans);color:var(--text);-webkit-font-smoothing:antialiased}

/* Sticky Header */
.site-header{position:sticky;top:0;z-index:100;background:rgba(253,252,248,0.95);backdrop-filter:blur(20px);border-bottom:2px solid var(--text);padding:8px 24px}
.header-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px}
.header-title{font-family:var(--display);font-size:1.1rem;font-weight:900;color:var(--red);white-space:nowrap}
.header-stats{font-size:.7rem;color:var(--text-muted);font-family:var(--sans)}
.search-box{display:flex;align-items:center;gap:6px;background:var(--bg-soft);border:1px solid #ddd;padding:4px 10px;border-radius:var(--r)}
.search-box input{border:none;background:none;outline:none;font-size:.75rem;font-family:var(--sans);width:160px;color:var(--text)}
.filter-row{display:flex;gap:6px;flex-wrap:wrap;max-width:1200px;margin:6px auto 0;padding:0 24px}
.filter-tag{background:none;border:1px solid #ccc;color:var(--text-muted);font-size:.65rem;padding:3px 10px;border-radius:20px;cursor:pointer;transition:all .2s;font-family:var(--sans);white-space:nowrap}
.filter-tag:hover{border-color:var(--red);color:var(--text)}
.filter-tag.active{background:var(--red);border-color:var(--red);color:#fff}
.filter-tag .count{opacity:.6;font-size:.55rem;margin-left:3px}

/* Main */
.main-content{max-width:1200px;margin:0 auto;padding:24px 24px 120px}
.empty-state{text-align:center;padding:120px 20px;color:var(--text-light)}
.empty-state .icon{font-size:48px;margin-bottom:16px}
.empty-state .title{font-family:var(--serif);font-size:1.4rem;margin-bottom:8px}

/* Date Section */
.date-section{margin-bottom:32px}
.section-header{display:flex;align-items:center;gap:8px;padding:8px 0;border-top:2px double var(--text);border-bottom:1px solid #ccc;margin-bottom:16px;cursor:pointer;user-select:none}
.section-header:hover{color:var(--red)}
.section-date{font-family:var(--display);font-size:1rem;font-weight:700;letter-spacing:.02em}
.section-count{font-size:.7rem;color:var(--text-muted)}
.section-fold{margin-left:auto;font-size:.7rem;color:var(--text-light)}
.section-header.folded .section-fold{transform:rotate(-90deg)}

/* Hero (头条) */
.hero-card{display:grid;grid-template-columns:300px 1fr;gap:24px;background:var(--bg);border:1px solid #ddd;padding:24px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,0.06)}
.hero-cover{width:300px;height:300px;overflow:hidden;background:var(--bg-soft)}
.hero-cover img{width:100%;height:100%;object-fit:cover}
.hero-info{display:flex;flex-direction:column;gap:8px}
.hero-eyebrow{font-family:var(--display);font-size:.7rem;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.1em}
.hero-title{font-family:var(--serif);font-size:2rem;font-weight:700;line-height:1.2;color:var(--text)}
.hero-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:.75rem;color:var(--text-muted)}
.hero-meta .genre-badge{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:3px;font-size:.7rem;font-weight:600}
.hero-lyrics{font-family:var(--serif);font-size:.85rem;line-height:1.8;color:var(--text-muted);column-count:2;column-gap:20px;column-rule:1px solid #eee;max-height:120px;overflow:hidden;margin-top:8px}
.hero-player{margin-top:auto}

/* Today Grid (其余4首) */
.today-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}
.song-card{background:var(--bg);border:1px solid #ddd;padding:0;overflow:hidden;cursor:pointer;transition:all .2s;display:flex;flex-direction:column}
.song-card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.1);transform:translateY(-2px)}
.card-cover{width:100%;aspect-ratio:1;overflow:hidden;background:var(--bg-soft);position:relative}
.card-cover img{width:100%;height:100%;object-fit:cover}
.card-cover-ph{width:100%;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:2rem;background:var(--bg-soft)}
.play-btn{position:absolute;bottom:8px;right:8px;width:32px;height:32px;border-radius:50%;background:rgba(200,30,30,0.9);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.8rem;opacity:0;transition:opacity .2s}
.song-card:hover .play-btn{opacity:1}
.card-body{padding:10px 12px}
.card-title{font-family:var(--serif);font-size:.9rem;font-weight:600;line-height:1.3;margin-bottom:4px}
.card-meta{display:flex;gap:6px;align-items:center;font-size:.65rem;color:var(--text-muted)}
.card-genre{font-size:.6rem;padding:1px 6px;border-radius:3px;color:#fff;font-weight:600}

/* Row (往期歌曲行) */
.song-row{display:flex;align-items:center;gap:12px;padding:8px 12px;border-bottom:1px solid #eee;cursor:pointer;transition:background .15s}
.song-row:hover{background:var(--bg-soft)}
.song-row.playing{background:var(--bg-soft);border-left:3px solid var(--red)}
.row-cover{width:48px;height:48px;flex-shrink:0;overflow:hidden;background:var(--bg-soft)}
.row-cover img{width:100%;height:100%;object-fit:cover}
.row-cover-ph{width:48px;height:48px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;background:var(--bg-soft)}
.row-info{flex:1;min-width:0}
.row-title{font-family:var(--serif);font-size:.85rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row-meta{font-size:.65rem;color:var(--text-muted);margin-top:2px}
.row-duration{font-family:var(--display);font-size:.7rem;color:var(--text-light);flex-shrink:0}
.row-play{width:28px;height:28px;flex-shrink:0;border-radius:50%;background:var(--bg-soft);border:1px solid #ddd;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.6rem;color:var(--red)}
.song-row:hover .row-play{background:var(--red);color:#fff;border-color:var(--red)}

/* Player Bar */
.player-bar{position:fixed;bottom:0;left:0;right:0;background:var(--bg-dark);color:#fff;padding:10px 24px;display:flex;align-items:center;gap:16px;transform:translateY(100%);transition:transform .3s;z-index:200}
.player-bar.active{transform:translateY(0)}
.player-cover{width:44px;height:44px;border-radius:4px;overflow:hidden;flex-shrink:0;background:#333}
.player-cover img{width:100%;height:100%;object-fit:cover}
.player-info{flex:1;min-width:0}
.player-title{font-size:.8rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.player-sub{font-size:.65rem;opacity:.6;margin-top:2px}
.player-controls{display:flex;align-items:center;gap:8px}
.player-btn{width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.1);border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.9rem}
.player-btn:hover{background:rgba(255,255,255,0.2)}
.player-progress{flex:1;display:flex;align-items:center;gap:8px;max-width:300px}
.player-progress input[type=range]{flex:1;-webkit-appearance:none;height:3px;background:rgba(255,255,255,0.2);border-radius:2px;outline:none}
.player-progress input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:var(--red);cursor:pointer}
.player-time{font-family:var(--display);font-size:.65rem;opacity:.6;white-space:nowrap}

/* Lyrics Panel */
.lyrics-panel{position:fixed;bottom:64px;right:24px;width:400px;max-height:400px;background:var(--bg);border:1px solid #ddd;box-shadow:0 -4px 24px rgba(0,0,0,0.12);padding:20px;overflow-y:auto;z-index:150;transform:translateX(420px);transition:transform .3s;display:none}
.lyrics-panel.show{display:block;transform:translateX(0)}
.lyrics-panel-title{font-family:var(--serif);font-size:.9rem;font-weight:700;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #eee}
.lyrics-panel-title .close{float:right;cursor:pointer;color:var(--text-muted);font-size:1rem}
.lyric-line{font-size:.85rem;line-height:2;color:var(--text-muted);transition:color .3s}
.lyric-line.active{color:var(--red);font-weight:600}

/* Colophon */
.colophon{max-width:1200px;margin:0 auto;padding:20px 24px 40px;text-align:center;border-top:2px double var(--text)}
.colophon-title{font-family:var(--display);font-size:1rem;font-weight:700;color:var(--red);margin-bottom:4px}
.colophon-text{font-size:.7rem;color:var(--text-muted);line-height:1.8}

@media (max-width:900px){
  .hero-card{grid-template-columns:1fr}
  .hero-cover{width:100%;height:240px}
  .today-grid{grid-template-columns:repeat(2,1fr)}
  .hero-lyrics{column-count:1}
  .lyrics-panel{width:calc(100% - 32px);right:16px;bottom:60px}
}
"""

JS = """
var SONGS = SONGS_DATA;
var audio = new Audio();
var currentSlug = null;
var lrcData = {};
var activeFilter = 'all';

function init() {
  audio.addEventListener('timeupdate', onTimeUpdate);
  audio.addEventListener('ended', playNext);
  audio.addEventListener('loadedmetadata', function() {
    document.getElementById('pDur').textContent = fmtTime(audio.duration);
  });
  renderFilters();
  renderSongs();
}

function renderFilters() {
  var counts = {};
  SONGS.forEach(function(s) {
    var gc = s.genre_code || 'other';
    counts[gc] = (counts[gc] || 0) + 1;
  });
  var html = '<button class="filter-tag active" data-filter="all" onclick="setFilter(\\'all\\')">全部 <span class="count">' + SONGS.length + '</span></button>';
  var order = ['dance','viral_pop','sad','guofeng','hometown'];
  order.forEach(function(gc) {
    if (counts[gc]) {
      var s = SONGS.find(function(x) { return x.genre_code === gc; });
      var icon = s ? s.genre_icon : '🎵';
      html += '<button class="filter-tag" data-filter="' + gc + '" onclick="setFilter(\\'' + gc + '\\')">' + icon + ' ' + (s?s.genre_label:gc) + ' <span class="count">' + counts[gc] + '</span></button>';
    }
  });
  document.getElementById('filterRow').innerHTML = html;
}

function setFilter(f) {
  activeFilter = f;
  document.querySelectorAll('.filter-tag').forEach(function(t) {
    t.classList.toggle('active', t.getAttribute('data-filter') === f);
  });
  renderSongs();
}

function getFiltered() {
  var search = (document.getElementById('searchInput').value || '').toLowerCase();
  return SONGS.filter(function(s) {
    var matchFilter = activeFilter === 'all' || s.genre_code === activeFilter;
    var matchSearch = !search || s.title.toLowerCase().indexOf(search) >= 0 || (s.lyrics || '').toLowerCase().indexOf(search) >= 0;
    return matchFilter && matchSearch;
  });
}

function renderSongs() {
  var filtered = getFiltered();
  var container = document.getElementById('songContainer');
  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="icon">📰</div><div class="title">今日报刊暂未发行</div><div style="color:#888;font-size:.8rem;margin-top:8px">等待番茄专项生产线启动...</div></div>';
    return;
  }

  // Group by date
  var byDate = {};
  filtered.forEach(function(s) {
    var d = s.date || '未知日期';
    if (!byDate[d]) byDate[d] = [];
    byDate[d].push(s);
  });
  var dates = Object.keys(byDate).sort().reverse();

  var html = '';
  var isFirstSection = true;
  dates.forEach(function(date) {
    var songs = byDate[date];
    // Sort within date by genre order
    songs.sort(function(a, b) {
      var ao = a.genre_code === 'dance' ? 1 : a.genre_code === 'viral_pop' ? 2 : a.genre_code === 'sad' ? 3 : a.genre_code === 'guofeng' ? 4 : a.genre_code === 'hometown' ? 5 : 9;
      var bo = b.genre_code === 'dance' ? 1 : b.genre_code === 'viral_pop' ? 2 : b.genre_code === 'sad' ? 3 : b.genre_code === 'guofeng' ? 4 : b.genre_code === 'hometown' ? 5 : 9;
      return ao - bo;
    });

    html += '<div class="date-section' + (isFirstSection ? '' : '') + '">';
    html += '<div class="section-header" onclick="toggleSection(this)"><span class="section-date">' + formatDate(date) + '</span><span class="section-count">· ' + songs.length + ' 首</span><span class="section-fold">▼</span></div>';
    html += '<div class="section-body">';

    if (isFirstSection && songs.length >= 3) {
      // Hero = first song (广场舞优先)
      var hero = songs[0];
      html += renderHero(hero);
      // Today grid = remaining songs
      var rest = songs.slice(1);
      if (rest.length > 0) {
        html += '<div class="today-grid">';
        rest.forEach(function(s) { html += renderCard(s); });
        html += '</div>';
      }
    } else if (isFirstSection && songs.length > 0 && songs.length < 3) {
      // Not enough for hero, show as cards
      html += '<div class="today-grid" style="grid-template-columns:repeat(' + Math.min(songs.length,4) + ',1fr)">';
      songs.forEach(function(s) { html += renderCard(s); });
      html += '</div>';
    } else {
      // Archive rows
      songs.forEach(function(s) { html += renderRow(s); });
    }

    html += '</div></div>';
    isFirstSection = false;
  });

  container.innerHTML = html;
}

function renderHero(s) {
  var cover = s.cover ? '<img src="' + s.cover + '" loading="lazy">' : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:3rem;background:#f5f0e6">' + (s.genre_icon||'🍅') + '</div>';
  var lyricsHtml = '';
  if (s.lyrics) {
    var lines = s.lyrics.split('\\n').filter(function(l) { return l.trim() && !l.startsWith('['); }).slice(0, 6);
    lyricsHtml = '<div class="hero-lyrics">' + lines.map(esc).join('<br>') + '</div>';
  }
  var playBtn = s.mp3 ? '<button class="player-btn" style="background:#c41e1e;width:44px;height:44px" onclick="event.stopPropagation();play(\\'' + s.slug + '\\')">' + (isPlaying(s.slug) ? '⏸' : '▶') + '</button>' : '';
  return '<div class="hero-card" onclick="play(\\'' + s.slug + '\\')">' +
    '<div class="hero-cover">' + cover + '</div>' +
    '<div class="hero-info">' +
    '<div class="hero-eyebrow">★ 今日头条 · ' + esc(s.genre_label||'') + '</div>' +
    '<div class="hero-title">' + esc(s.title) + '</div>' +
    '<div class="hero-meta"><span class="genre-badge" style="background:' + (s.genre_color||'#c41e1e') + ';color:#fff">' + (s.genre_icon||'') + ' ' + esc(s.genre_label||'') + '</span>' +
    (s.bpm ? '<span>🎯 ' + s.bpm + ' BPM</span>' : '') +
    (s.chord ? '<span>🎵 ' + esc(s.chord) + '</span>' : '') +
    (s.duration ? '<span>⏱ ' + fmtTime(s.duration) + '</span>' : '') + '</div>' +
    lyricsHtml +
    '<div class="hero-player">' + playBtn + '</div>' +
    '</div></div>';
}

function renderCard(s) {
  var cover = s.cover ? '<img src="' + s.cover + '" loading="lazy">' : '<div class="card-cover-ph">' + (s.genre_icon||'🍅') + '</div>';
  var playBtn = s.mp3 ? '<button class="play-btn" onclick="event.stopPropagation();play(\\'' + s.slug + '\\')">' + (isPlaying(s.slug) ? '⏸' : '▶') + '</button>' : '';
  return '<div class="song-card" onclick="play(\\'' + s.slug + '\\')">' +
    '<div class="card-cover">' + cover + playBtn + '</div>' +
    '<div class="card-body">' +
    '<div class="card-title">' + esc(s.title) + '</div>' +
    '<div class="card-meta"><span class="card-genre" style="background:' + (s.genre_color||'#c41e1e') + '">' + esc(s.genre_label||'') + '</span>' +
    (s.duration ? '<span>' + fmtTime(s.duration) + '</span>' : '') + '</div>' +
    '</div></div>';
}

function renderRow(s) {
  var cover = s.cover ? '<img src="' + s.cover + '" loading="lazy">' : '<div class="row-cover-ph">' + (s.genre_icon||'🍅') + '</div>';
  var playing = isPlaying(s.slug);
  return '<div class="song-row' + (playing ? ' playing' : '') + '" onclick="play(\\'' + s.slug + '\\')">' +
    '<div class="row-cover">' + cover + '</div>' +
    '<div class="row-info"><div class="row-title">' + esc(s.title) + '</div>' +
    '<div class="row-meta"><span style="color:' + (s.genre_color||'#c41e1e') + '">' + (s.genre_icon||'') + ' ' + esc(s.genre_label||'') + '</span>' +
    (s.chord ? ' · ' + esc(s.chord) : '') + (s.bpm ? ' · ' + s.bpm + 'BPM' : '') + '</div></div>' +
    '<span class="row-duration">' + (s.duration ? fmtTime(s.duration) : '') + '</span>' +
    '<button class="row-play" onclick="event.stopPropagation();play(\\'' + s.slug + '\\')">' + (playing ? '⏸' : '▶') + '</button>' +
    '</div>';
}

function isPlaying(slug) { return currentSlug === slug && !audio.paused; }

function play(slug) {
  var s = SONGS.find(function(x) { return x.slug === slug; });
  if (!s || !s.mp3) return;
  if (currentSlug === slug && !audio.paused) {
    audio.pause();
    renderSongs();
    updatePlayer();
    return;
  }
  audio.src = s.mp3;
  audio.play();
  currentSlug = slug;
  lrcData = {};
  if (s.syncedLyrics) { parseLrc(s.syncedLyrics); }
  renderSongs();
  updatePlayer();
  document.getElementById('lyricsBtn').style.opacity = s.syncedLyrics ? '1' : '.4';
}

function updatePlayer() {
  var bar = document.getElementById('playerBar');
  if (!currentSlug) { bar.classList.remove('active'); return; }
  var s = SONGS.find(function(x) { return x.slug === currentSlug; });
  if (!s) return;
  bar.classList.add('active');
  document.getElementById('pTitle').textContent = s.title;
  document.getElementById('pSub').textContent = (s.genre_icon||'') + ' ' + (s.genre_label||'');
  var c = document.getElementById('pCover');
  c.innerHTML = s.cover ? '<img src="' + s.cover + '">' : (s.genre_icon||'🍅');
  c.style.fontSize = s.cover ? '' : '1.2rem';
  c.style.display = 'flex';
  c.style.alignItems = 'center';
  c.style.justifyContent = 'center';
  document.getElementById('pPlay').innerHTML = audio.paused ? '▶' : '⏸';
}

function togglePlay() {
  if (!currentSlug) { var f = getFiltered(); if (f.length) play(f[0].slug); return; }
  if (audio.paused) audio.play(); else audio.pause();
  updatePlayer();
  renderSongs();
}

function playNext() {
  var f = getFiltered();
  var i = f.findIndex(function(s) { return s.slug === currentSlug; });
  if (i >= 0 && i < f.length - 1) play(f[i+1].slug);
}

function playPrev() {
  var f = getFiltered();
  var i = f.findIndex(function(s) { return s.slug === currentSlug; });
  if (i > 0) play(f[i-1].slug);
}

function onTimeUpdate() {
  if (!audio.duration) return;
  var pct = audio.currentTime / audio.duration * 100;
  document.getElementById('pProgress').value = pct;
  document.getElementById('pCur').textContent = fmtTime(audio.currentTime);
  // LRC sync
  if (Object.keys(lrcData).length > 0) {
    var times = Object.keys(lrcData).map(Number).sort(function(a,b){return a-b});
    var cur = -1;
    for (var i = 0; i < times.length; i++) {
      if (audio.currentTime >= times[i]) cur = i; else break;
    }
    document.querySelectorAll('.lyric-line').forEach(function(el, i) {
      el.classList.toggle('active', i === cur);
    });
    var activeEl = document.querySelector('.lyric-line.active');
    if (activeEl) activeEl.scrollIntoView({behavior:'smooth', block:'center'});
  }
}

function parseLrc(lrcStr) {
  lrcData = {};
  var lines = lrcStr.split('\\n');
  lines.forEach(function(line) {
    var m = line.match(/\\[(\\d+):(\\d+)\\.(\\d+)\\](.*)/);
    if (m) {
      var t = parseInt(m[1]) * 60 + parseInt(m[2]) + parseInt(m[3]) / 1000;
      lrcData[t] = m[4].trim();
    }
  });
}

function toggleLyrics() {
  var p = document.getElementById('lyricsPanel');
  if (!currentSlug) return;
  var s = SONGS.find(function(x) { return x.slug === currentSlug; });
  if (!s) return;
  var lyricsText = s.syncedLyrics || s.lyrics || '';
  if (!lyricsText) return;
  var lines = lyricsText.split('\\n').filter(function(l) { return l.trim(); });
  var html = '<div class="lyrics-panel-title">📰 ' + esc(s.title) + ' <span class="close" onclick="toggleLyrics()">✕</span></div>';
  lines.forEach(function(l) {
    var text = l.replace(/^\\[.*?\\]/, '');
    if (text.trim()) html += '<div class="lyric-line">' + esc(text) + '</div>';
  });
  p.innerHTML = html;
  p.classList.toggle('show');
}

function toggleSection(el) {
  var body = el.nextElementSibling;
  el.classList.toggle('folded');
  body.style.display = el.classList.contains('folded') ? 'none' : 'block';
}

function onSearch() { renderSongs(); }
function clearSearch() { document.getElementById('searchInput').value = ''; renderSongs(); }
function esc(s) { if (!s) return ''; var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function fmtTime(s) { if (!s || isNaN(s)) return '0:00'; var m = Math.floor(s/60); return m + ':' + String(Math.floor(s%60)).padStart(2,'0'); }
function formatDate(d) { if (!d) return '未知'; var parts = d.split('-'); if (parts.length === 3) return parts[0] + '年' + parseInt(parts[1]) + '月' + parseInt(parts[2]) + '日'; return d; }

document.addEventListener('DOMContentLoaded', init);
"""


def generate_html(songs, songs_json_str):
    today = datetime.now().strftime('%Y年%m月%d日')
    total = len(songs)
    today_count = sum(1 for s in songs if s['date'] == datetime.now().strftime('%Y-%m-%d'))

    # Genre stats
    genre_counts = {}
    for s in songs:
        gc = s.get('genre_code', 'other')
        genre_counts[gc] = genre_counts.get(gc, 0) + 1

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍅 番茄音乐报</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/favicon.svg">
<style>{CSS}</style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <div class="header-title"><img src="/favicon.svg" alt="🍅" style="height:1.2rem;vertical-align:middle;margin-right:4px;border-radius:3px">番茄音乐报</div>
    <div class="header-stats">第 {total} 期 · {today} · 共 {total} 首</div>
    <div class="search-box">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input type="text" id="searchInput" placeholder="搜索歌名/歌词..." oninput="onSearch()">
    </div>
  </div>
  <div class="filter-row" id="filterRow"></div>
</header>

<div class="main-content">
  <div id="songContainer"></div>
</div>

<div class="colophon">
  <div class="colophon-title">🍅 番茄音乐报</div>
  <div class="colophon-text">AI 自动生产 · 5 曲风 × 日更 · Powered by violin<br>番茄音乐人成长计划第 3 期</div>
</div>

<!-- Player Bar -->
<div class="player-bar" id="playerBar">
  <div class="player-cover" id="pCover"></div>
  <div class="player-info">
    <div class="player-title" id="pTitle">—</div>
    <div class="player-sub" id="pSub">—</div>
  </div>
  <div class="player-progress">
    <span class="player-time" id="pCur">0:00</span>
    <input type="range" id="pProgress" min="0" max="100" value="0" oninput="audio.currentTime=this.value/100*audio.duration">
    <span class="player-time" id="pDur">0:00</span>
  </div>
  <div class="player-controls">
    <button class="player-btn" onclick="playPrev()">⏮</button>
    <button class="player-btn" id="pPlay" onclick="togglePlay()">▶</button>
    <button class="player-btn" onclick="playNext()">⏭</button>
    <button class="player-btn" id="lyricsBtn" onclick="toggleLyrics()" style="font-size:.7rem">词</button>
  </div>
</div>

<!-- Lyrics Panel -->
<div class="lyrics-panel" id="lyricsPanel"></div>

<script>
var SONGS_DATA = {songs_json_str};
</script>
<script>{JS}</script>
</body>
</html>'''


# ═══ Server ═══════════════════════════════════════════════════════════════════

class TomatoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API endpoints
        if path == '/api/songs':
            self._api_songs()
            return
        if path == '/api/stats':
            self._api_stats()
            return

        # Serve /music/ from MUSIC_DIR
        if path.startswith('/music/'):
            rel = urllib.parse.unquote(path[7:])
            fp = MUSIC_DIR / rel
            if fp.exists() and fp.is_file():
                self._serve_file(fp)
                return
            self._error(404, 'File not found')
            return

        # Serve favicon
        if path == '/favicon.svg':
            fav = BASE / 'favicon.svg'
            if fav.exists():
                self._serve_file(fav)
                return

        # Serve admin
        if path == '/admin' or path == '/admin.html':
            admin_path = BASE / "admin.html"
            if admin_path.exists():
                self._serve_file(admin_path)
                return

        # Default static serving
        super().do_GET()

    def _api_songs(self):
        if not SONGS_JSON.exists():
            self._json({'songs': []})
            return
        with open(SONGS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        songs = [s for s in data.get('songs', []) if not s.get('exclude')]
        self._json({'songs': songs, 'total': len(songs)})

    def _api_stats(self):
        if not SONGS_JSON.exists():
            self._json({'total': 0})
            return
        with open(SONGS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        songs = data.get('songs', [])
        today = datetime.now().strftime('%Y-%m-%d')
        stats = {
            'total': len(songs),
            'today': sum(1 for s in songs if s.get('date') == today),
            'genres': {}
        }
        for s in songs:
            gc = s.get('genre_code', 'other')
            stats['genres'][gc] = stats['genres'].get(gc, 0) + 1
        self._json(stats)

    def _serve_file(self, fp):
        ct = 'application/octet-stream'
        if str(fp).endswith('.html'):
            ct = 'text/html; charset=utf-8'
        elif str(fp).endswith('.mp3'):
            ct = 'audio/mpeg'
        elif str(fp).endswith(('.jpg', '.jpeg')):
            ct = 'image/jpeg'
        elif str(fp).endswith('.png'):
            ct = 'image/png'
        elif str(fp).endswith('.css'):
            ct = 'text/css'
        elif str(fp).endswith('.js'):
            ct = 'application/javascript'
        try:
            with open(fp, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._error(500, str(e))

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(msg.encode('utf-8'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, *a):
        pass


def serve():
    print(f"\n🍅 番茄音乐报 → http://localhost:{PORT}")
    print(f"   管理后台  → http://localhost:{PORT}/admin")
    print(f"   音乐目录: {MUSIC_DIR}")
    print(f"\n   按 Ctrl+C 停止\n")
    import socket
    class ReuseHTTPServer(HTTPServer):
        allow_reuse_address = True
        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            super().server_bind()
    server = ReuseHTTPServer(('0.0.0.0', PORT), TomatoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 已停止")
        server.server_close()


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'serve':
        serve()
    elif cmd == 'build':
        build()
    else:
        if build():
            webbrowser.open(f'http://localhost:{PORT}')
            serve()
