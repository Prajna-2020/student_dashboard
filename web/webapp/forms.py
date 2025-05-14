from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import Department, Student, Faculty, Course, Scheme, CourseScheme,Enrollment,Event
from django.forms.widgets import DateTimeInput
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm

#Custom group creation form
class GroupCreationForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']  # Only ask for the group name

# Admin change password form
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text="Your password must contain at least 8 characters."
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'placeholder': 'Enter current password'})
        self.fields['new_password1'].widget.attrs.update({'placeholder': 'Enter new password'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Confirm new password'})

#student / faculty change password form
class UniversalPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })

# Admin edit profile form
class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

# Custom user creation forms
class BulkUserCreationForm(forms.Form):
    file = forms.FileField(label='Upload CSV')

# departments
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name']  # Fields to include in the form

#bulk upload faculty
class BulkFacultyUploadForm(forms.Form):
    file = forms.FileField(label='Upload CSV or Excel File', 
                         widget=forms.FileInput(attrs={'class': 'form-control'}))
    
#bulk upload Student
class BulkStudentUploadForm(forms.Form):
    file = forms.FileField(label='Upload CSV or Excel File', 
                         widget=forms.FileInput(attrs={'class': 'form-control'}))

from django import forms
from .models import Student, Department, Scheme

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        exclude = ['user']  # Exclude user field as it's handled separately
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'guardian_address': forms.Textarea(attrs={'rows': 3}),
            'parent_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'

        # Special handling for file input
        self.fields['profile_picture'].widget.attrs['class'] = 'custom-file-input'


from django import forms
from .models import Faculty, Department

class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = '__all__'
        exclude = ['user']  # Exclude user field as it's handled separately
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'

        # Special handling for file input
        self.fields['profile_picture'].widget.attrs['class'] = 'custom-file-input'
    
# Scheme
class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = ['scheme_name', 'is_active']
        widgets = {
            'scheme_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'faculty', 'semester', 'scheme']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'faculty': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(choices=[(i, f'Semester {i}') for i in range(1, 9)], 
                       attrs={'class': 'form-control'}),
            'scheme': forms.Select(attrs={'class': 'form-control'}),
        }

#course scheme maping
class CourseForm(forms.ModelForm):
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Course
        fields = ['course_code','course_name', 'credits', 'semester', 'internal_count', 
                 'assignment_count', 'quiz_count', 'project_count',
                 'internal_total_marks', 'assignment_total_marks',
                 'quiz_total_marks', 'project_total_marks']
        

class CourseSchemeForm(forms.ModelForm):
    class Meta:
        model = CourseScheme
        fields = ['course', 'scheme', 'scheme_year', 'internal_weightage',
                 'external_weightage']

class CourseCSVImportForm(forms.Form):
    scheme = forms.ModelChoiceField(queryset=Scheme.objects.all())
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    csv_file = forms.FileField(label='CSV File')
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV")
        return csv_file
    
#calendar
class EventForm(forms.ModelForm):
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_date', 'end_date', 'event_type', 'location', 'departments']
        widgets = {
            'start_date': DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        # Format the datetime fields
        for field in ['start_date', 'end_date']:
            if field in self.initial:
                self.initial[field] = self.initial[field].strftime('%Y-%m-%dT%H:%M')
        
        # Set initial departments for existing events
        if self.instance.pk:
            self.fields['departments'].initial = self.instance.department.all()

#Student profile form

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control-file'})
        }
    