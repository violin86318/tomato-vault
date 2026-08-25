# 🍅 PRD v2：番茄音乐每日自动化 — n8n 全自治方案

> 版本：v2.0 | 日期：2026-06-17 | 状态：待确认
> 核心变更：**完全在 NAS920 运行，Mac 零参与，不需要 mmx/make_webhook.py/LRC**

---

## 一、一句话方案

n8n 原生 HTTP Request 节点直接调 4 个云 API（DeepSeek + MiniMax + BizyAir + Telegram），文件落地 NAS，网站在容器内构建。**一条工作流跑完全程，预计 3-5 分钟**。

---

## 二、现有环节 → n8n 映射

| 环节 | 现有实现 | n8n 方案 | 改造量 |
|------|---------|---------|:------:|
| ① 歌词创作 | remio scheduler → DeepSeek | **HTTP Request 节点直调 DeepSeek API** | 零 |
| ② MP3 生成 | mmx CLI / make_webhook.py | **HTTP Request 节点直调 MiniMax API** | 零 |
| ③ 封面生成 | make_webhook.py → BizyAir | **HTTP Request submit → Loop poll → Write File** | 零 |
| ④ 文件下载 | curl in Python | **n8n Write Binary File 节点** | 零 |
| ⑤ 网站构建 | build.py + vault.py (Python) | **容器内 Execute Command 调 Python** | 改 2 处 |
| ⑥ LRC 对齐 | Mac mini M2 ForcedAligner | **❌ 取消** | — |
| ⑦ Telegram 通知 | remio agent | **HTTP Request 节点直调 Bot API** | 零 |

**结论**：只有网站构建需要改造（`afinfo`→`ffprobe`，路径映射），其余全部 n8n 原生节点。

---

## 三、架构图

```
┌──────────────────────────────────────────────────────┐
│         n8n @ NAS920 (单工作流, 全自治)               │
│                                                       │
│  ┌─ Schedule 08:00 CST                               │
│  │                                                    │
│  ├─ HTTP Request → DeepSeek API (创作5首歌词+提示词)   │
│  │    ↳ model: deepseek-chat                          │
│  │    ↳ system prompt: 番茄曲风矩阵 + 词规            │
│  │                                                    │
│  ├─ Code (解析歌词 JSON, 分配曲风)                    │
│  │                                                    │
│  ├─ Split In Batches (5首并行) ─────────────────┐    │
│  │   每首同时:                                    │    │
│  │   ├─ HTTP → MiniMax API (/v1/music_generation)│    │
│  │   │   → 返回 MP3 URL                          │    │
│  │   │   → Write Binary File → /volume1/tomato/  │    │
│  │   │                                            │    │
│  │   └─ HTTP → BizyAir (submit) → Loop(poll)     │    │
│  │       → 返回封面 URL                           │    │
│  │       → Write Binary File → /volume1/tomato/  │    │
│  ├─ ── ── ── ── ── ── ── ── ── ── ── ── ── ── ┘    │
│  │                                                    │
│  ├─ Code (合并结果 → 写 songs.json)                  │
│  │                                                    │
│  ├─ Execute Command                                   │
│  │    python3 /tomato-vault/build.py extract          │
│  │    python3 /tomato-vault/vault.py build            │
│  │    → 生成静态网站 HTML                             │
│  │                                                    │
│  └─ HTTP Request → Telegram Bot API (发送日报)        │
│                                                       │
│  文件落地: /volume1/tomato-music/{date}_{title}/      │
│  网站输出: /volume1/tomato-vault/site/                │
└──────────────────────────────────────────────────────┘
```

---

## 四、关键设计决策

### 4.1 为什么不需要 mmx CLI

mmx 本质是 MiniMax API 的 HTTP 封装。n8n 的 HTTP Request 节点直接调：

```
POST https://api.minimaxi.com/v1/music_generation
Authorization: Bearer {MINIMAX_API_KEY}
{
  "model": "music-2.6",
  "lyrics": "[Verse]\n歌词...",
  "prompt": "广场舞 BPM 128 动感节奏",
  "audio_setting": { "sample_rate": 44100, "bitrate": 256000, "format": "mp3" },
  "output_format": "url"
}
→ 返回 { data: { audio: "https://..." } }
→ n8n Write Binary File 下载到 NAS
```

**API Key 已知**（`~/.mmx/config.json` 里有）：MiniMax `sk-cp-lLxx...`

### 4.2 并行策略

```
5 首歌 × (1 MP3 + 1 封面) = 10 个 HTTP 请求
n8n Split In Batches (batch size=5) → 每首的 MP3 和封面同时发

时间线：
  t=0s    5首 MP3 同时提交  +  5张封面同时提交
  t=90s   MP3 开始陆续返回（每首~90s）
  t=60s   封面开始陆续返回（每首~60s）
  t=120s  全部完成，开始写文件
  t=180s  网站构建 + Telegram
  ────────────────────────
  总计 ≈ 3-5 分钟 (vs 现在 27-47 分钟)
```

### 4.3 网站构建改造（唯一需要改代码的地方）

现有 `vault.py` 和 `build.py` 有两个 macOS 依赖需替换：

| 依赖 | 现有 (macOS) | 改为 (Linux/Docker) | 改动 |
|------|-------------|---------------------|------|
| MP3 时长 | `afinfo` | `ffprobe` | build.py 1处 |
| 音乐路径 | `~/Music/番茄音乐` | `/volume1/tomato-music` | 环境变量 |

**Dockerfile 改造**：加 `python3 + ffmpeg`，挂载 tomato-vault 目录。

### 4.4 重试策略（n8n 节点级）

| 节点 | 失败率 | Retry | 间隔 |
|------|--------|-------|------|
| MiniMax MP3 | ~5% | 3次 | 30s |
| BizyAir 封面 | ~10% | 3次 | 60s |
| DeepSeek 歌词 | ~1% | 2次 | 10s |
| Telegram | ~1% | 2次 | 5s |

n8n 每个节点都有 `Retry On Fail` + `Max Tries` + `Wait Between Tries` 配置，不需要写代码。

### 4.5 容器改造清单

```
Dockerfile 新增:
  apk add python3 ffmpeg

docker-compose.yml 新增 volume:
  - /volume1/tomato-music:/home/node/tomato-music
  - /volume1/tomato-vault:/home/node/tomato-vault

环境变量新增:
  TOMATO_MUSIC_DIR=/home/node/tomato-music
  DEEPSEEK_API_KEY=...
  MINIMAX_API_KEY=sk-cp-lLxx...
  BIZYAIR_API_KEY=...
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...
```

---

## 五、数据流

```
DeepSeek API
  → 5首歌词 JSON {title, genre, lyrics, mmx_prompt, cover_prompt, mood}
  → 5路并行:
      MiniMax API → MP3 bytes → /volume1/tomato-music/{date}_{title}/{title}.mp3
      BizyAir API → Cover bytes → /volume1/tomato-music/{date}_{title}/{title}_cover.png
  → songs.json (合并元数据)
  → build.py (扫描目录, 生成 songs.json)
  → vault.py build (生成网站 HTML)
  → Telegram (日报)
```

**最终文件结构**：
```
/volume1/tomato-music/
├── 2026-06-18_摇起来/
│   ├── 摇起来.mp3
│   ├── 摇起来_cover.png
│   └── 摇起来_lyrics.txt
├── 2026-06-18_月满西楼/
│   └── ...
└── ...（累积）

/volume1/tomato-vault/
├── data/songs.json
├── site/index.html        ← 静态网站
└── site/music/...         ← 软链接到 tomato-music
```

---

## 六、实施计划

### Step 1：容器改造（30min）

1. 改 Dockerfile：加 python3 + ffmpeg
2. 改 docker-compose.yml：加 volume 挂载 + 环境变量
3. 重建容器
4. 验证 python3 + ffprobe 可用

### Step 2：代码移植（1h）

1. 复制 `build.py` + `vault.py` 到 `/volume1/tomato-vault/`
2. 改 `afinfo` → `ffprobe`
3. 改路径为环境变量
4. 在容器内测试 `python3 build.py extract` + `python3 vault.py build`

### Step 3：n8n 工作流搭建（2h）

用 n8n Web UI 或 MCP 创建工作流：
1. Schedule Trigger → DeepSeek HTTP Request → Code（歌词解析）
2. Split In Batches → MiniMax HTTP + BizyAir HTTP（并行 + 重试）
3. Write Binary File（MP3 + 封面落地）
4. Code（合并 songs.json）
5. Execute Command（网站构建）
6. HTTP Request（Telegram 通知）

### Step 4：测试 + 上线（30min）

1. 手动触发，验证全链路
2. 对比耗时（目标 < 5min）
3. 关闭 remio scheduler T-A/T-A'/T-B
4. 激活 n8n 工作流

---

## 七、待确认

| # | 问题 | 影响 |
|---|------|------|
| 1 | **DeepSeek API Key** — 用 NAS920 freellmapi 代理还是 DeepSeek 官方 key？ | 歌词创作环节 |
| 2 | **BizyAir API Key** — 当前 key 还有效吗？ | 封面生成 |
| 3 | **Telegram Bot** — 番茄日报发哪个 Bot / Chat ID？ | 通知环节 |
| 4 | **海报生成** — 代码里只有读写逻辑，实际生成用的什么服务？还是也用 BizyAir？还是取消？ | 可选环节 |
| 5 | **曲风矩阵** — 继续 广场舞×2 + 民谣×1 + 流行×1 + 抒情×1？还是调整？ | 歌词创作 |
| 6 | **网站外网访问** — tomato-vault 网站是否也走 cpolar 隧道？ | 发布环节 |

---

*确认后立即执行 Step 1-4。*
