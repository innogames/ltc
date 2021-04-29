from .models import TestResultFile
from django import forms

class TestResultFileUploadForm(forms.ModelForm):
    class Meta:
        model = TestResultFile
        fields = ('file', )