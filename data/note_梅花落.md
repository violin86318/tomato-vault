# 🍅 番茄档案：梅花落

**日期**: 2026-09-14
**曲风**: 民族风/古诗词改编/中国风 (guofeng)
**和弦**: 大调卡农
**BPM**: 90
**Slug**: `梅花落_2026-09-14`
**音频目录**: `/Users/wanglingwei/Music/番茄音乐/2026-09-14_梅花落`
**创作模型**: kimi-k2.6（guofeng）→ deepseek-flash（fallback）
**歌词行数**: 64 行
**D5 碎句检测**: 主歌 5/33 = 15%,均长 9.6 字 ✅

## 创作思路

番茄音乐面向下沉受众,追求「接地气 × 情绪浓 × 旋律洗脑 × 下沉受众买单」。

**风格定位**:直白口语、短句重复(仅限副歌 Hook)、情绪外放;D5 碎句检测通过。

延续「青石巷/故人归/念长安/醉月楼/醉西厢/桃花笺/寄明月/故园梦」国风路线,本次跳出「醉/忆/长安/故人」格式,直接以「梅花落」古典意象做标题。Hook「梅花落」三字重复 + 「一片一片落在我肩头/一年一年落满这空楼」堆砌等待时长。Bridge 加「你走时梅花才刚长骨头 / 现在落得我心里到处都是」的时间折叠。Outro 收「等你等到明年花开」。

## 歌词正文

```
[Intro]
梅花落 梅花落
落在谁家的窗
落进谁的心上

[Verse 1]
那年下雪你牵我走过这条街
你说梅花开的时候你就回来
我在城东小楼租了一间房
推开窗就能看见那一片白
月亮挂在楼角像你留的灯
我数着日子把冬天都数完
你的棉衣我还挂在门后边
风一吹我就当你推门进来

[Pre-Chorus]
炉火烧了一夜热水凉了又热
我学着你教我的曲子慢慢弹
弹到那一段指头就开始发抖

[Chorus]
梅花落 一片一片落在我肩头
梅花落 一年一年落满这空楼
梅花落 我还在楼下一直等着
风把花瓣吹到我脸上很凉
你走那天 也是这么一个天
你可知道 我等你等到头发白了

[Verse 2]
隔壁阿婆问我你几时回来
我笑着说他在外头忙挣钱
其实我连一封信都没收着
信封上写着城南那条老巷
雪又下大了路都看不清了
我点着灯站在门口不肯回
人家都说我这人太死心眼了
可我就信你说的那一句话啊

[Pre-Chorus]
琴弦断了一根我也没去换
我怕换了就弹不出那首曲
怕你回来听不见我在这等你

[Chorus]
梅花落 一片一片落在我肩头
梅花落 一年一年落满这空楼
梅花落 我还在楼下一直等着
风把花瓣吹到我脸上很凉
你走那天 也是这么一个天
你可知道 我等你等到头发白了

[Instrumental]

[Bridge]
雪停了梅花开了一整树
我数了数今年又多开几朵
你走的时候它才刚长骨头
现在它落得我心里到处都是
我把花瓣一片片收进旧衣裳
等你回来闻一闻这一年的香

[Chorus]
梅花落 一片一片落在我肩头
梅花落 一年一年落满这空楼
梅花落 我还在楼下一直等着
风把花瓣吹到我脸上很凉
你走那天 也是这么一个天
你可知道 我等你等到头发白了

[Outro]
梅花落 落满了台阶
梅花落 落白了头发
你到底还回不回来
我等你等到明年花开
```

## mmx 提示词（music-3.0,新格式）

A Chinese traditional-style pop song at 90 BPM featuring guzheng and dizi, built on a canon chord progression. The arrangement is elegant and atmospheric with extended guzheng solo passages, leaving generous space between vocal lines. An operatic female vocal delivers poetic phrases with unhurried pacing. Long intro establishes the classical mood before the first verse enters.

## Suno 提示词

```
Chinese traditional-style pop, 90 BPM, guzheng, dizi, classical Chinese instruments, poetic imagery, melancholic female vocal with operatic touch, plum blossoms and snow, canon chord progression, atmospheric, cinematic
```

## 封面提示词

```
A snow-covered plum blossom tree shedding petals onto a stone path leading to an old wooden door, a woman in traditional hanfu standing alone in the falling snow, full moon behind her. the Chinese characters '梅花落' etched into a surface in the scene on a wooden plaque. Cool ivory and crimson palette, classical Chinese painting aesthetic, 1:1 square
```

## 数据交接

- ✅ mmx_prompt 已生成（新格式：完整英文句子 + 留白词,禁止 style: 逗号堆叠）
- ✅ suno_prompt 已生成
- ✅ cover_prompt 已生成（差异化意象,提取歌词 2-3 个具体画面元素）
- ✅ D5 碎句检测通过（主歌 ≤7字行 5/33 = 15%,均长 9.6 字）
- ✅ 歌词行数 64 行达标
- ✅ assemble_tomato_audio.py exit 0,tomato_audio.json 已写入
