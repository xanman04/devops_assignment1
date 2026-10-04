"""Curated listening links for the seeded artist / DJ profiles.

Each profile lists its most-listened songs (kind "track", roughly by popularity)
and past sets or mixes (kind "set", roughly by views). Producers and DJs with
releases get both lists; Carl Cox is treated as a DJ only, so his list is sets.
Links point at the artist's, label's, promoter's or broadcaster's own uploads
(SoundCloud, or YouTube). Bassline stores URLs and titles only; no audio is copied.
Gathered from YouTube search results on October 1, 2026; popularity order follows
the view counts shown then.
"""


def yt(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def sc(path):
    return f"https://soundcloud.com/{path}"


def track(title, url, platform="youtube"):
    return ("track", title, platform, url)


def mix(title, url, platform="youtube"):
    return ("set", title, platform, url)


MEDIA = {
    "Charlotte de Witte": [
        track("Doppler", yt("AS8Q_5knkrg")),
        track("Overdrive", yt("u1v-TN6j0Rk")),
        track("High Street", yt("vJtTq0JDTyY")),
        track("Sgadi Li Mi", yt("4qJdigju5UM")),
        track("Apollo", yt("uxNjgtFTkLE")),
        track("The Age of Love (Charlotte de Witte & Enrico Sangiuliano Remix)", sc("charlottedewittemusic/theageofloveremix"), "soundcloud"),
        track("Return To Nowhere", yt("XxOym1jIPBc")),
        track("Rave On Time", yt("WnCjczaFg8U")),
        track("Selected", yt("SnnwwWY4uMU")),
        track("Vision", yt("Kgy9UJp3PSg")),
        mix("‘New Form’ III: Rave On Time", yt("mgtu7u9PKkI")),
        mix("Dour Festival 2017 for Cercle", yt("AtZxg-OC5ho")),
        mix("Tomorrowland KNTXT Stage 2022", sc("charlottedewittemusic/tomorrowlandkntxtstage2022"), "soundcloud"),
        mix("Tomorrowland Belgium 2025 · Main Stage closing", yt("fjnSF0K70q4")),
        mix("Tomorrowland Belgium 2019 · KNTXT Stage", yt("6E3TKJ3scww")),
        mix("The Lab NYC · Mixmag", yt("Q9dzq_SWd3k")),
        mix("Pukkelpop 2018 · Boiler Room", yt("er2lzvlfPCE")),
        mix("Awakenings Festival 2019 · Area V", yt("8YGTMZxxcno")),
        mix("Castelo de S. Jorge, Lisbon · DJ Mag", yt("8NUiR9ZloPo")),
    ],
    "Andy C": [
        track("Get Free (Andy C Remix) · Major Lazer", yt("6_8ZZtL6qmM")),
        track("Heartbeat Loud (feat. Fiora)", sc("andyc_ram/andy-c-heartbeat-loud-ft-fiora"), "soundcloud"),
        track("Heartbeat Loud (Andy C VIP) · with Fiora", yt("CizqApSwfjQ")),
        track("Haunting", yt("It-Wzg0UZsw")),
        track("Take Me Away (Andy C Remix) · DJ S.K.T", yt("G_5nb-CwJms")),
        track("Back & Forth", yt("wT8dXnyCsXg")),
        track("Workout", yt("cRyJdrMZLRo")),
        track("Indestructible · with Becky Hill", yt("MW8Z2btfMV4")),
        mix("Rampage 2018 · with MC Tonn Piper", yt("5PwXNb5Bbbo")),
        mix("Rampage 2019 · with MC Tonn Piper", yt("mhGx7xeyNp8")),
        mix("DnB Allstars 360°", yt("VISIvMP8kl4")),
        mix("One7Four Stream · D&BTV Locked In x UKF On Air", yt("BnhBK8yyG-U")),
        mix("Boiler Room: London", yt("23Oh1LHavuE")),
        mix("Radio 1 Residency Mix · April 2022", sc("andyc_ram/andy-c-radio-1-residency-mix-28042022"), "soundcloud"),
        mix("Rampage Total Takeover 2023", yt("pp3sxUyO8qg")),
        mix("Radio 1 Essential Mix · live from Glastonbury 2015", yt("Eko2ph8HuK4")),
        mix("Ultra Miami 2026 · Worldwide Stage", yt("QrggpHiltfM")),
        mix("EDC Las Vegas 2025 · Basspod", yt("lIAalwQyE7E")),
        mix("Live from KOKO · 30 Years of The End", yt("q5xA-7Auy24")),
    ],
    "Black Coffee": [
        track("Drive · with David Guetta, feat. Delilah Montagu", yt("32HANv-bdJs")),
        track("You Turn Me On", yt("do9oJ41Qsck")),
        track("Superman (feat. Bucie)", sc("realblackcoffee/superman-1"), "soundcloud"),
        track("Your Eyes (feat. Shekhinah)", yt("PPUyHWWrQzE")),
        track("Wish You Were Here (feat. Msaki)", yt("17zOUL27cJk")),
        track("Come With Me (feat. Mque)", yt("osQUJTBGCMs")),
        track("We Dance Again (feat. Nakhane)", yt("JjWaET5AWCw")),
        track("10 Missed Calls (feat. Pharrell Williams & Jozzy)", yt("u6miHa1MoYM")),
        mix("Cercle · Salle Wagram, Paris", yt("SGqg_ZzThDU")),
        mix("Mixmag Live, London", yt("wamL0A9Qzxg")),
        mix("Tomorrowland Belgium 2019", yt("xB-mSCeDqUE")),
        mix("Sunset set from DJ Mag HQ, Ibiza", yt("ifJQQkbuijQ")),
        mix("The Lab LDN · Mixmag", yt("f0coQKqxzU0")),
        mix("Tomorrowland Belgium 2018", yt("B3ObxaSCY9Y")),
        mix("Mayan Warrior · Burning Man 2025", yt("FH7lIOv1s3Q")),
        mix("Boiler Room · Stay True South Africa", yt("9JtTbx-hYWk")),
        mix("Boiler Room · ADE x Bridges For Music", yt("DuzhuGtaHkg")),
        mix("DJ Mix", sc("realblackcoffee/dj-mix"), "soundcloud"),
    ],
    "Skrillex": [
        track("Where Are Ü Now · with Diplo & Justin Bieber", yt("nntGTK2Fhb0")),
        track("Bangarang (feat. Sirah)", sc("skrillex/skrillex-bangarang-feat-sirah"), "soundcloud"),
        track("First of the Year (Equinox)", yt("2cXDgFwE13g")),
        track("Scary Monsters and Nice Sprites", yt("WSeNSzJ2-Jw")),
        track("Ragga Bomb (feat. Ragga Twins)", yt("8eJDTcDUQxQ")),
        track("Kyoto (feat. Sirah)", yt("86khmc6y1yE")),
        track("Rock n Roll (Will Take You to the Mountain)", yt("eOofWzI3flA")),
        track("Make It Bun Dem · with Damian “Jr. Gong” Marley", yt("PR_u9rvFKzE")),
        track("Cinema (Skrillex Remix) · Benny Benassi", yt("Ua0KpfJsxKo")),
        track("Rumble · with Fred again.. & Flowdan", yt("7z25ZZ3DHds")),
        mix("Ultra Music Festival 2015", yt("V2VmcuOEqEg")),
        mix("Jack Ü · Ultra Music Festival 2014", yt("GjHf2ckHkeo")),
        mix("Ultra Music Festival 2025", yt("ni2pGkTPLDo")),
        mix("Boiler Room x IMS Asia-Pacific x OWSLA · Shanghai", yt("PRlLNfKYm8U")),
        mix("Tomorrowland 2012", yt("M4N-9hVBW2M")),
        mix("Four Tet, Fred again.. & Skrillex · Times Square for The Lot Radio", yt("ahe9baHOWIg")),
        mix("Baby again.. · Fred again.. x Four Tet x Skrillex, New York 2023", yt("odI4cpFXhq8")),
    ],
    "Armin van Buuren": [
        track("Blah Blah Blah", yt("mfJhMfOPWdE")),
        track("In And Out Of Love (feat. Sharon den Adel)", yt("TxvpctgU_s8")),
        track("Great Spirit · with Vini Vici, feat. Hilight Tribe", yt("yo4pmauhugo")),
        track("This Is What It Feels Like (feat. Trevor Guthrie)", sc("arminvanbuuren/armin-van-buuren-feat-trevor-guthrie-this-is-what-it-feels-like"), "soundcloud"),
        track("Intense (feat. Miri Ben-Ari)", yt("6UoNXz0Ox-g")),
        track("Love You More (feat. Racoon)", yt("71WK5gtTh64")),
        track("Communication", yt("bn1ycNxQMvk")),
        track("Shivers (feat. Susana)", yt("5GowkwJN-qU")),
        mix("Tomorrowland 2018", yt("79nFO8dTJfY")),
        mix("Mysteryland 2022 · Mainstage", yt("ZtmIokzkeyA")),
        mix("Ultra Music Festival Miami 2017 · ASOT Stage", yt("cLcKew4cQq4")),
        mix("Armin Only: Intense · The Final Show", yt("F-7OFftB43w")),
        mix("FSOE 500 · Pyramids of Giza", yt("DtaZsqKDlBo")),
        mix("The Best Of Armin Only · Johan Cruijff ArenA", yt("vDe9pO6P84Q")),
        mix("Ushuaïa, Ibiza 2023", yt("l-TUrm26VzQ")),
        mix("EDC Las Vegas 2018", yt("AbH2tJrCoAE")),
        mix("Ultra Music Festival Miami 2019 · ASOT Stage", yt("xr40tgMaD1k")),
        mix("Tomorrowland 2022 · Weekend 1", yt("QrSebQAbytY")),
        mix("A State of Trance at Ushuaïa Ibiza 2015 · minimix", sc("arminvanbuuren/armin-van-buuren-a-state-of-trance-ushuaia-ibiza-2015-minimix-out-now"), "soundcloud"),
    ],
    "Peggy Gou": [
        track("(It Goes Like) Nanana", sc("peggygou/peggy-gou-it-goes-like-2"), "soundcloud"),
        track("Starry Night", yt("r_wwmmo6UGY")),
        track("It Makes You Forget (Itgehane)", yt("SlbVgjFvE3I")),
        track("Han Jan", yt("A8S5Rd_02uA")),
        track("I Go", yt("d1gmuWdZzkw")),
        track("Lobster Telephone", yt("bLsDLxISc5w")),
        track("Wo, man (feat. Ayra Starr)", yt("CLkV6Se8JLk")),
        track("1+1=11", yt("qTSadqfWeDw")),
        mix("Cercle · Palais des Beaux-Arts de Lille", yt("-UOMvxh4MYU")),
        mix("Boiler Room x Dekmantel Festival · Amsterdam", yt("nKHpbiYCtDQ")),
        mix("Montblanc x Maison Kitsuné · Paris", yt("a4Sm1lTkf1I")),
        mix("Boiler Room: Streaming From Isolation #21", yt("jxcK_wENFgo")),
        mix("BitterSweet Festival 2025", yt("M_vDO25av6E")),
        mix("Boiler Room BUDx Seoul", yt("ApRsse-T2hc")),
        mix("Peggy Gou's mixset 01", sc("peggygou/peggy-gous-mixset-01"), "soundcloud"),
    ],
    "Carl Cox": [
        mix("Boiler Room · Ibiza Villa Takeovers", yt("vy-k0FopsmY")),
        mix("Château de Chambord, France · Cercle", yt("ZdAwiV4T22I")),
        mix("Tomorrowland 2015", yt("PCVI7qFU17c")),
        mix("Live from Melbourne · Defected We Dance As One", yt("TOu5pmcoXKQ")),
        mix("Space Opening, Ibiza · Dance TV", yt("XHms8POkG0Q")),
        mix("Mayan Warrior · Burning Man 2024", yt("BtEka3j8lKM")),
        mix("Sunset Over Scotland · Mixmag", yt("HBUfqPBD7Uo")),
        mix("Tomorrowland Belgium 2019 · Weekend 2", yt("FLFwpjGvWbQ")),
        mix("Tomorrowland Belgium 2017", yt("6KVtA5BiV6Y")),
        mix("Club Space Miami · Sunrise set", yt("CTvkbzE4Jus")),
        mix("Carl Cox Stems Mix · Boiler Room", sc("platform/carl-cox-stems-mixtape"), "soundcloud"),
        mix("Awakenings Festival 2025", yt("eFSEriPYeV0")),
    ],
}
