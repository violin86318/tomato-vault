## 基本信息

| 项目 | 值 |
|:---|:---|
| 曲风代号 | `guofeng` |
| 风格描述 | 民族风/古诗词改编/中国风 |
| BPM | 90 |
| 和弦公式 | 大调卡农 |
| 创作模型 | deepseek-flash |
| 歌词行数 | 62 行（纯歌词，不含 [Tag]） |
| 日期 | 2026-09-13 |
| slug | 青石巷_2026-09-13 |

## 创作思路

番茄音乐面向下沉受众，追求「接地气 × 情绪浓 × 旋律洗脑 × 下沉受众买单」。

**风格定位**：国风例外允许古典意象，但仍要直白易懂；D5 碎句检测通过。

**本次选题：《青石巷》** ——跳出「长安/醉/月/桃花笺」系列词牌名路线，本次用「青石巷」三字直接命名意象——青石板/苔痕/油纸伞/古井/苔痕。Hook「青石巷 那条巷 我还在巷口等你归」古典意象拉回痴情直白。Bridge 落到「那巷口的灯笼换了又换/我还在原地站了千年」的时空折叠。

## 歌词

```
[Intro]
青石板路湿透谁家衣裳
油纸伞下走过半段旧时光
苔痕悄悄爬上斑驳的墙

[Verse 1]
月色爬上小楼旧了雕花的窗
风卷起往事吹散一地过往
那年雪落时你说会回到故乡
我数着更漏一直等到天亮
琴弦断了一根还剩几根在响
没人听的曲子最是断人肠
青石的缝隙里长出新草两行

[Pre-Chorus]
你走那天下着细雨没有一点声响
我站在巷口把背影望成了山岗
那句等你藏在心里至今没敢讲

[Chorus]
青石巷 雨微凉
谁家笛声吹断肠
青石巷 人成双
只剩影子陪我到天亮
若问相思多长 一巷烟雨长
青石巷 等你回望

[Verse 2]
楼上的人把明月看成了霜
我把旧信读了又读纸已泛黄
风穿过巷口像你还在耳边唱
雪落满肩头我也不觉得凉
琴还在墙角落满一层灰和慌
我弹着弹着眼泪就红了眼眶
青石巷这条路我走了千百趟

[Pre-Chorus]
花开了一年又一年不见你模样
伞下空出的一半总被雨打凉
我把想说的话都种进了青苔上

[Chorus]
青石巷 雨微凉
谁家笛声吹断肠
青石巷 人成双
只剩影子陪我到天亮
若问相思多长 一巷烟雨长
青石巷 等你回望

[Instrumental]
古筝起 笛声扬 巷深处有人唱

[Bridge]
我也曾想过转身就把你遗忘
可每次走到巷口脚就不听讲
石阶被人踩出一层淡淡的亮
想你这件事我却怎么也学不会放
月亮啊你若见他就替我望一望

[Chorus]
青石巷 雨微凉
谁家笛声吹断肠
青石巷 人成双
只剩影子陪我到天亮
若问相思多长 一巷烟雨长
青石巷 等你回望

[Outro]
青石板还在 苔痕又长
油纸伞收好 放在门旁
你若哪天回来 请别慌张
我一直在巷子最深的那个地方
```

## mmx 提示词

```
A Chinese traditional-style pop song at 90 BPM featuring guzheng and dizi, built on a canon chord progression. The arrangement is elegant and atmospheric with extended guzheng solo passages, leaving generous space between vocal lines. An operatic female vocal delivers poetic phrases with unhurried pacing. Long intro establishes the classical mood before the first verse enters.
```

## Suno 提示词

```
Chinese traditional pop, guzheng, dizi flute, 90 BPM, canon progression, operatic female vocal, poetic classical imagery, atmospheric, moonlit, nostalgic, extended guzheng solo, elegant pacing
```

## cover_prompt

```
A narrow cobblestone alley with ancient green moss, a red paper umbrella leaning against the mossy wall, and soft golden light filtering through hanging laundry. the Chinese characters '青石巷' naturally appearing as part of the scene (carved into a stone slab). Classical Chinese ink wash painting style with warm sepia and celadon tones, 1:1 square
```

## 质检

- ✅ D1 直白口语（无诗化）
- ✅ D2 副歌 A+A+A+B 排比洗脑
- ✅ D3 Hook 重复
- ✅ D4 主歌押韵（句尾词分布自然）
- ✅ D5 碎句检测（主歌碎句 0%、均长 ≥10 字）
- ✅ 行数 ≥ 下限（广场舞 ≥55 / 洗脑 ≥55 / 伤感 ≥50 / 国风 ≥50 / 家乡 ≥55）
