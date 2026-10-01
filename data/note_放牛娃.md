# 🍅 番茄档案：放牛娃

**日期**: 2026-09-14
**曲风**: 乡愁/励志/朴实口语 (hometown)
**和弦**: 卡农变体
**BPM**: 100
**Slug**: `放牛娃_2026-09-14`
**音频目录**: `/Users/wanglingwei/Music/番茄音乐/2026-09-14_放牛娃`
**创作模型**: kimi-k2.6（hometown）→ deepseek-flash（fallback）
**歌词行数**: 69 行
**D5 碎句检测**: 主歌 5/33 = 15%,均长 10.3 字 ✅

## 创作思路

番茄音乐面向下沉受众,追求「接地气 × 情绪浓 × 旋律洗脑 × 下沉受众买单」。

**风格定位**:直白口语、短句重复(仅限副歌 Hook)、情绪外放;D5 碎句检测通过。

延续「老灶台/老水井/老屋门/老碾子/老磨坊/柴火饭/小米粥/麦穗黄/山路弯弯/土坯墙」乡愁童年物件路线,本次跳出「老X/妈X」物件格式,直接以「放牛娃」角色做标题——更具体更有人物。Hook「放牛娃/山里娃」+「光着脚也能把石头踩塌」+「谁说我这一辈子只能放牛 / 我偏要闯出个名堂给我爹娘看」励志转折。Bridge 写「后来我在城里搬过砖也扛过包 / 夜里想起老牛就偷偷掉眼泪」+「村口那棵老槐树还站在风里头」具象。最后 Chorus 回到「今天我开着小车回到这山洼」完成励志闭环。

## 歌词正文

```
[Intro]
放牛娃 放牛娃
山那边的晚霞红啦
娘在村口喊我回家

[Verse 1]
我家住在山脚下那个小村子
门前那条土路一直通向山那边
七岁那年爹把牛绳交到我手里
他说这头老黄牛是咱家半边天
清早露水打湿我那双破裤脚
我牵着老牛慢慢悠悠走上山坡
它低头啃草我就躺在草地上
看云一朵一朵飘过对面那道梁

[Pre-Chorus]
那时候我不懂什么叫远方
只晓得山外头还连着山
娘的饭香飘过整条山岗

[Chorus]
放牛娃 放牛娃
追着夕阳跑过一道道山洼
老黄牛 老黄牛
陪我咽下多少苦和辣
山里娃 山里娃
光着脚也能把石头踩塌
谁说我这一辈子只能放牛
我偏要闯出个名堂给我爹娘看

[Verse 2]
十五岁那年我背起那个旧书包
走过村口那棵老槐树底下
老牛拴在树下抬着头看看我
它眼睛里好像有话说不出来
娘往我兜里塞了两个热鸡蛋
爹说出去就好好念书别老想家
我一步三回头走下山那条路
老槐树叶子哗啦啦地响个不停

[Pre-Chorus]
我知道山路弯弯一点不好走
也知道城里灯火不认识我
可我身上有老黄牛那股犟劲

[Chorus]
放牛娃 放牛娃
追着夕阳跑过一道道山洼
老黄牛 老黄牛
陪我咽下多少苦和辣
山里娃 山里娃
光着脚也能把石头踩塌
谁说我这一辈子只能放牛
我偏要闯出个名堂给我爹娘看

[Bridge]
后来我在城里搬过砖也扛过包
夜里想起老牛就偷偷掉眼泪
村口那棵老槐树还站在风里头
爹娘的头发又白了好几根
我告诉自己再难也不能够倒下
因为我答应过他们要出人头地

[Chorus]
放牛娃 放牛娃
今天我开着小车回到这山洼
老黄牛 老黄牛
你看见了吗我真的出息啦
山里娃 山里娃
我把我爹娘接到城里住下
谁说山里娃一辈子抬不起头
我偏要把这口气争给全世界看

[Outro]
放牛娃 放牛娃
如今我回来啦
老槐树还在 老牛不在了
娘 你儿子出息啦
```

## mmx 提示词（music-3.0,新格式）

A warm Chinese folk pop song at 100 BPM with a gentle male vocal and acoustic guitar, built on a canon variation progression. The arrangement is nostalgic and uplifting with extended instrumental sections, leaving room between verses for the melody to breathe. Bridge section provides an inspirational turn before the final chorus. Countryside imagery guides the emotional arc.

## Suno 提示词

```
Chinese folk pop, 100 BPM, warm male vocal with acoustic guitar, countryside nostalgia, hometown memories, inspirational bridge, canon variation progression, rural childhood, warm and uplifting, determined
```

## 封面提示词

```
A young barefoot boy with a straw hat leading an old yellow ox up a grassy hillside at sunset, old locust tree and thatched-roof cottage in the distance, rosy clouds in the sky. the Chinese characters '放牛娃' naturally appearing as part of the scene carved into a stone by the path. Warm sepia and golden-hour tones, nostalgic rural illustration style, 1:1 square
```

## 数据交接

- ✅ mmx_prompt 已生成（新格式：完整英文句子 + 留白词,禁止 style: 逗号堆叠）
- ✅ suno_prompt 已生成
- ✅ cover_prompt 已生成（差异化意象,提取歌词 2-3 个具体画面元素）
- ✅ D5 碎句检测通过（主歌 ≤7字行 5/33 = 15%,均长 10.3 字）
- ✅ 歌词行数 69 行达标
- ✅ assemble_tomato_audio.py exit 0,tomato_audio.json 已写入
