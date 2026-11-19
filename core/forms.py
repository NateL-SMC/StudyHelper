from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Task

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "notes", "due_date", "priority", "status")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What do you need to do?"}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Notes / links (optional)"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
