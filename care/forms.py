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


class AvailabilityForm(forms.Form):
    counsellor = forms.ModelChoiceField(queryset=None, required=False)
    starts_at = SessionForm.base_fields["starts_at"]

    def clean_starts_at(self):
        value = self.cleaned_data["starts_at"]
        if value <= timezone.now():
            raise forms.ValidationError("Choose a future date and time.")
        return value

    def __init__(self, *args, user, **kwargs):
        from django.contrib.auth import get_user_model
        super().__init__(*args, **kwargs)
        self.fields["counsellor"].queryset = get_user_model().objects.filter(is_active=True, care_profile__isnull=False)
        if not user.is_staff:
            self.fields.pop("counsellor")
