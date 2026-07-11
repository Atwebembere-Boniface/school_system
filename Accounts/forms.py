from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms
from Academics.models import ClassLevel
from .models import StudentProfile

User = get_user_model() # This is safer

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'phone_number']


class StudentProfileForm(forms.ModelForm):
    # This fetches all classes created by the admin for the dropdown
    current_class = forms.ModelChoiceField(
        queryset=ClassLevel.objects.all(),
        empty_label="Select Class",
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px;'})
    )

    class Meta:
        model = StudentProfile
        fields = ['registration_number', 'current_class', 'student_type']
        widgets = {
            'student_type': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px;'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 8px;', 'placeholder': 'Enter Reg No.'}),
        }        