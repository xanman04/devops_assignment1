"""Draw the Pickle Rick demo flyer: an acid-green swirling portal on black, with the lineup underneath.

Run from the repository root with `.venv/Scripts/python.exe tools/build_pickle_rick_poster.py`. The artwork is drawn
here from scratch (nothing copied from the show); the event and names are fictional demo content."""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pickle-rick-poster.png"
FONT = ROOT / "static" / "fonts" / "FunnelDisplay-VariableFont_wght.ttf"
W, H = 900, 1350
GREEN, LIME, DEEP = (122, 255, 0), (210, 255, 120), (8, 60, 10)


def font(size):
    return ImageFont.truetype(str(FONT), size)


def portal_layer():
    """Spiral arms, rings and speckle for the portal, drawn large and blurred twice for a glow."""
    rng = random.Random(137)
    cx, cy = W // 2, 560
    art = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(art)
    for r in range(330, 20, -2):                                # filled rings from dark rim to bright core
        t = 1 - r / 330
        shade = tuple(int(DEEP[i] + (GREEN[i] - DEEP[i]) * t ** 1.6) for i in range(3))
        wobble = 6 * math.sin(r / 9)
        draw.ellipse((cx - r - wobble, cy - r * 1.18, cx + r + wobble, cy + r * 1.18), fill=shade)
    swirl = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(swirl)
    for arm in range(5):                                         # spiral arms
        points = []
        for step in range(0, 520):
            angle = step * 0.045 + arm * (2 * math.pi / 5)
            radius = 8 + step * 0.62
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius * 1.18))
        for i in range(len(points) - 1):
            width = max(2, int(14 - i / 45))
            sd.line((points[i], points[i + 1]), fill=255, width=width)
    swirl_rgb = ImageChops.multiply(Image.merge("RGB", (swirl, swirl, swirl)), Image.new("RGB", (W, H), LIME))
    art = ImageChops.screen(art, swirl_rgb.filter(ImageFilter.GaussianBlur(2)))
    for _ in range(260):                                         # splatter and sparks
        angle, dist = rng.uniform(0, 2 * math.pi), rng.uniform(320, 540)
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist * 1.1
        size = rng.choice((1, 1, 2, 2, 3, 5))
        if 0 < x < W and 0 < y < 1000:
            draw.ellipse((x - size, y - size, x + size, y + size), fill=(150 + rng.randint(0, 100), 255, 40 + rng.randint(0, 90)))
    for _ in range(14):                                          # drips running down from the lower rim
        x = rng.randint(cx - 230, cx + 230)
        top = cy + int(((330 ** 2 - (x - cx) ** 2) ** 0.5) * 1.18 * 0.9)
        length = rng.randint(40, 150)
        draw.line((x, top, x, top + length), fill=(120, 240, 20), width=rng.randint(4, 9))
        draw.ellipse((x - 7, top + length - 6, x + 7, top + length + 8), fill=(160, 255, 60))
    glow = art.filter(ImageFilter.GaussianBlur(26))
    return ImageChops.screen(art, ImageChops.multiply(glow, Image.new("RGB", (W, H), (230, 255, 230))))


def build():
    image = portal_layer()
    # dark vignette and a fade into the lineup area
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        sd.line((0, y, W, y), fill=int(min(255, max(0, (y - 760) / (H - 760)) ** 0.8 * 245 + max(0, 160 - y) * 0.6)))
    image = Image.composite(Image.new("RGB", (W, H), (3, 8, 4)), image, shade)
    draw = ImageDraw.Draw(image)

    def centred(y, text, face, fill, spacing=0, stroke=0):
        width = draw.textbbox((0, 0), text, font=face)[2] + spacing * (len(text) - 1)
        x = (W - width) / 2
        if not spacing:
            draw.text((x, y), text, font=face, fill=fill, stroke_width=stroke, stroke_fill=(3, 8, 4))
            return
        for letter in text:
            draw.text((x, y), letter, font=face, fill=fill)
            x += draw.textbbox((0, 0), letter, font=face)[2] + spacing

    centred(48, "MADRID NIGHTS  /  PSY-TRANCE", font(24), LIME, 4)
    centred(76, "PICKLE", font(150), (235, 255, 214), stroke=7)
    centred(214, "RICK", font(150), GREEN, stroke=7)
    centred(930, "PORTAL RAVE", font(70), (235, 255, 214))
    draw.line((120, 1030, W - 120, 1030), fill=GREEN, width=3)
    centred(1050, "LINEUP", font(22), LIME, 6)
    centred(1090, "Pickle Rick  ·  Squanchy  ·  Birdperson", font(38), (240, 255, 230))
    centred(1146, "Evil Morty  ·  Gazorp", font(38), (200, 235, 190))
    centred(1230, "SAT 14 NOV  ·  22:00  ·  LA RIVIERA", font(30), GREEN, 2)
    centred(1290, "A fictional demo event. No portals were harmed.", font(20), (150, 190, 140))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG", optimize=True)
    print("wrote", OUT, image.size)


if __name__ == "__main__":
    build()
