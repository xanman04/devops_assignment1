from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "display_name", "email"]
        help_texts = {"email": "Optional and private. Email recovery is not available yet."}


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["display_name", "email"]
        help_texts = {"email": "Optional and private. Email recovery is not available yet."}
