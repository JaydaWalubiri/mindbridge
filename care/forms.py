from django import forms
from django.utils import timezone
from .models import Session

class SessionForm(forms.ModelForm):
    starts_at = forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(
        date_attrs={"type": "date"}, time_attrs={"type": "time", "step": "900"}))

    class Meta:
        model = Session
        fields = ["starts_at"]

    def clean_starts_at(self):
        value = self.cleaned_data["starts_at"]
        if value <= timezone.now():
            raise forms.ValidationError("Choose a future date and time.")
        return value
