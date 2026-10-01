"""番茄 T-A 并行创作 5 首歌词

⛔ 网络铁律：所有 new-api 请求必须 proxies={"http": None, "https": None} 显式绕过本机代理
⛔ 单首超时 150s，fallback deepseek-flash 重试 1 次
"""
import json
import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

VAULT = "/Users/wanglingwei/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault"
NEWAPI_BASE = "http://192.168.50.78:3003/v1"
NEWAPI_KEY = "eftv7vr0c7yniU5bsBMpqrF5FQqumdcls0AV2z2IxW4jvk2C"
NO_PROXY = {"http": None, "https": None}

# 今日选题
TODAY = {
    "dance":     ("摇到天亮", "广场舞/DJ舞曲/车载慢摇", 128, "6415"),
    "viral_pop": ("心动砰砰", "抖音热歌/口水歌/欢快洗脑", 115, "4536251"),
    "sad":       ("好久不见", "失恋/孤独/情感共鸣", 80, "1645"),
    "guofeng":   ("声声慢", "民族风/古诗词改编/中国风", 90, "大调卡农"),
    "hometown":  ("妈妈的针线", "乡愁/励志/朴实口语", 100, "卡农变体"),
}

# 各曲风详细 prompt 模板
GENRE_INSTRUCTIONS = {
    "dance": """【广场舞/DJ舞曲/车载慢摇】（BPM 128，和弦 6415 循环）
结构模板（≥55行）：
- [Intro] 2-3行（节奏感强的短句）
- [Verse 1] 6-8行（场景铺陈：广场/灯光/人群）
- [Chorus] 6-8行（核心洗脑 Hook，三字/四字重复）
- [Verse 2] 6-8行
- [Pre-Chorus] 2-3行
- [Chorus] 6-8行（重复不变）
- [Instrumental] 标记纯器乐段落
- [Verse 3] 4-6行（新增：舞蹈动作描写/互动喊麦）
- [Chorus] 6-8行（Double Chorus）
- [Chorus] 6-8行
- [Outro] 2-3行（渐弱）""",

    "viral_pop": """【抖音热歌/口水歌/欢快洗脑】（BPM 115，和弦 4536251 循环）
结构模板（≥55行）：
- [Intro] 2-3行
- [Verse 1] 6-8行（日常生活场景）
- [Pre-Chorus] 2-3行
- [Chorus] 6-8行（A+A+A+B 排比结构）
- [Verse 2] 6-8行
- [Pre-Chorus] 2-3行
- [Chorus] 6-8行
- [Bridge] 4-6行
- [Chorus] 6-8行（Double Chorus）
- [Chorus] 6-8行
- [Outro] 2-3行""",

    "sad": """【失恋/孤独/情感共鸣】（BPM 80，和弦 1645 循环）
结构模板（≥50行）：
- [Intro] 2-3行（雨/夜/空房间意象）
- [Verse 1] 6-8行（直白叙事：分手场景/独处时刻）
- [Pre-Chorus] 2-3行
- [Chorus] 4-6行（核心情绪爆发：想你/放不下/算了吧）
- [Verse 2] 6-8行（回忆对比）
- [Pre-Chorus] 2-3行
- [Chorus] 4-6行
- [Bridge] 4-6行（转折：接受/放下）
- [Chorus] 4-6行
- [Outro] 3-4行""",

    "guofeng": """【民族风/古诗词改编/中国风】（BPM 90，和弦 大调卡农）
结构模板（≥50行）：
- [Intro] 2-3行（古典意象铺陈）
- [Verse 1] 6-8行（月/楼/风/雪/琴意象，仿古句式）
- [Pre-Chorus] 2-3行
- [Chorus] 4-6行（化用古诗或仿古句式）
- [Verse 2] 6-8行
- [Pre-Chorus] 2-3行
- [Chorus] 4-6行
- [Instrumental] 标记器乐段落（古筝/笛子）
- [Bridge] 4-6行
- [Chorus] 4-6行
- [Outro] 3-4行""",

    "hometown": """【乡愁/励志/朴实口语】（BPM 100，和弦 卡农变体）
结构模板（≥55行）：
- [Intro] 2-3行（村口/老屋/炊烟）
- [Verse 1] 6-8行（童年记忆/妈妈/老屋）
- [Pre-Chorus] 2-3行
- [Chorus] 6-8行（乡愁核心：回家/想念/奋斗）
- [Verse 2] 6-8行（离开家乡/城市打拼）
- [Pre-Chorus] 2-3行
- [Chorus] 6-8行
- [Bridge] 4-6行（励志转折：一定要出人头地）
- [Chorus] 6-8行
- [Outro] 3-4行""",
}

# 通用铁律（番茄音乐风格）
GLOBAL_RULES = """【番茄音乐歌词铁律 ⛔ 必读】

1. ⛔ **句式范围铁律（最关键）**：
   - **短句重复仅限副歌 Hook**：[Verse]/[Pre-Chorus]/[Bridge] 主歌必须用 **8-14 字自然叙事句**！
   - 禁止把主歌写成"电话响一声 我就心跳加速"式 3+3 空格碎句堆砌（每段 ≤4 字）
   - 主歌行均长 <7 字 或 ≤7 字行占比 >40% = 不合格打回
   - 主歌必须写出完整句子，像日常叙事（8-14 字）

2. ⛔ **直白口语**：用大白话说事，可以写"想你/放不下/我爱你/心好痛"

3. ⛔ **副歌用 A+A+A+B 排比结构**：三句相同/相似 + 一句转折收束

4. ⛔ **格式**：只允许 [Tag] + 纯歌词，禁止括号描述词

5. ⛔ **禁止发音黑名单**：画框、缝补、依归、干涸、禁止项、避让

6. ⛔ **国风例外**：可用古典意象（月/楼/风/雪/琴）和仿古句式，但副歌必须可记可唱

7. ⛔ **时长**：广场舞/洗脑情歌/家乡励志 ≥55行，伤感/国风 ≥50行
"""


def call_lyrics_api(model: str, system_prompt: str, user_prompt: str, timeout: int = 150):
    """调 new-api 创作歌词（绕代理）"""
    headers = {
        "Authorization": f"Bearer {NEWAPI_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.85,
        "max_tokens": 4096,
    }
    resp = requests.post(
        f"{NEWAPI_BASE}/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout,
        proxies=NO_PROXY,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return text


def make_prompt(genre_code: str, title: str, desc: str) -> tuple:
    """构造 system + user prompt"""
    instr = GENRE_INSTRUCTIONS[genre_code]
    system = f"""你是一位番茄音乐平台（下沉受众）的歌词创作人，专攻口水歌/广场舞/洗脑情歌/伤感/国风/家乡题材。

{GLOBAL_RULES}

【本次任务】{instr}

【核心提醒】短句重复只允许在 [Chorus] 副歌段！[Verse]/[Pre-Chorus]/[Bridge] 必须是 8-14 字完整叙事句，禁止 3+3 空格碎句堆砌！

【输出要求】
- 仅输出歌词正文，从 [Intro] 开始，[Outro] 结束
- 每行结尾换行
- 不要解释、不要前言、不要标题外的任何文字
- 严格遵守 ≥50 行 或 ≥55 行 的最低行数要求
"""
    user = f"""请为番茄音乐平台创作一首【{title}】（{desc}）。

要求：
1. 严格遵守 system 中的句式铁律——主歌必须 8-14 字自然叙事句，碎句仅限副歌 Hook
2. 必须达到对应曲风的行数要求
4. 歌词整体可记可唱，下沉受众听完能在超市哼出来

请直接输出歌词正文："""
    return system, user


def create_one(genre_code: str, title: str, desc: str, bpm: int, chord: str):
    """创作一首：先 kimi，超时/异常 fallback 到 deepseek-flash"""
    system, user = make_prompt(genre_code, title, desc)

    # 第一次：kimi-k2.6
    t0 = time.time()
    lyrics = None
    err = None
    model_used = None
    try:
        lyrics = call_lyrics_api("kimi-k2.6", system, user, timeout=150)
        model_used = "kimi-k2.6"
        elapsed = time.time() - t0
        print(f"  [{genre_code}] kimi-k2.6 OK ({elapsed:.1f}s) {title}")
    except Exception as e1:
        err = f"kimi: {type(e1).__name__}: {str(e1)[:150]}"
        print(f"  [{genre_code}] kimi 失败 → 切 deepseek-flash: {err}")
        # Fallback: deepseek-flash
        try:
            t1 = time.time()
            lyrics = call_lyrics_api("deepseek-flash", system, user, timeout=150)
            model_used = "deepseek-flash"
            elapsed = time.time() - t0
            print(f"  [{genre_code}] deepseek-flash OK ({elapsed:.1f}s) {title}")
        except Exception as e2:
            err += f" | deepseek: {type(e2).__name__}: {str(e2)[:150]}"
            print(f"  [{genre_code}] ❌ 双双失败: {err}")

    return {
        "genre_code": genre_code,
        "title": title,
        "desc": desc,
        "bpm": bpm,
        "chord": chord,
        "lyrics": lyrics,
        "model": model_used,
        "error": err,
    }


def main():
    print(f"⏱️ T={time.time():.1f} 启动 5 首并行创作\n")

    songs = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {
            ex.submit(create_one, gc, t, d, bpm, chord): gc
            for gc, (t, d, bpm, chord) in TODAY.items()
        }
        for future in as_completed(futures):
            genre = futures[future]
            try:
                result = future.result(timeout=200)
                songs.append(result)
            except Exception as e:
                print(f"  [{genre}] 任务异常: {e}")
                songs.append({
                    "genre_code": genre,
                    "title": TODAY[genre][0],
                    "desc": TODAY[genre][1],
                    "bpm": TODAY[genre][2],
                    "chord": TODAY[genre][3],
                    "lyrics": None,
                    "model": None,
                    "error": str(e),
                })

    print(f"\n⏱️ T={time.time():.1f} 全部完成")
    print(f"\n{'='*60}")
    print("产出汇总:")
    for s in songs:
        if s.get("lyrics"):
            lines = [l for l in s["lyrics"].split("\n") if l.strip() and not l.strip().startswith("[")]
            print(f"  ✅ {s['genre_code']:12s} | {s['title']:8s} | {s['model']:18s} | 纯歌词 {len(lines)} 行")
        else:
            print(f"  ❌ {s['genre_code']:12s} | {s['title']:8s} | 失败: {s.get('error', '?')[:80]}")

    # 保存到 phase2 中间文件
    out_path = f"{VAULT}/data/_ta_phase2_lyrics_today.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"songs": songs, "ts": time.time()}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 写到 {out_path}")


if __name__ == "__main__":
    main()