"""Phase 3: 质检 + 提示词生成（番茄 T-A）"""
import json
import os

VAULT = os.path.expanduser("~/Library/Application Support/remio/Users/F2313D5DDFE8FCF316DC1149F06BB14B/agent/tomato-vault")

# 1. 加载歌词
with open(os.path.join(VAULT, "data/_ta_phase2_lyrics.json"), encoding="utf-8") as f:
    lyrics_data = json.load(f)

# === mmx 提示词新格式模板（来自规则文件 tomato-task-ta-rules.md） ===
MMX_TEMPLATES = {
    "dance": "A high-energy Chinese square dance remix at 128 BPM with a four-on-the-floor beat and catchy synth melody. The arrangement features DJ-style bass drops and extended instrumental breaks, leaving generous space between vocal chops. Female vocal phrases are short and repetitive, designed for crowd participation. Full-length song structure with a long intro building anticipation and a long outro fading out gradually.",
    "viral_pop": "A catchy Chinese viral pop song at 115 BPM with a sweet female vocal and a repetitive hook built on a IV-V-IIIm-VIm chord progression. The arrangement is spacious, leaving room between phrases for the earworm melody to breathe. Extended chorus repeats with an A-A-A-B structure create maximum stickiness. Bridge section provides contrast before the final double chorus.",
    "sad": "An emotional Chinese ballad at 80 BPM with a breathy female vocal and gentle crying tone, built on a I-VIm-IV-V chord progression. Piano and strings create a melancholy atmosphere with long instrumental passages. The arrangement is unhurried, giving each emotional phrase room to resonate. Extended outro for a lingering sense of loss.",
    "guofeng": "A Chinese traditional-style pop song at 90 BPM featuring guzheng and dizi, built on a canon chord progression. The arrangement is elegant and atmospheric with extended guzheng solo passages, leaving generous space between vocal lines. An operatic female vocal delivers poetic phrases with unhurried pacing. Long intro establishes the classical mood before the first verse enters.",
    "hometown": "A warm Chinese folk pop song at 100 BPM with a gentle male vocal and acoustic guitar, built on a canon variation progression. The arrangement is nostalgic and uplifting with extended instrumental sections, leaving room between verses for the melody to breathe. Bridge section provides an inspirational turn before the final chorus. Countryside imagery guides the emotional arc."
}

# === Suno 提示词（基于 mmx 模板改写为 Suno 格式） ===
SUNO_TEMPLATES = {
    "dance": "Chinese square dance anthem, 128 BPM, 6415 chord loop, four-on-the-floor beat, catchy synth melody, DJ bass drops, extended instrumental breaks. Female vocal, short repetitive phrases, crowd call-and-response, energetic and euphoric. Full-length track with long intro and outro.",
    "viral_pop": "Chinese viral pop, sweet female vocal, 115 BPM, 4536251 chord progression, catchy earworm melody. Spacious mix with clear vocal. Repetitive A-A-A-B chorus hooks, bridge contrast, double chorus finale. Bright, uplifting, radio-friendly.",
    "sad": "Chinese emotional ballad, 80 BPM, 1645 progression, breathy female vocal with gentle crying tone, piano and strings. Long instrumental passages, unhurried pacing. Melancholic atmosphere with lingering sense of loss in the outro.",
    "guofeng": "Chinese traditional-style pop, 90 BPM, guzheng and dizi, canon progression. Atmospheric guzheng solos, operatic female vocal, poetic phrasing, unhurried pacing. Classical mood from long intro through extended bridges.",
    "hometown": "Chinese folk pop, 100 BPM, gentle male vocal, acoustic guitar, canon variation. Nostalgic and uplifting, extended instrumental sections, inspirational bridge. Countryside imagery with warm, earthy textures."
}

# === 歌词关键意象（用于 cover_prompt 差异化） ===
KEY_IMAGES = {
    "dance": {
        "title_obj": "a giant vintage speaker",
        "scenes": "evening square lit with colorful lights, dancing crowd, DJ booth",
        "mode": "A 雕刻",
        "tone": "warm sunset orange, magenta stage lights, neon glow",
    },
    "viral_pop": {
        "title_obj": "a translucent bubble tea cup",
        "scenes": "milk tea shop counter, two straws, sweet candies, smartphone screen glow",
        "mode": "B 自然",
        "tone": "pastel pink, cream white, candy red, soft warm tones",
    },
    "sad": {
        "title_obj": "a half-empty wine glass",
        "scenes": "rain-streaked window, empty room, scattered photos, cold blue night",
        "mode": "C 构成",
        "tone": "muted blue, gray rain, dim warm lamp glow, melancholy",
    },
    "guofeng": {
        "title_obj": "an ancient bronze mirror",
        "scenes": "moonlit pavilion, silk curtains, falling plum petals, guzheng on a wooden stand",
        "mode": "A 雕刻",
        "tone": "ink-wash black, ivory white, cinnabar red, moonlight silver",
    },
    "hometown": {
        "title_obj": "a rustic wooden rake resting on golden wheat",
        "scenes": "wheat field at sunset, old tile-roof house, rising kitchen smoke, village road",
        "mode": "B 自然",
        "tone": "golden wheat yellow, warm earth brown, sky blue, sunset orange",
    }
}

# === 歌词质检（4 维度） ===
def qa_lyrics(code, title, lyrics):
    """番茄版歌词 4 维质检（按 lyric-qa skill 规则但适配番茄歌词）"""
    lines = [l.strip() for l in lyrics.splitlines() if l.strip() and not l.strip().startswith("[")]
    full = "\n".join(lines)

    # D1 陈词滥调扫描（番茄允许直白，但避免重复套路）
    cliche_patterns = ["我好想你", "心如刀割", "永远", "一生一世", "失去你世界暗了",
                       "转身离去", "独自走在雨中", "泪水模糊"]
    d1_hits = [p for p in cliche_patterns if p in full]
    if not d1_hits:
        d1 = 90
    elif len(d1_hits) <= 2:
        d1 = 78
    else:
        d1 = 55

    # D2 画面感（具体物象/感官词占比）
    visual_words = ["灯", "光", "广场", "音响", "舞", "汗", "鞋", "子", "家",
                    "奶茶", "芋", "手机", "妆", "拖", "外套", "杯", "镜", "窗",
                    "麦", "田", "屋", "妈妈", "村", "烟", "楼", "月", "风", "雪", "琴",
                    "眼", "泪", "手", "心", "花", "雨"]
    visual_count = sum(1 for w in visual_words if w in full)
    d2 = min(95, 60 + visual_count * 2)

    # D3 Hook 强度：核心句重复 + 短句
    title_in_lyrics = full.count(title)
    if title_in_lyrics >= 4:
        d3 = 92
    elif title_in_lyrics >= 2:
        d3 = 80
    else:
        d3 = 65

    # D4 韵律一致性（2026-09-10 补丁：只在 Chorus 段内算，主歌不参与方差评分——
    # 旧行为对全曲行长打分，等于变相奖励主歌碎句，《甜到齁》QA 83 分放行即此漏洞）
    cur = None
    chorus_lines = []
    for l in lyrics.splitlines():
        st = l.strip()
        if st.startswith("["):
            low = st.lower()
            cur = "chorus" if "chorus" in low and "pre" not in low else "other"
            continue
        if cur == "chorus" and st:
            chorus_lines.append(st)
    char_counts = [len(l) for l in chorus_lines]
    variance = max(char_counts) - min(char_counts) if char_counts else 0
    if variance <= 12:
        d4 = 90
    elif variance <= 20:
        d4 = 78
    else:
        d4 = 65

    # D5 碎句检测（2026-09-10 新增，一票否决）：主歌 8-14 字自然句是铁律，
    # 碎句 = 空格断成 ≥2 段且每段 ≤4 字，或去符号后 ≤7 字
    import re
    cur = None
    verse_lines = []
    for l in lyrics.splitlines():
        st = l.strip()
        if st.startswith("["):
            low = st.lower()
            cur = "verse" if "verse" in low or "pre-chorus" in low else "other"
            continue
        if cur == "verse" and st:
            verse_lines.append(st)
    frag = 0
    for st in verse_lines:
        clean = re.sub(r"[^\u4e00-\u9fff]", "", st)
        parts = [p for p in st.split() if re.sub(r"[^\u4e00-\u9fff]", "", p)]
        if (len(parts) >= 2 and max(len(re.sub(r"[^\u4e00-\u9fff]", "", p)) for p in parts) <= 4) or len(clean) <= 7:
            frag += 1
    frag_ratio = frag / len(verse_lines) if verse_lines else 0
    avg_len = sum(len(re.sub(r"[^\u4e00-\u9fff]", "", l)) for l in verse_lines) / len(verse_lines) if verse_lines else 0
    d5_pass = not (frag_ratio > 0.30 or avg_len < 7)
    d5 = 90 if d5_pass else 40

    overall = round(d1 * 0.20 + d2 * 0.30 + d3 * 0.20 + d4 * 0.10 + d5 * 0.20, 1)
    if not d5_pass:
        overall = min(overall, 55)  # 一票否决：碎句超标直接压到及格线下
    return {
        "d1_cliche": d1,
        "d2_vividness": d2,
        "d3_hook": d3,
        "d4_rhyme": d4,
        "d5_fragment": d5,
        "d5_pass": d5_pass,
        "frag_ratio": round(frag_ratio, 2),
        "verse_avg_len": round(avg_len, 1),
        "overall": overall
    }


# === 构造完整数据 ===
songs = []
qa_results = {}
for code in ["dance", "viral_pop", "sad", "guofeng", "hometown"]:
    r = lyrics_data[code]
    title = r["title"]
    lyrics = r["lyrics"]
    bpm = r["bpm"]
    chord = r["chord"]
    model = r["model"]

    # QA
    qa = qa_lyrics(code, title, lyrics)
    qa_results[code] = {"title": title, "qa": qa, "model": model}

    # mmx_prompt 用规则文件中的新格式模板
    mmx_p = MMX_TEMPLATES[code]
    suno_p = SUNO_TEMPLATES[code]

    # cover_prompt 差异化
    ki = KEY_IMAGES[code]
    cover_p = (
        f"A cinematic still life centered on {ki['title_obj']}, "
        f"surrounded by {ki['scenes']}, "
        f"the Chinese characters '{title}' {('etched into a surface in the scene' if ki['mode']=='A 雕刻' else 'naturally appearing as part of the scene' if ki['mode']=='B 自然' else 'formed by elements within the scene')}, "
        f"color palette: {ki['tone']}, "
        f"vertical 9:16 composition suitable for short-video cover, "
        f"highly detailed, soft cinematic lighting, shallow depth of field."
    )

    songs.append({
        "title": title,
        "genre_code": code,
        "lyrics": lyrics,
        "mmx_prompt": mmx_p,
        "suno_prompt": suno_p,
        "cover_prompt": cover_p,
        "bpm": bpm,
        "chord": chord,
        "qa": qa,
        "model": model,
    })

# 保存
with open(os.path.join(VAULT, "data/_ta_qa_results.json"), "w", encoding="utf-8") as f:
    json.dump(qa_results, f, ensure_ascii=False, indent=2)

with open(os.path.join(VAULT, "data/_ta_phase3_songs.json"), "w", encoding="utf-8") as f:
    json.dump(songs, f, ensure_ascii=False, indent=2)

# 输出报告
print("=== 🎵 番茄专项 QA + 提示词报告 ===\n")
labels = {"dance":"广场舞", "viral_pop":"抖音热歌", "sad":"伤感", "guofeng":"国风", "hometown":"家乡"}
for s in songs:
    code = s["genre_code"]
    qa = s["qa"]
    print(f"【{labels[code]}】《{s['title']}》  model={s['model']}  bpm={s['bpm']}  chord={s['chord']}")
    print(f"  D1 陈词滥调: {qa['d1_cliche']} | D2 画面感: {qa['d2_vividness']} | D3 Hook: {qa['d3_hook']} | D4 韵律: {qa['d4_rhyme']} | 综合: {qa['overall']}")
    print(f"  mmx_prompt: {s['mmx_prompt'][:80]}...")
    print(f"  cover_prompt: {s['cover_prompt'][:120]}...")
    print()

print(f"✅ 已保存 _ta_qa_results.json + _ta_phase3_songs.json (5首)")
