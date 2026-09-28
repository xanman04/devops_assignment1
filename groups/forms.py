from django import forms
from .models import AttendanceGroup


class GroupForm(forms.ModelForm):
    # Decode/re-encode in the service rather than ModelForm.save().
    photo = forms.FileField(required=False, help_text="JPG, PNG or WebP; up to 5 MiB and 20 megapixels. No animation.")
    remove_photo = forms.BooleanField(required=False)
    description = forms.CharField(max_length=2000, widget=forms.Textarea)

    class Meta:
        model = AttendanceGroup
        fields = ["name", "description", "capacity", "joining_mode"]


class MessageForm(forms.Form):
    body = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 4}), label="Message")


class JoinForm(forms.Form):
    confirm_switch = forms.BooleanField(required=False, label="Leave my current group for this event and join this group")


class BanForm(forms.Form):
    reason = forms.CharField(max_length=2000, required=False, widget=forms.Textarea)
