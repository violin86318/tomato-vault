#!/usr/bin/env python3
"""5 路并行创作番茄歌词 - Kimi 2.6（绕过代理）"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

NEWAPI_KEY = "eftv7vr0c7yniU5bsBMpqrF5FQqumdcls0AV2z2IxW4jvk2C"
NEWAPI_BASE = "http://192.168.50.78:3003/v1"
PRIMARY_MODEL = "kimi-k2.6"
FALLBACK_MODEL = "deepseek-flash"

# === 五大曲风矩阵 ===
GENRES = {
    "dance": {
        "title": "村头大喇叭",
        "bpm": 128,
        "chord": "6415",
        "template": "dance",
        "lyric_direction": "广场舞/DJ舞曲/车载慢摇。极简重复，可纯音乐。女声/无人声。",
        "structure": """[Intro] 2-3行
[Verse 1] 6-8行（场景铺陈：村口大喇叭/广场/灯光/人群，8-14字自然句）
[Pre-Chorus] 2-3行
[Chorus] 6-8行（核心洗脑Hook，三字/四字重复为主）
[Verse 2] 6-8行
[Pre-Chorus] 2-3行
[Chorus] 6-8行（重复不变）
[Instrumental] - 标记纯器乐段落（DJ间奏）
[Verse 3] 4-6行（新增：舞蹈动作描写/互动喊麦）
[Chorus] 6-8行（Double Chorus：副歌唱两遍）
[Chorus] 6-8行
[Outro] 2-3行（渐弱）
总计：≥55行（⚠️ 广场舞节奏快，每行只值~2.8秒，必须多写才能撑够时长）"""
    },
    "viral_pop": {
        "title": "吃醋啦",
        "bpm": 115,
        "chord": "4536251",
        "template": "viral_pop",
        "lyric_direction": "抖音热歌/口水歌/欢快洗脑。短句三字重复，A+A+A+B。夹子音女声。",
        "structure": """[Intro] 2-3行
[Verse 1] 6-8行（日常生活场景：女友吃醋的具体动作：翻手机/叉腰/嘟嘴/审问，8-14字自然句）
[Pre-Chorus] 2-3行
[Chorus] 6-8行（A+A+A+B排比结构！三句相同/相似+一句转折）
[Verse 2] 6-8行
[Pre-Chorus] 2-3行
[Chorus] 6-8行
[Bridge] 4-6行
[Chorus] 6-8行（Double Chorus）
[Chorus] 6-8行
[Outro] 2-3行
总计：≥55行"""
    },
    "sad": {
        "title": "戒不掉",
        "bpm": 80,
        "chord": "1645",
        "template": "sad",
        "lyric_direction": "失恋/孤独/情感共鸣。直白情绪。气声女声/哭腔。",
        "structure": """[Intro] 2-3行（雨/夜/空房间意象）
[Verse 1] 6-8行（直白叙事：分手场景/独处时刻，戒不掉的具体表现，8-14字自然句）
[Pre-Chorus] 2-3行
[Chorus] 4-6行（核心情绪爆发：戒不掉/放不下/还是想你）
[Verse 2] 6-8行（回忆对比：戒不掉看聊天记录、戒不掉偷看朋友圈）
[Pre-Chorus] 2-3行
[Chorus] 4-6行
[Bridge] 4-6行（转折：接受/放下/或戒不掉一辈子）
[Chorus] 4-6行
[Outro] 3-4行
总计：≥50行"""
    },
    "guofeng": {
        "title": "青石巷",
        "bpm": 90,
        "chord": "大调卡农",
        "template": "guofeng",
        "lyric_direction": "民族风/古诗词改编/中国风。古典意象（月/楼/风/雪/琴）。戏腔/民族女声。",
        "structure": """[Intro] 2-3行（古典意象铺陈：青石板/油纸伞/苔痕）
[Verse 1] 6-8月/楼/风/雪/琴意象，8-14字仿古句式）
[Pre-Chorus] 2-3行
[Chorus] 4-6行（化用古诗或仿古句式）
[Verse 2] 6-8行
[Pre-Chorus] 2-3行
[Chorus] 4-6行
[Instrumental] - 标记器乐段落（古筝/笛子）
[Bridge] 4-6行
[Chorus] 4-6行
[Outro] 3-4行
总计：≥50行"""
    },
    "hometown": {
        "title": "山路弯弯",
        "bpm": 100,
        "chord": "卡农变体",
        "template": "hometown",
        "lyric_direction": "乡愁/励志/朴实口语。地名+亲情。温暖男声/民谣女声。",
        "structure": """[Intro] 2-3行（山路弯弯/村口/老屋）
[Verse 1] 6-8行（童年记忆/娘送到村口山路弯弯的场景，8-14字自然句）
[Pre-Chorus] 2-3行
[Chorus] 6-8行（乡愁核心：山路弯弯/还是那条路）
[Verse 2] 6-8行（离开家乡/城市打拼/梦里山路弯弯）
[Pre-Chorus] 2-3行
[Chorus] 6-8行
[Bridge] 4-6行（励志转折：一定要出人头地）
[Chorus] 6-8行
[Outro] 3-4行
总计：≥55行"""
    }
}

# 通用 D5 碎句铁律提示
D5_RULE = """
⛔ **句式范围铁律（2026-09-10 必读）**：
- 短句重复（三字/四字/2-3字）**仅限副歌 Hook**
- [Verse] / [Pre-Chorus] / [Bridge] 主歌必须用 **8-14 字自然叙事句**
- 禁止把主歌写成 3+3 空格碎句（如「电话响一声 我就心跳加速」式只允许作为语气点缀，**主歌大部分行须是完整句**）
- 主歌行均长 <7 字或 ≤7 字行占比 >40% = 不合格，必须重写主歌
"""

LYRICS_PROMPT_TEMPLATE = """你是番茄音乐平台歌词创作师，为下沉受众写接地气、情绪外放、洗脑的歌词。

**任务**：为「{genre}」曲风写一首完整歌词，歌名：《{title}》。

**曲风**：{direction}

**结构要求（必须严格按此结构与行数）**：
{structure}

**番茄歌词审核规则**（反转版，禁止诗化）：
1. 直白表达：鼓励「想你」「放不下」「我爱你」「心好痛」等直白情感词
2. 口语化：像跟朋友聊天
3. 短句重复：**仅限副歌核心**用三字/四字重复（滴答滴/会不会/想你啦）
4. 排比洗脑：副歌 A+A+A+B 结构（三句相似+一句转折）
5. 线性叙事：好懂，不跳跃
6. 不追求留白：该说透就说透
{D5_RULE}

**输出格式要求（严格遵守）**：
- 只输出歌词，不要任何解释或描述
- 只允许 `[Tag]` + 纯歌词，禁止括号描述词
- 禁止发音黑名单：画框、缝补、依归、干涸、禁止项、避让
- 每个 Tag 后换行，每行一句歌词
- 行数必须达到上述结构要求的下限
"""

def call_newapi(model, system_prompt, user_prompt, timeout=150):
    """调用 new-api 网关 - 绕过代理"""
    url = f"{NEWAPI_BASE}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.9,
        "max_tokens": 4000,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NEWAPI_KEY}",
        },
        method="POST",
    )
    # ⛔ 绕过代理（urllib）
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    resp = opener.open(req, timeout=timeout)
    result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def write_one_lyrics(genre_code, genre_info):
    """创作一首歌词，带 fallback"""
    user_prompt = LYRICS_PROMPT_TEMPLATE.format(
        genre=genre_info["template"],
        title=genre_info["title"],
        direction=genre_info["lyric_direction"],
        structure=genre_info["structure"],
        D5_RULE=D5_RULE,
    )
    system_prompt = "你是番茄音乐平台歌词创作师，写接地气、情绪外放、洗脑的歌词。"
    
    # 主用 kimi-k2.6
    try:
        print(f"  [{genre_code}] kimi-k2.6 创作中...")
        t0 = time.time()
        result = call_newapi(PRIMARY_MODEL, system_prompt, user_prompt, timeout=150)
        elapsed = time.time() - t0
        print(f"  [{genre_code}] ✅ kimi 完成 ({elapsed:.1f}s)")
        return result, PRIMARY_MODEL
    except Exception as e:
        print(f"  [{genre_code}] ⚠️ kimi 失败: {type(e).__name__}: {str(e)[:200]}")
    
    # Fallback deepseek-flash
    try:
        print(f"  [{genre_code}] deepseek-flash fallback 中...")
        t0 = time.time()
        result = call_newapi(FALLBACK_MODEL, system_prompt, user_prompt, timeout=150)
        elapsed = time.time() - t0
        print(f"  [{genre_code}] ✅ deepseek 完成 ({elapsed:.1f}s)")
        return result, FALLBACK_MODEL
    except Exception as e:
        print(f"  [{genre_code}] ❌ deepseek 也失败: {type(e).__name__}: {str(e)[:200]}")
        return None, None


def main():
    print(f"🚀 启动 5 路并行创作...")
    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(write_one_lyrics, code, info): code
            for code, info in GENRES.items()
        }
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                lyrics, model = fut.result(timeout=180)
                results[code] = {"lyrics": lyrics, "model": model}
            except Exception as e:
                print(f"  [{code}] ❌ Future 异常: {e}")
                results[code] = {"lyrics": None, "model": None}
    
    # 输出到临时 JSON
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/_ta_phase2_lyrics_today.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📝 歌词写入: {out_path}")
    
    # 输出每首行数
    for code, info in GENRES.items():
        lyrics = results.get(code, {}).get("lyrics")
        if lyrics:
            pure_lines = [l for l in lyrics.splitlines() if l.strip() and not l.strip().startswith("[") or (l.strip().startswith("[") and "]" in l)]
            pure_lines = [l for l in lyrics.splitlines() if l.strip()]
            print(f"  [{code}] {info['title']}: {len(pure_lines)} 行 (model={results[code]['model']})")
        else:
            print(f"  [{code}] ❌ 无歌词")


if __name__ == "__main__":
    main()
