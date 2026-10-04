from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


AVATAR_WIDGET = {"accept": "image/jpeg,image/png,image/webp", "data-crop-aspect": "1", "data-crop-shape": "circle"}
PROFILE_LABELS = {"instagram_url": "Instagram", "spotify_url": "Spotify", "apple_music_url": "Apple Music", "soundcloud_url": "SoundCloud"}
PROFILE_HELP = {
    "email": "Private. Email recovery is not available yet.",
    "instagram_url": "Links only for now. Nothing is connected to or read from these accounts.",
    "spotify_url": "e.g. https://open.spotify.com/user/…",
    "apple_music_url": "e.g. https://music.apple.com/profile/…",
    "soundcloud_url": "e.g. https://soundcloud.com/…",
}


class RegistrationForm(UserCreationForm):
    """Everything on the profile can be filled in here; only the username and password are needed."""
    avatar = forms.FileField(required=False, label="Profile picture", widget=forms.FileInput(attrs=AVATAR_WIDGET),
                             help_text="JPG, PNG or WebP; up to 5 MiB. It is shown as a circle.")
    field_order = ["username", "password1", "password2", "display_name", "avatar", "bio", "email",
                   "instagram_url", "spotify_url", "apple_music_url", "soundcloud_url"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "display_name", "bio", "email", "instagram_url", "spotify_url", "apple_music_url", "soundcloud_url"]
        labels = PROFILE_LABELS
        widgets = {"bio": forms.Textarea(attrs={"rows": 3, "maxlength": 280})}
        help_texts = PROFILE_HELP

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Letters, digits and @ . + - _ only. This is how people find you."
        self.fields["password1"].help_text = "At least 8 characters. Not a common password, not only numbers, and not too similar to your username."
        self.fields["password2"].help_text = "Type the same password again."
        self.fields["display_name"].help_text = "Shown instead of your username."


class AccountSettingsForm(forms.ModelForm):
    avatar = forms.FileField(required=False, label="Profile picture", widget=forms.FileInput(attrs={
        "accept": "image/jpeg,image/png,image/webp", "data-crop-aspect": "1", "data-crop-shape": "circle"}), help_text="JPG, PNG or WebP; up to 5 MiB. It is shown as a circle.")

    field_order = ["avatar"]

    class Meta:
        model = User
        fields = ["display_name", "bio", "email", "instagram_url", "spotify_url", "apple_music_url", "soundcloud_url"]
        labels = {"instagram_url": "Instagram", "spotify_url": "Spotify", "apple_music_url": "Apple Music", "soundcloud_url": "SoundCloud"}
        widgets = {"bio": forms.Textarea(attrs={"rows": 3, "maxlength": 280})}
        help_texts = {
            "email": "Optional and private. Email recovery is not available yet.",
            "instagram_url": "Links only for now. Nothing is connected to or read from these accounts.",
            "spotify_url": "e.g. https://open.spotify.com/user/…",
            "apple_music_url": "e.g. https://music.apple.com/profile/…",
            "soundcloud_url": "e.g. https://soundcloud.com/…",
        }
