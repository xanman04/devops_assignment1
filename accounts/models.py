# Copyright © 2026 Xander Chen. All rights reserved.
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.deconstruct import deconstructible

from discovery.validators import http_url


def avatar_path(instance, filename):
    return f"avatars/{uuid4().hex}{Path(filename).suffix.lower()}"


@deconstructible
class HostValidator:
    """Only accept a link that really points at the named service, so a field cannot hold any other site."""

    def __init__(self, label, *domains):
        self.label, self.domains = label, domains

    def __call__(self, value):
        host = (urlsplit(value).hostname or "").lower()
        if not any(host == domain or host.endswith("." + domain) for domain in self.domains):
            raise ValidationError(f"Use a link to your {self.label} profile.")

    def __eq__(self, other):
        return isinstance(other, HostValidator) and (self.label, self.domains) == (other.label, other.domains)


class User(AbstractUser):
    display_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    avatar = models.ImageField(upload_to=avatar_path, blank=True)
    bio = models.CharField(max_length=280, blank=True, help_text="A line or two about you and the music you like.")
    instagram_url = models.URLField(max_length=2048, blank=True, validators=[http_url, HostValidator("Instagram", "instagram.com")])
    spotify_url = models.URLField(max_length=2048, blank=True, validators=[http_url, HostValidator("Spotify", "spotify.com")])
    apple_music_url = models.URLField(max_length=2048, blank=True, validators=[http_url, HostValidator("Apple Music", "music.apple.com")])
    soundcloud_url = models.URLField(max_length=2048, blank=True, validators=[http_url, HostValidator("SoundCloud", "soundcloud.com")])

    SOCIALS = (("instagram", "Instagram"), ("spotify", "Spotify"), ("apple_music", "Apple Music"), ("soundcloud", "SoundCloud"))

    @property
    def public_name(self):
        return self.display_name or self.username

    @property
    def social_links(self):
        """The connected profiles, in a fixed order, as dicts the profile template can loop over."""
        return [{"platform": key, "icon": key.replace("_", "-"), "label": label, "url": getattr(self, f"{key}_url")}
                for key, label in self.SOCIALS if getattr(self, f"{key}_url")]
