"""番茄 T-A 5首歌词并行创作（Phase 2）

使用 Kimi 2.6 (new-api 网关)，fallback deepseek-v4-flash，超时 90s/首，5 首并发。
"""
import os
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

VAULT = os.path.expanduser("~/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault")
NEWAPI_BASE = "http://192.168.50.78:3003/v1"
NEWAPI_KEY = "eftv7vr0c7yniU5bsBMpqrF5FQqumdcls0AV2z2IxW4jvk2C"

TODAY = "2026-09-08"
TIMEOUT = 90


def call_llm(model, system, user, timeout=90):
    """调用 new-api 网关的 chat completion"""
    url = f"{NEWAPI_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {NEWAPI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.85,
        "max_tokens": 4096
    }
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"]


def write_song(genre_code, song):
    """创作单首歌：先 Kimi 2.6，超时/失败则 fallback deepseek-v4-flash"""
    title = song["title"]
    system = song["system"]
    user = song["user"]
    print(f"[{genre_code}] 《{title}》 开始创作（Kimi 2.6）...")
    t0 = time.time()

    lyrics = None
    model_used = None
    try:
        lyrics = call_llm("kimi-k2.6", system, user, timeout=TIMEOUT)
        model_used = "kimi-k2.6"
        print(f"[{genre_code}] Kimi 2.6 成功 ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"[{genre_code}] Kimi 失败: {e}，切 fallback deepseek-v4-flash")
        try:
            lyrics = call_llm("deepseek-v4-flash", system, user, timeout=TIMEOUT)
            model_used = "deepseek-v4-flash"
            print(f"[{genre_code}] Fallback 成功 ({time.time()-t0:.1f}s)")
        except Exception as e2:
            print(f"[{genre_code}] Fallback 也失败: {e2}")
            return {"code": genre_code, "title": title, "ok": False, "error": str(e2)}

    # 行数统计：只数 [Tag] 之后的纯歌词行
    lines = [l.strip() for l in lyrics.splitlines() if l.strip()]
    lyric_lines = len([l for l in lines if not l.startswith("[") and not l.startswith("（")])
    # 估算时长（按规则：dance 2.8s/行, viral_pop 2.7s/行, sad 3.4s/行, guofeng 4.0s/行, hometown 2.8s/行）
    sec_per_line = {"dance": 2.8, "viral_pop": 2.7, "sad": 3.4, "guofeng": 4.0, "hometown": 2.8}
    bpm = song["bpm"]
    chord = song["chord"]
    return {
        "code": genre_code,
        "title": title,
        "ok": True,
        "lyrics": lyrics,
        "lyric_lines": lyric_lines,
        "model": model_used,
        "bpm": bpm,
        "chord": chord,
        "sec_per_line": sec_per_line[genre_code],
        "elapsed": time.time() - t0
    }


def main():
    with open(os.path.join(VAULT, "data/_ta_lyric_prompts.json"), encoding="utf-8") as f:
        prompts = json.load(f)

    print(f"\n=== Phase 2: 5首歌并行创作 ===")
    t_start = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(write_song, code, song): code for code, song in prompts.items()}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                r = fut.result(timeout=120)
                results[code] = r
            except Exception as e:
                results[code] = {"code": code, "ok": False, "error": str(e)}

    elapsed = time.time() - t_start
    print(f"\n=== 创作完成 总耗时 {elapsed:.1f}s ===")
    for code in ["dance", "viral_pop", "sad", "guofeng", "hometown"]:
        r = results.get(code, {})
        if r.get("ok"):
            ll = r["lyric_lines"]
            est = ll * r["sec_per_line"]
            print(f"  ✅ [{code}] 《{r['title']}》 {ll}行 ~{int(est//60)}:{int(est%60):02d}  model={r['model']}")
        else:
            print(f"  ❌ [{code}] 失败: {r.get('error', '?')}")

    # 保存
    out = {code: r for code, r in results.items()}
    with open(os.path.join(VAULT, "data/_ta_phase2_lyrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已保存 _ta_phase2_lyrics.json")

    return results


if __name__ == "__main__":
    main()
