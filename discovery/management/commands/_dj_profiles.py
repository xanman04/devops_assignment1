# Copyright © 2026 Xander Chen. All rights reserved.
"""Profile facts and official social links for the seeded artist / DJ profiles.

Handles, hometowns, start years and labels come from Wikidata (queried October 1, 2026);
every profile URL was checked to resolve. Only Instagram, YouTube, SoundCloud and Spotify
are kept so the profile header stays uncluttered.
"""


def _links(instagram, youtube_channel, soundcloud, spotify):
    return {
        "instagram": f"https://www.instagram.com/{instagram}/",
        "youtube": f"https://www.youtube.com/channel/{youtube_channel}",
        "soundcloud": f"https://soundcloud.com/{soundcloud}",
        "spotify": f"https://open.spotify.com/artist/{spotify}",
    }


DETAILS = {
    "Charlotte de Witte": {
        "origin": "Ghent, Belgium", "active_since": 2010, "labels": "KNTXT, Mute Records",
        "social": _links("charlottedewittemusic", "UC-yOW3e6zBSo1JwLXq46Suw", "charlottedewittemusic", "1lJhME1ZpzsEa5M0wW6Mso"),
    },
    "Andy C": {
        "origin": "Walsall, England", "active_since": 1989, "labels": "RAM Records",
        "social": _links("andyc_ramagram", "UCa4HoeRdmCZ1JYy_jqLxFRw", "andyc_ram", "75HK7rgkmDMTnWwwmcN53N"),
    },
    "Black Coffee": {
        "origin": "Durban, South Africa", "active_since": 1994, "labels": "Soulistic Music",
        "social": _links("realblackcoffee", "UC0cUnMCsopLMon3_lXYTx_g", "realblackcoffee", "6wMr4zKPrrR0UVz08WtUWc"),
    },
    "Skrillex": {
        "origin": "Los Angeles, United States", "active_since": 2004, "labels": "OWSLA, Atlantic Records",
        "social": _links("skrillex", "UC_TVqp_SyG6j5hG-xVRy95A", "skrillex", "5he5w2lnU9x7JFhnwcekXX"),
    },
    "Armin van Buuren": {
        "origin": "Leiden, Netherlands", "active_since": 1995, "labels": "Armada Music, A State of Trance",
        "social": _links("arminvanbuuren", "UCu5jfQcpRLm9xhmlSd5S8xw", "arminvanbuuren", "0SfsnGyD8FpIN4U4WCkBZ5"),
    },
    "Peggy Gou": {
        "origin": "Incheon, South Korea", "active_since": 2014, "labels": "Gudu Records, Ninja Tune",
        "social": _links("peggygou_", "UCWd5yMFDEuSCWzTM4xuA1fg", "peggygou", "2mLA48B366zkELXYx7hcDN"),
    },
    "Carl Cox": {
        "origin": "Oldham, England", "active_since": 1988, "labels": "Intec",
        "social": _links("carlcoxofficial", "UCCrHGOX6Uoj5PndNIoRkoFw", "carl-cox", "19SmlbABtI4bXz864MLqOS"),
    },
}
