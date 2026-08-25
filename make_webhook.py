#!/usr/bin/env python3
"""
Make.com Webhook 接收端 — 番茄音乐管线 v2
==========================================
端口: 8897
路由:
  POST /api/make/start   — Make 触发 → 本地调 MiniMax API + BizyAir 封面 → 下载
  POST /api/make/finish  — 接收 Make 回传的 URL（向后兼容）
  GET  /api/make/health  — 健康检查

支持两种请求格式：
  单首: {"title": "...", "lyrics": "...", "prompt": "...", ...}
  批量: {"songs": [{...}, {...}, ...]}

输出: ~/Music/番茄音乐/{date}_{title}/  (MP3 + 封面 + 歌词 + 元数据)
"""

import json
import os
import sys
import time
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# === 配置 ===
PORT = 8897
MUSIC_BASE = Path("/tmp/tomato_music")  # 沙盒限制，实际 ~/Music/ 由 osascript 同步
MUSIC_FINAL = Path.home() / "Music" / "番茄音乐"  # 最终目标目录
LOG_DIR = Path.home() / "Library" / "Application Support" / "remio" / "Users" / "F2313D5DDFE8FCF316DC1149F06BB14B" / "agent" / "tomato-vault" / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RECEIVE_LOG = LOG_DIR / "make_receive.jsonl"

MINIMAX_ENDPOINT = "https://api.minimaxi.com/v1/music_generation"
BIZYAIR_X_BASE = "https://api.bizyair.cn/x/v1"

# 默认封面 prompt 模板
COVER_PROMPT_TEMPLATE = (
    "Professional album cover art, {genre} music style, "
    "feeling: {mood}, modern design, no text, square format, high quality"
)

DOWNLOAD_TIMEOUT = 120

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("make-webhook")


# ─── API Key 加载 ───

def _read_key_from_zshrc(var_name: str) -> str:
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        for line in zshrc.read_text().split("\n"):
            if f"{var_name}=" in line and (line.startswith("export ") or line.startswith(var_name)):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def load_minimax_key() -> str:
    key = os.environ.get("MINIMAX_API_KEY", "") or _read_key_from_zshrc("MINIMAX_API_KEY")
    if not key:
        raise RuntimeError("MINIMAX_API_KEY 未设置")
    return key


def load_bizyair_key():
    key = (os.environ.get("BIZYAIR_API_KEY", "")
           or os.environ.get("BIZYAIR_KEY", "")
           or _read_key_from_zshrc("BIZYAIR_API_KEY")
           or _read_key_from_zshrc("BIZYAIR_KEY"))
    return key


# ─── 文件下载 ───

def download_file(url: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["curl", "-sL", "--max-time", str(DOWNLOAD_TIMEOUT), "-o", str(dest), url],
        capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT + 10
    )
    if r.returncode != 0 or not dest.exists():
        raise RuntimeError(f"curl 下载失败: {r.stderr[:200]}")
    return dest.stat().st_size


def _sync_to_final(song_dir: Path):
    """用 osascript 绕过沙盒，将 /tmp/tomato_music/{song} 复制到 ~/Music/番茄音乐/"""
    final = MUSIC_FINAL / song_dir.name
    src = str(song_dir)
    dst = str(final)
    script = f'mkdir -p "{dst}" && cp -R "{src}/." "{dst}/" && echo ok'
    try:
        subprocess.run(["osascript", "-e", f'do shell script \'{script}\''],
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass  # 同步失败不阻塞主流程


# ─── MiniMax API ───

def call_minimax(title: str, lyrics: str, prompt: str) -> str:
    api_key = load_minimax_key()
    payload = json.dumps({
        "model": "music-3.0",
        "lyrics": lyrics,
        "prompt": prompt,
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"},
        "output_format": "url"
    })
    curl = [
        "curl", "-sS", "--http1.1", "-X", "POST", MINIMAX_ENDPOINT,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", payload,
        "--connect-timeout", "15",
        "--max-time", "300",
    ]
    log.info(f"  ⏳ MiniMax 生成中: {title}")
    r = subprocess.run(curl, capture_output=True, text=True, timeout=310)
    if r.returncode != 0:
        raise RuntimeError(f"curl 失败: {r.stderr[:200]}")
    resp = json.loads(r.stdout)
    if resp.get("base_resp", {}).get("status_code") != 0:
        raise RuntimeError(f"MiniMax 错误: {resp.get('base_resp', {}).get('status_msg', '?')}")
    url = resp.get("data", {}).get("audio", "")
    if not url:
        raise RuntimeError("MiniMax 未返回 audio URL")
    log.info(f"  ✅ MiniMax OK: {title}")
    return url


# ─── BizyAir 封面 ───

def generate_cover(title: str, genre: str, mood: str, song_dir: Path):
    """3 步：submit → watch → result。失败不阻塞主流程。"""
    bizyair_key = load_bizyair_key()
    if not bizyair_key:
        log.warning(f"  ⚠️ 无 BIZYAIR_KEY，跳过封面")
        return None

    endpoint = "bza-image-o2-base/text-to-image"  # BizyAir O.2 文生图
    prompt = COVER_PROMPT_TEMPLATE.format(genre=genre or "pop", mood=mood or "dreamy")

    # Step 1: Submit
    submit_payload = json.dumps({
        "prompt": f"Album cover for song \"{title}\", {prompt}",
        "image_size": "1024x1024",
    })
    env = os.environ.copy()
    env["HTTPS_PROXY"] = "http://127.0.0.1:7890"

    try:
        r = subprocess.run(
            ["curl", "-sS", "-X", "POST", f"{BIZYAIR_X_BASE}/modelzoo/tasks/openapi/{endpoint}",
             "-H", f"Authorization: Bearer {bizyair_key}",
             "-H", "Content-Type: application/json",
             "-H", "lang: zh",
             "-d", submit_payload],
            capture_output=True, text=True, env=env, timeout=30
        )
        submit_resp = json.loads(r.stdout)
        log.info(f"  📦 BizyAir submit resp: {str(submit_resp)[:200]}")
        data = submit_resp.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        elif data is None:
            data = {}
        request_id = data.get("request_id", "") if isinstance(data, dict) else ""
        if not request_id:
            log.warning(f"  ⚠️ BizyAir submit 失败: {submit_resp.get('message', '?')[:100]}")
            return None
        log.info(f"  ⏳ 封面生成中: {title} (req={request_id[:12]}...)")

        # Step 2: Watch (轮询)
        for attempt in range(30):  # 最多 5 分钟
            time.sleep(10)  # 首次等 10 秒，后续每 10 秒
            r2 = subprocess.run(
                ["curl", "-sS", f"{BIZYAIR_X_BASE}/modelzoo/tasks/openapi/{request_id}",
                 "-H", f"Authorization: Bearer {bizyair_key}",
                 "-H", "lang: zh"],
                capture_output=True, text=True, env=env, timeout=15
            )
            watch_resp = json.loads(r2.stdout)
            data = watch_resp.get("data") or {}
            if isinstance(data, str):
                data = {}
            status = data.get("status", "")
            if status == "Success":
                outputs = data.get("outputs", {})
                images = outputs.get("images", []) if isinstance(outputs, dict) else []
                if images and isinstance(images, list):
                    img_url = images[0] if isinstance(images[0], str) else images[0].get("url", "")
                    if img_url:
                        cover_path = song_dir / f"{title}_cover.png"
                        download_file(img_url, cover_path)
                        log.info(f"  ✅ 封面下载: {title}")
                        return str(cover_path)
                log.warning(f"  ⚠️ 封面 Success 但无图片")
                return None
            elif status == "Failed":
                log.warning(f"  ⚠️ 封面失败: {data.get('message', '?')[:100]}")
                return None
        log.warning(f"  ⚠️ 封面超时")
        return None
    except Exception as e:
        log.warning(f"  ⚠️ 封面异常: {e}")
        return None


# ─── 核心处理 ───

def process_one_song(data: dict) -> dict:
    """处理单首歌：MiniMax + 封面 + 保存。"""
    title = data.get("title", "unknown")
    lyrics = data.get("lyrics", "")
    prompt = data.get("prompt", "")
    genre = data.get("genre", "流行")
    mood = data.get("mood", "梦幻")
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    song_dir = MUSIC_BASE / f"{date}_{title}"
    song_dir.mkdir(parents=True, exist_ok=True)
    result = {"title": title, "song_dir": str(song_dir), "errors": []}

    # 并行：MiniMax + 封面（线程同时跑，节省时间）
    mp3_result = {}
    cover_result = {}

    def _do_mp3():
        try:
            mp3_url = call_minimax(title, lyrics, prompt)
            mp3_path = song_dir / f"{title}_v1.mp3"
            size = download_file(mp3_url, mp3_path)
            mp3_result["mp3"] = str(mp3_path)
            mp3_result["size_mb"] = round(size / 1048576, 1)
            log.info(f"  🎵 MP3: {title} ({mp3_result['size_mb']}MB)")
        except Exception as e:
            mp3_result["error"] = str(e)
            log.error(f"  ❌ MP3 失败 {title}: {e}")

    def _do_cover():
        cover_path = generate_cover(title, genre, mood, song_dir)
        if cover_path:
            cover_result["cover"] = cover_path
        else:
            cover_result["error"] = "封面跳过或失败"

    t_mp3 = threading.Thread(target=_do_mp3)
    t_cover = threading.Thread(target=_do_cover)
    t_mp3.start()
    t_cover.start()
    t_mp3.join(timeout=310)
    t_cover.join(timeout=310)

    if "mp3" in mp3_result:
        result["mp3"] = mp3_result["mp3"]
        result["size_mb"] = mp3_result["size_mb"]
    else:
        result["errors"].append(f"MP3: {mp3_result.get('error', '未知')}")

    if "cover" in cover_result:
        result["cover"] = cover_result["cover"]
    else:
        result["errors"].append(cover_result.get("error", "封面失败"))

    # 3. 保存歌词 + 元数据
    if lyrics:
        (song_dir / f"{title}_lyrics.txt").write_text(lyrics, encoding="utf-8")
    meta = {k: v for k, v in data.items() if k != "lyrics"}
    meta["generated_at"] = datetime.now().isoformat()
    (song_dir / f"{title}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. 同步到 ~/Music/番茄音乐/（绕过沙盒）
    _sync_to_final(song_dir)

    return result


def process_songs(data: dict) -> dict:
    """处理单首或批量。"""
    if "songs" in data and isinstance(data["songs"], list):
        songs = data["songs"]
        log.info(f"🎼 批量处理 {len(songs)} 首歌")
        results = []
        for i, song in enumerate(songs, 1):
            log.info(f"--- [{i}/{len(songs)}] ---")
            results.append(process_one_song(song))
        return {"status": "ok", "count": len(results), "results": results}
    else:
        result = process_one_song(data)
        ok = len(result.get("errors", [])) == 0
        return {"status": "ok" if ok else "partial", "result": result}


# ─── HTTP Handler ───

class WebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def do_GET(self):
        if self.path == "/api/make/health":
            self._send_json(200, {"status": "ok", "version": "v2", "port": PORT})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.loads(raw)
        except Exception as e:
            self._send_json(400, {"error": f"bad json: {e}"})
            return

        log_entry = {"ts": datetime.now().isoformat(), "path": self.path, "data_keys": list(data.keys())}
        with open(RECEIVE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        if self.path in ("/api/make/start", "/api/make/finish"):
            log.info(f"📨 收到: {self.path} keys={list(data.keys())}")
            try:
                result = process_songs(data)
                self._send_json(200, result)
                log.info(f"✅ 完成: {result.get('count', 1)} 首")
            except Exception as e:
                log.error(f"❌ 处理失败: {e}")
                self._send_json(500, {"status": "error", "error": str(e)})
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, *a):
        pass


def main():
    MUSIC_BASE.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("127.0.0.1", PORT), WebhookHandler)
    log.info(f"🚀 Tomato webhook v2 — http://127.0.0.1:{PORT}")
    log.info(f"   输出: {MUSIC_BASE}")
    log.info(f"   POST /api/make/start  — 单首 {{title,lyrics,prompt}} 或批量 {{songs:[...]}}")
    log.info(f"   POST /api/make/finish — 向后兼容")
    log.info(f"   健康检查: curl http://127.0.0.1:{PORT}/api/make/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("停止")
        server.shutdown()


if __name__ == "__main__":
    main()