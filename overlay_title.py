#!/usr/bin/env python3
"""
番茄音乐封面叠加歌名文字
=========================
AI 生图无法精确渲染中文文字。
此脚本在封面生成后，用 PIL 将准确的歌名文字叠加到封面底部。

用法：
  python3 overlay_title.py                          # 处理所有歌曲
  python3 overlay_title.py --postprocess <path>     # 指定 JSON 数据源
"""

import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 中文字体路径（按优先级）
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]

VAULT_DIR = Path(__file__).parent


def find_font():
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp):
            return fp
    return None


def overlay_title_on_cover(cover_path, title, font_path):
    """为单张封面叠加歌名文字"""
    img = Image.open(cover_path).convert("RGBA")
    w, h = img.size
    base_size = max(w, h)

    # 文字大小：10% 图宽，最小 24px
    font_size = max(int(base_size * 0.1), 24)
    font = ImageFont.truetype(font_path, font_size)

    # 计算文字占据区域
    bb = ImageDraw.Draw(img).textbbox((0, 0), title, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    # 居中，距底部 6%
    tx = (w - tw) / 2
    ty = h - th - int(h * 0.06)

    # 半透明黑色背景条（底部带状）
    bar_pad = int(h * 0.025)
    bar_h = th + bar_pad * 2
    bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 120))

    # 构建叠加层
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bar_y = ty - bar_pad
    overlay.paste(bar, (0, bar_y), bar)

    # 绘制文字阴影 + 主体
    draw = ImageDraw.Draw(overlay)
    shadow_color = (0, 0, 0, 200)
    draw.text((tx + 2, ty + 2), title, font=font, fill=shadow_color)
    draw.text((tx, ty), title, font=font, fill=(255, 255, 255, 255))

    # 合并 + 保存（覆盖原图）
    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(cover_path, "JPEG", quality=95)
    return True


def main():
    font_path = find_font()
    if not font_path:
        print("❌ 未找到中文字体（PingFang/STHeiti）")
        sys.exit(1)

    print(f"🔤 字体: {os.path.basename(font_path)}")

    # 确定数据源
    postprocess_path = VAULT_DIR / "data" / "tomato_postprocess.json"
    if not postprocess_path.exists():
        print(f"❌ 未找到数据源: {postprocess_path}")
        sys.exit(1)

    with open(postprocess_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    songs = data.get("songs", [])
    print(f"📋 共 {len(songs)} 首")

    success = 0
    skipped = 0

    for song in songs:
        song_dir = song["song_dir"]
        title = song["title"]

        if not os.path.isdir(song_dir):
            print(f"⏭️ {title}: 目录不存在")
            skipped += 1
            continue

        covers = sorted([
            f for f in os.listdir(song_dir)
            if f.startswith("cover_") and f.endswith(".jpg")
        ])
        if not covers:
            print(f"⏭️ {title}: 无封面文件")
            skipped += 1
            continue

        for cover_file in covers:
            cover_path = os.path.join(song_dir, cover_file)
            try:
                overlay_title_on_cover(cover_path, title, font_path)
                print(f"  ✅ {cover_file}: 叠加歌名「{title}」")
                success += 1
            except Exception as e:
                print(f"  ❌ {cover_file}: {e}")

    print(f"\n🎉 完成: {success} 张成功, {skipped} 首跳过")


if __name__ == "__main__":
    main()