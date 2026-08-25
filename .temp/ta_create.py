#!/usr/bin/env python3
"""番茄 T-A Phase 2: 并行创作 5 首歌词（Kimi 2.6 → DeepSeek-V4-Pro fallback）"""
import json, os, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

NEWAPI_BASE = "http://192.168.50.78:3003/v1"
NEWAPI_KEY = "eftv7vr0c7yniU5bsBMpqrF5FQqumdcls0AV2z2IxW4jvk2C"
MODEL_MAIN = "kimi-k2.6"
MODEL_FALLBACK = "deepseek-v4-pro"

BANNED_WORDS = "画框、缝补、依归、干涸、禁止项、避让"

GENRES = [
    {
        "title": "大花袄",
        "genre_code": "dance",
        "bpm": 125,
        "chord": "6415",
        "voice": "女声 / 无人声",
        "style_desc": "广场舞 / DJ 舞曲 / 车载慢摇，BPM 125，6415 循环",
        "structure": """[Intro] - 2-3行（节奏感强的短句）
[Verse 1] - 6-8行（场景铺陈：广场/灯光/人群）
[Chorus] - 6-8行（核心洗脑Hook，三字/四字重复为主）
[Verse 2] - 6-8行
[Pre-Chorus] - 2-3行
[Chorus] - 6-8行（重复不变）
[Instrumental] - 标记纯器乐段落（DJ间奏）
[Verse 3] - 4-6行（舞蹈动作描写/互动喊麦）
[Chorus] - 6-8行（Double Chorus：副歌唱两遍）
[Chorus] - 6-8行
[Outro] - 2-3行（渐弱）
总计：≥55行""",
        "theme": "穿大花袄跳广场舞的热闹夜晚，大妈们的自信与快乐，接地气、有画面感",
    },
    {
        "title": "小冤家",
        "genre_code": "viral_pop",
        "bpm": 115,
        "chord": "4536251",
        "voice": "夹子音女声",
        "style_desc": "抖音热歌/口水歌/欢快洗脑，BPM 115，4536251",
        "structure": """[Intro] - 2-3行
[Verse 1] - 6-8行（日常生活场景）
[Pre-Chorus] - 2-3行
[Chorus] - 6-8行（A+A+A+B排比结构！三句相同/相似+一句转折）
[Verse 2] - 6-8行
[Pre-Chorus] - 2-3行
[Chorus] - 6-8行
[Bridge] - 4-6行
[Chorus] - 6-8行（Double Chorus）
[Chorus] - 6-8行
[Outro] - 2-3行
总计：≥55行""",
        "theme": "情侣日常拌嘴打闹的小甜蜜，「小冤家」是亲昵称呼，撒娇式斗嘴，欢快洗脑",
    },
    {
        "title": "旧号码",
        "genre_code": "sad",
        "bpm": 80,
        "chord": "1645",
        "voice": "气声女声 / 哭腔",
        "style_desc": "失恋/孤独/情感共鸣，BPM 80，1645",
        "structure": """[Intro] - 2-3行（雨/夜/空房间意象）
[Verse 1] - 6-8行（直白叙事：分手场景/独处时刻）
[Pre-Chorus] - 2-3行
[Chorus] - 4-6行（核心情绪爆发：想你/放不下/算了吧）
[Verse 2] - 6-8行（回忆对比）
[Pre-Chorus] - 2-3行
[Chorus] - 4-6行
[Bridge] - 4-6行（转折：接受/放下）
[Chorus] - 4-6行
[Outro] - 3-4行
总计：≥50行""",
        "theme": "手机里删不掉的旧号码，深夜想拨又不敢拨，直白表达想念与放不下",
    },
    {
        "title": "念君安",
        "genre_code": "guofeng",
        "bpm": 90,
        "chord": "大调卡农（I→V→VIm→IV→IV→IIIm→II→V）",
        "voice": "戏腔 / 民族女声",
        "style_desc": "民族风/古诗词改编/中国风，BPM 90，大调卡农",
        "structure": """[Intro] - 2-3行（古典意象铺陈）
[Verse 1] - 6-8行（月/楼/风/雪/琴意象）
[Pre-Chorus] - 2-3行
[Chorus] - 4-6行（化用古诗或仿古句式）
[Verse 2] - 6-8行
[Pre-Chorus] - 2-3行
[Chorus] - 4-6行
[Instrumental] - 标记器乐段落（古筝/笛子）
[Bridge] - 4-6行
[Chorus] - 4-6行
[Outro] - 3-4行
总计：≥50行""",
        "theme": "思念远方征人/离人，一句「念君安」是千言万语，用月、楼、风、雪、琴等古典意象",
    },
    {
        "title": "麦田黄了",
        "genre_code": "hometown",
        "bpm": 100,
        "chord": "卡农变体（I→V→VIm→IV→V→I）",
        "voice": "温暖男声 / 民谣女声",
        "style_desc": "乡愁/励志/朴实口语，BPM 100，卡农变体",
        "structure": """[Intro] - 2-3行（村口/老屋/炊烟）
[Verse 1] - 6-8行（童年记忆/妈妈/老屋）
[Pre-Chorus] - 2-3行
[Chorus] - 6-8行（乡愁核心：回家/想念/奋斗）
[Verse 2] - 6-8行（离开家乡/城市打拼）
[Pre-Chorus] - 2-3行
[Chorus] - 6-8行
[Bridge] - 4-6行（励志转折：一定要出人头地）
[Chorus] - 6-8行
[Outro] - 3-4行
总计：≥55行""",
        "theme": "麦收时节想起家乡，妈妈在田埂上等，在城市打拼想家又想出人头地",
    },
]

SYSTEM_PROMPT = """你是番茄音乐平台的职业作词人。番茄音乐的流量密码 = 接地气 × 情绪浓 × 旋律洗脑 × 下沉受众买单。

【番茄歌词铁律】（与诗化歌词完全相反，必须遵守）：
1. 直白表达：鼓励「想你」「放不下」「我爱你」「心好痛」等直白情感词
2. 口语化：用大白话说事，像跟朋友聊天一样
3. 短句重复：副歌核心用三字/四字重复（滴答滴/会不会/想你啦）
4. 排比洗脑：副歌用 A+A+A+B 结构——三句相似 + 一句转折
5. 线性叙事：好懂，时间线清晰，不需要跳跃
6. 不追求留白：该说透就说透，用户要即时共鸣
7. 国风例外：国风古风可用古典意象和仿古句式

【格式铁律】：
- 只允许 [Tag]（如 [Intro]、[Verse 1]、[Chorus]、[Pre-Chorus]、[Bridge]、[Instrumental]、[Outro]）+ 纯歌词行
- 禁止任何括号描述词（禁止（挥手）（喊麦）（DJ drop）这类括号注释，[Instrumental] 段落直接单独一行标记即可）
- 禁止使用这些字词：""" + BANNED_WORDS + """

【行数要求】：严格按给定结构的总行数下限写满，宁可多写不可少写。"""

def call_api(model, prompt, timeout=60):
    resp = requests.post(
        f"{NEWAPI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {NEWAPI_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 4000,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def create_lyrics(genre):
    title = genre["title"]
    prompt = f"""请为番茄音乐平台创作一首歌名为《{title}》的歌词。

【曲风】{genre['style_desc']}
【音色】{genre['voice']}
【主题方向】{genre['theme']}
【歌曲结构】（严格按此结构写满行数）：
{genre['structure']}

要求：
- 整首歌词围绕歌名《{title}》展开，副歌 Hook 里要反复出现歌名
- 副歌用 A+A+A+B 排比洗脑结构（三句相似 + 一句转折）
- 每行一句，短句为主，节奏感强
- 输出只有歌词本身，从 [Intro] 开始，不要任何解释文字"""

    # 尝试主模型
    try:
        return call_api(MODEL_MAIN, prompt), MODEL_MAIN
    except Exception as e:
        print(f"  ⚠️ {title} {MODEL_MAIN} 失败({e.__class__.__name__})，切 fallback")
    # fallback 重试 1 次
    try:
        return call_api(MODEL_FALLBACK, prompt), MODEL_FALLBACK
    except Exception as e:
        print(f"  ⚠️ {title} {MODEL_FALLBACK} 也失败({e.__class__.__name__})")
        raise

def count_lines(lyrics):
    """统计纯歌词行数（去掉 [Tag] 行和空行）"""
    lines = [l.strip() for l in lyrics.splitlines() if l.strip()]
    pure = [l for l in lines if not (l.startswith("[") and l.endswith("]"))]
    return len(lines), len(pure)

def main():
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(create_lyrics, g): g for g in GENRES}
        for fut in as_completed(futures):
            g = futures[fut]
            try:
                lyrics, model = fut.result(timeout=90)
                total, pure = count_lines(lyrics)
                print(f"✅ {g['title']} 完成（{model}）总行 {total} 纯歌词 {pure} 行")
                results.append({**g, "lyrics": lyrics, "model": model})
            except Exception as e:
                print(f"❌ {g['title']} 创作失败: {e}")
                results.append({**g, "lyrics": "", "model": "failed", "error": str(e)})

    with open(os.path.expanduser("~/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault/.temp/ta_created.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n完成 {len(results)} 首，已存 .temp/ta_created.json")

if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"Phase 2 耗时: {time.time()-t0:.0f}s")
