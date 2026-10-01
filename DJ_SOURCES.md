# Curated DJ sources and photo credits

The seven DJ profiles are real artists, separate from the fictional Madrid event fixtures. Their broad genre associations are editorial starting points, not claims that every set fits only those categories. The `seed_djs` command uses existing admin-managed genres and skips a profile if a required category is missing.

Bundled thumbnails in `static/djs/` were resized and converted to WebP from Wikimedia Commons originals. Each DJ page links its photo source and names the photographer and license. These credits should remain with the images if the project is reused.

| DJ | Music/profile source | Photo source | Photographer / license |
|---|---|---|---|
| Charlotte de Witte | [KNTXT, her techno platform](https://kntxt.be/about/) | [Commons file](https://commons.wikimedia.org/wiki/File:Charlotte_de_witte-1513626416.jpg) | Alan Overbeek · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Andy C | [RAM Records artist profile](https://www.ramrecords.com/artist/andy-c) | [Commons file](https://commons.wikimedia.org/wiki/File:Andy_C_live_in_2011_(cropped).jpg) | Stephen West · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) |
| Black Coffee | [Artist site](https://www.realblackcoffee.net/) and [South African Music Rights Organisation](https://old.samro.org.za/wp-content/uploads/2022/11/SAMRO-Notes-Vol-2-Final-Spread-Hi-res.pdf) | [Commons file](https://commons.wikimedia.org/wiki/File:Black_Coffee_perfoming_at_H%C3%AF_Ibiza_in_June_2018.jpg) | DeepBluuue · [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Skrillex | [Artist site](https://skrillex.com/pages/home) and [UKF artist profile](https://ukf.com/discover/artists/skrillex/) | [Commons file](https://commons.wikimedia.org/wiki/File:Skrillex.jpg) | Michael Nusbaum · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) |
| Armin van Buuren | [Official biography](https://www.arminvanbuuren.com/biography/) | [Commons file](https://commons.wikimedia.org/wiki/File:Armin_van_Buuren,_November_2025.jpg) | Web Summit / Sam Barnes / Sportsfile · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Peggy Gou | [XL Recordings artist page](https://www.xlrecordings.com/artists/peggy-gou) and [Gudu Records](https://gudurecords.bandcamp.com/artists) | [Commons file](https://commons.wikimedia.org/wiki/File:Peggy_Gou_2019.jpg) | Davide Guidone · public domain |
| Carl Cox | [Official biography](https://carlcox.com/biography/) | [Commons file](https://commons.wikimedia.org/wiki/File:Carl_Cox_@_ADE_2012.jpg) | Sergey Kozak · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) |

Photo names, licenses, and source URLs are also stored on each `DJProfile`. Run `python tools/fetch_dj_photos.py` only when deliberately refreshing the bundled thumbnails; check the Commons source and license again before replacing any file.
