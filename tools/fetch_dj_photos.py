# Copyright © 2026 Xander Chen. All rights reserved.
"""Refresh the curated, freely licensed DJ thumbnails from Wikimedia Commons.

Run manually when updating the profiles. Photo credits and licenses are recorded
in the seed command and DJ_SOURCES.md; this tool does not change that metadata.
"""
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageOps


FILES = {
    "charlotte_de_witte": "Charlotte de witte-1513626416.jpg",
    "andy_c": "Andy C live in 2011 (cropped).jpg",
    "black_coffee": "Black Coffee perfoming at Hï Ibiza in June 2018.jpg",
    "skrillex": "Skrillex.jpg",
    "armin_van_buuren": "Armin van Buuren, November 2025.jpg",
    "peggy_gou": "Peggy Gou 2019.jpg",
    "carl_cox": "Carl Cox @ ADE 2012.jpg",
}
OUTPUT = Path(__file__).resolve().parents[1] / "static" / "djs"
HEADERS = {"User-Agent": "BasslineStudentDemo/1.0 (Wikimedia Commons photo attribution)"}


def fetch(url):
    with urlopen(Request(url, headers=HEADERS), timeout=30) as response:
        return response.read()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for slug, title in FILES.items():
        query = urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 640,
                           "titles": f"File:{title}"})
        payload = json.loads(fetch(f"https://commons.wikimedia.org/w/api.php?{query}"))
        page = next(iter(payload["query"]["pages"].values()))
        info = page["imageinfo"][0]
        with Image.open(io.BytesIO(fetch(info.get("thumburl", info["url"])))) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((640, 720))
            image.save(OUTPUT / f"{slug}.webp", "WEBP", quality=82, method=6)
        print(f"{slug}: {OUTPUT / (slug + '.webp')}")


if __name__ == "__main__":
    main()
