"""Build original, clearly fictional Madrid demo flyers from bundled artwork.

Run from the repository root with `.venv/Scripts/python.exe tools/build_demo_posters.py`.
The four background images were created for this project with the built-in image tool.
"""
from pathlib import Path
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from discovery.management.commands.seed_madrid_demo import NIGHTS, VENUES

ART = ROOT / "static" / "demo-posters"
FONT = ROOT / "static" / "fonts" / "FunnelDisplay-VariableFont_wght.ttf"
WIDTH, HEIGHT = 900, 1350


def font(size):
    return ImageFont.truetype(str(FONT), size)


def wrap(draw, text, face, max_width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and draw.textbbox((0, 0), candidate, font=face)[2] > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def poster(night, index):
    key, title, venue_key, _, _, _, _, _, _, theme, lineup, _ = night
    with Image.open(ART / f"{theme}.webp") as source:
        image = source.convert("RGB")
    # Vary the crop and contrast slightly so recurring genre artwork does not form a wall of duplicates.
    inset = 12 + (index % 5) * 8
    image = image.crop((inset, inset, WIDTH - inset, HEIGHT - inset)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(1.05 + (index % 3) * .04)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        top = max(0, 210 - y) / 210
        bottom = max(0, y - 690) / (HEIGHT - 690)
        alpha = int(min(235, 55 + top * 120 + bottom * 145))
        shade.line((0, y, WIDTH, y), fill=(4, 7, 12, alpha))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    accent = {"house": "#72A9FF", "techno": "#FF6E6E", "bass": "#FFB253", "ambient": "#C6A2FF"}[theme]
    draw.rounded_rectangle((68, 56, 390, 111), radius=8, fill=(13, 15, 20, 220), outline=accent, width=3)
    draw.text((83, 66), "MADRID NIGHTS", font=font(31), fill="white")
    draw.text((68, 160), "BASSLINE  /  MADRID", font=font(35), fill=accent)
    title_face = font(100 if len(title) < 19 else 86)
    lines = wrap(draw, title.upper(), title_face, WIDTH - 136)
    for line_index, line in enumerate(lines[:3]):
        draw.text((64, 220 + line_index * 104), line, font=title_face, fill="white", stroke_width=1, stroke_fill="#101319")
    draw.line((68, 1000, WIDTH - 68, 1000), fill=accent, width=5)
    draw.text((68, 1031), "LINEUP", font=font(29), fill=accent)
    for line_index, line in enumerate(wrap(draw, lineup, font(48), WIDTH - 136)[:2]):
        draw.text((68, 1080 + line_index * 58), line, font=font(48), fill="white")
    draw.text((68, 1240), VENUES[venue_key][0].upper(), font=font(36), fill="white")
    draw.text((68, 1287), "MADRID · MUSIC FIRST", font=font(23), fill="#d3d5dc")
    result = ART / f"{key}.webp"
    image.convert("RGB").save(result, "WEBP", quality=84, method=6)
    print(result.relative_to(ROOT))


if __name__ == "__main__":
    for index, night in enumerate(NIGHTS):
        poster(night, index)
