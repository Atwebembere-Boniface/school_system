from django import forms
from Accounts.models import User
from .models import StudentProfile, Result, Material, CourseAssignment, ClassLevel
from django.contrib.auth import get_user_model

# Get the custom user model safely
User = get_user_model()

class StudentRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = StudentProfile
        # Included 'gender' in the fields list
        fields = ['registration_number', 'current_class', 'student_type', 'gender']
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'current_class': forms.Select(attrs={'class': 'form-control'}),
            'student_type': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}), # Added gender widget
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def save(self, commit=True):
        # 1. Create the User account
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password'],
            role='STUDENT'
        )
        
        # 2. Create the profile instance with the new gender field
        profile = StudentProfile(
            user=user,
            registration_number=self.cleaned_data['registration_number'],
            current_class=self.cleaned_data['current_class'],
            student_type=self.cleaned_data['student_type'],
            gender=self.cleaned_data['gender'] # Added this line
        )
        
        if commit:
            profile.save()
        return profile
    


class BulkMarkForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'score', 'term']
        widgets = {
            'student': forms.HiddenInput(),
            'score': forms.NumberInput(attrs={'class': 'mark-input', 'min': 0, 'max': 100}),
            'term': forms.Select(attrs={'class': 'term-input', 'class': 'form-control'}),
        }    

class CourseAssignmentForm(forms.ModelForm):
    class_levels = forms.ModelMultipleChoiceField(
        queryset=ClassLevel.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'list-unstyled'}),
        help_text="Select all classes taught by this teacher for this subject."
    )

    class Meta:
        model = CourseAssignment
        fields = ['teacher', 'subject', 'class_levels', 'academic_session']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'academic_session': forms.Select(attrs={'class': 'form-control'}),
        }

# Academics/forms.py

class MaterialUploadForm(forms.ModelForm):
    # This allows the teacher to pick specific classes
    target_classes = forms.ModelMultipleChoiceField(
        queryset=ClassLevel.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'class-checkbox-list'}),
        required=True,
        help_text="Select one or more classes that should see these notes."
    )

    class Meta:
        model = Material
        fields = ['title', 'material_type', 'assignment', 'target_classes', 'file']

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        if teacher:
            # Only show classes this teacher is actually assigned to
            self.fields['target_classes'].queryset = ClassLevel.objects.filter(
                course_assignments__teacher=teacher
            ).distinct()
            # Only show subject assignments for this teacher
            self.fields['assignment'].queryset = CourseAssignment.objects.filter(teacher=teacher)



class StudentEditForm(forms.ModelForm):
    """
    Form for editing existing students. 
    It doesn't require a password and updates the existing profile.
    """
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = StudentProfile
        # We include gender so the Admin can change it from the default
        fields = ['registration_number', 'current_class', 'student_type', 'gender']
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'current_class': forms.Select(attrs={'class': 'form-control'}),
            'student_type': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        # 1. Update the linked User model fields (First/Last name)
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            profile.save()
        return profile            