from django import forms
from .models import JobSeeker

class ResumeForm(forms.ModelForm):
    class Meta:
        model = JobSeeker
        fields = ['resume']