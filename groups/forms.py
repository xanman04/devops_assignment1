# Copyright © 2026 Xander Chen. All rights reserved.
from django import forms
from .models import AttendanceGroup


class GroupForm(forms.ModelForm):
    # Decode/re-encode in the service rather than ModelForm.save().
    photo = forms.FileField(required=False, widget=forms.FileInput(attrs={
        "accept": "image/jpeg,image/png,image/webp", "data-crop-aspect": "1.333"}), help_text="JPG, PNG or WebP; up to 5 MiB and 20 megapixels. No animation.")
    description = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 5}))

    class Meta:
        model = AttendanceGroup
        fields = ["name", "description", "capacity", "joining_mode"]


class MessageForm(forms.Form):
    body = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 1, "placeholder": "Write a message…"}), label="Message")


class JoinForm(forms.Form):
    confirm_switch = forms.BooleanField(required=False)   # set by the confirmation popup when the person already has a group for this event


class BanForm(forms.Form):
    reason = forms.CharField(max_length=2000, required=False, widget=forms.Textarea)
