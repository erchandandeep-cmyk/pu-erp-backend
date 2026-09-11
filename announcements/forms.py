from django import forms
from .models import Announcement
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "audience", "attachment", "expires_at"]
        widgets = {"body": forms.Textarea(attrs={"rows": 6}), "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
