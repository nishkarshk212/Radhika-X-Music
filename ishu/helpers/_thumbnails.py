# Copyright (c) 2025 TheHamkerAlone 
# Licensed under the MIT License.
# This file is part of AloneX

import os
import asyncio
import numpy as np
import re
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from collections import Counter
from ishu import config
from ishu.helpers import Track

try:
    from unidecode import unidecode
except ImportError:
    def unidecode(text):
        return text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE_PATH = os.path.join(BASE_DIR, "font.ttf")
FONT_INFO_PATH = os.path.join(BASE_DIR, "font2.ttf")
TEMPLATE_PATH = os.path.join(BASE_DIR, "..", "assets", "template.png")

def safe_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)
        self.font_title = safe_font(FONT_TITLE_PATH, 32)
        self.font_info = safe_font(FONT_INFO_PATH, 20)
        self.font_watermark = safe_font(FONT_TITLE_PATH, 24)

    async def start(self):
        os.makedirs("cache", exist_ok=True)

        if not os.path.exists(FONT_TITLE_PATH):
            print(f"Missing font: {FONT_TITLE_PATH}")

        if not os.path.exists(FONT_INFO_PATH):
            print(f"Missing font: {FONT_INFO_PATH}")

        if not os.path.exists(TEMPLATE_PATH):
            print(f"Missing template: {TEMPLATE_PATH}")

        return True

    async def save_thumb(self, output_path: str, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        for attempt in range(3):
            try:
                if url.startswith("http"):
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(url, timeout=15) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                with open(output_path, "wb") as f:
                                    f.write(content)
                                return output_path
            except Exception as e:
                if attempt == 2:
                    print(f"Error saving thumb: {e}")
                await asyncio.sleep(1)
        return output_path

    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            temp = f"cache/temp_{song.id}.jpg"
            final_path = f"cache/{song.id}.png"
            if os.path.exists(final_path):
                return final_path

            await self.save_thumb(temp, song.thumbnail)
            
            try:
                src = Image.open(temp).convert("RGBA")
            except Exception:
                try:
                    src = Image.new("RGBA", (1280, 720), (30, 30, 30, 255))
                except Exception:
                    return config.DEFAULT_THUMB

            W, H = self.size

            # 1. BLURRED BACKGROUND from song image
            bg_ratio = W / H
            src_ratio = src.width / src.height
            if src_ratio > bg_ratio:
                new_w = int(src.height * bg_ratio)
                offset = (src.width - new_w) // 2
                bg = src.crop((offset, 0, offset + new_w, src.height))
            else:
                new_h = int(src.width / bg_ratio)
                offset = (src.height - new_h) // 2
                bg = src.crop((0, offset, src.width, offset + new_h))

            bg = bg.resize((W, H), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(35))

            # Darken slightly
            bg_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
            bg = Image.alpha_composite(bg, bg_overlay)

            # 2. CREATE CARD in the center
            card_w, card_h = 940, 580
            card_x = (W - card_w) // 2
            card_y = (H - card_h) // 2
            card_radius = 45
            
            card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_layer)
            card_draw.rounded_rectangle(
                (card_x, card_y, card_x + card_w, card_y + card_h),
                radius=card_radius,
                fill=(235, 235, 235, 255)
            )
            
            bg = Image.alpha_composite(bg, card_layer)

            # 3. PASTE COVER ART inside the card
            cover_margin = 35
            cover_w = card_w - (cover_margin * 2) # 870
            cover_h = 370
            cover_x = card_x + cover_margin # 205
            cover_y = card_y + cover_margin # 105
            cover_radius = 25
            
            # Center crop the cover art to fit 870x370
            target_ratio = cover_w / cover_h
            src_ratio = src.width / src.height
            if src_ratio > target_ratio:
                new_w = int(src.height * target_ratio)
                offset = (src.width - new_w) // 2
                cover = src.crop((offset, 0, offset + new_w, src.height))
            else:
                new_h = int(src.width / target_ratio)
                offset = (src.height - new_h) // 2
                cover = src.crop((0, offset, src.width, offset + new_h))
                
            cover = cover.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
            
            cover_mask = Image.new("L", (cover_w, cover_h), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, cover_w, cover_h), radius=cover_radius, fill=255
            )
            
            bg.paste(cover, (cover_x, cover_y), cover_mask)

            # 4. ADD TEXT & PROGRESS BAR inside the card
            draw = ImageDraw.Draw(bg)
            
            title_x = cover_x
            title_y = cover_y + cover_h + 20
            max_title_w = cover_w
            
            def ellipsize(s, font, max_w):
                if draw.textbbox((0, 0), s, font=font)[2] <= max_w:
                    return s
                lo, hi = 1, len(s)
                best = "…"
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = s[:mid].rstrip() + "…"
                    if draw.textbbox((0, 0), cand, font=font)[2] <= max_w:
                        best = cand
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return best

            title_str = ellipsize(unidecode(str(song.title)), self.font_title, max_title_w)
            draw.text((title_x, title_y), title_str, fill=(18, 18, 18, 255), font=self.font_title)
            
            subtitle_str = f"{song.channel_name}  •  {song.view_count}" if song.view_count else str(song.channel_name)
            subtitle_str = ellipsize(unidecode(subtitle_str), self.font_info, max_title_w)
            subtitle_y = title_y + 38
            draw.text((title_x, subtitle_y), subtitle_str, fill=(110, 110, 110, 255), font=self.font_info)
            
            bar_y = subtitle_y + 38
            bar_h = 6
            bar_radius = 3
            draw.rounded_rectangle(
                (cover_x, bar_y, cover_x + cover_w, bar_y + bar_h),
                radius=bar_radius,
                fill=(210, 210, 210, 255)
            )
            
            # Show a fixed progress (e.g. 35%) representing play onset visual mockup
            active_percentage = 0.35
            active_w = int(cover_w * active_percentage)
            draw.rounded_rectangle(
                (cover_x, bar_y, cover_x + active_w, bar_y + bar_h),
                radius=bar_radius,
                fill=(235, 50, 50, 255)
            )
            
            time_y = bar_y + 12
            draw.text((cover_x, time_y), "0:00", fill=(100, 100, 100, 255), font=self.font_info)
            duration_str = str(song.duration)
            duration_w = draw.textbbox((0, 0), duration_str, font=self.font_info)[2]
            draw.text((cover_x + cover_w - duration_w, time_y), duration_str, fill=(100, 100, 100, 255), font=self.font_info)

            # 5. WATERMARK TEXT
            watermark_text = "[ BILLU BADMOSH ]"
            watermark_w = draw.textbbox((0, 0), watermark_text, font=self.font_watermark)[2]
            watermark_x = W - watermark_w - 45
            watermark_y = 35
            
            draw.text((watermark_x + 2, watermark_y + 2), watermark_text, fill=(0, 0, 0, 150), font=self.font_watermark)
            draw.text((watermark_x, watermark_y), watermark_text, fill=(255, 255, 255, 255), font=self.font_watermark)

            out = bg.convert("RGB")
            out.save(final_path, "PNG")

            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception:
                pass

            return final_path

        except Exception as e:
            print(f"Error: {e}")
            return config.DEFAULT_THUMB
