from django import forms

from .models import seekerdb


class ResumeForm(forms.ModelForm):
    class Meta:
        model = seekerdb
        fields = ["resume"]

