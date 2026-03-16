from django import forms
from django.contrib.auth.models import User
from .models import Profile  
from .models import Exam, Question, Option
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Teacher


class TeacherProfileEditForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, 
        required=True,
        help_text=""
    )
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(
        required=True,
        help_text="Enter a valid email address."
    )
    # phone = forms.CharField(
    #     max_length=15, 
    #     required=False, 
    #     help_text="Optional. Format: +1234567890 or 0123456789"
    # )
    profile_picture = forms.ImageField(required=False)
    qualification = forms.CharField(max_length=255, required=False, label="Qualification")
    experience = forms.IntegerField(required=False, label="Years of Experience")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        help_texts = {'username': None}  # Removes Django's default help text

    def __init__(self, *args, **kwargs):
        """ Populate profile fields if user has a profile """
        user = kwargs.pop('user', None)  # Retrieve user from kwargs
        super().__init__(*args, **kwargs)

        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            # self.fields['phone'].initial = profile.phone
            self.fields['qualification'].initial = profile.qualification
            self.fields['experience'].initial = profile.experience

        # Ensure the user is authenticated
        if user and not user.is_authenticated:
            raise ValidationError("You must be logged in to edit your profile.")

    def clean_email(self):
        """ Ensure email is unique """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(username=self.instance.username).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_username(self):
        """ Ensure username is unique """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This username is already taken.")
        return username

    # def clean_phone(self):
    #     """ Validate phone number format """
    #     phone = self.cleaned_data.get('phone')
    #     if phone and not re.match(r'^\+?\d{10,15}$', phone):
    #         raise ValidationError("Enter a valid phone number (e.g., +1234567890 or 0123456789).")
    #     return phone

    def save(self, commit=True):
        """ Save data to both User and Profile models """
        user = super().save(commit=False)

        if commit:
            user.save()  # Save User model fields

        # Get or create associated Profile
        profile, created = Profile.objects.get_or_create(user=user)
        # profile.phone = self.cleaned_data['phone']
        profile.qualification = self.cleaned_data['qualification']
        profile.experience = self.cleaned_data['experience']

        # Save profile picture if uploaded
        if self.cleaned_data.get('profile_picture'):
            profile.profile_picture = self.cleaned_data['profile_picture']

        if commit:
            profile.save()

        return user
    
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
import re
from .models import Profile  # Assuming Profile model is already defined

class StudentProfileForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, 
        required=True,
        help_text="Required. Max 150 characters. Only letters, digits, and @/./+/-/_ allowed."
    )
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(
        required=True,
        help_text="Enter a valid email address."
    )
    phone = forms.CharField(
        max_length=15, 
        required=False, 
        help_text="Optional. Format: +1234567890 or 0123456789"
    )
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = Profile  # 'phone' is in Profile, other fields belong to User
        fields = ['phone', 'profile_picture']

    def __init__(self, *args, **kwargs):
        """ Populate user-related fields from the linked User model """
        user = kwargs.pop('user', None)  # Retrieve user from kwargs
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

        # If user is passed, ensure they are authenticated
        if user and not user.is_authenticated:
            raise ValidationError("You must be logged in to edit your profile.")

    def clean_email(self):
        """ Ensure email is unique """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(username=self.instance.user.username).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_username(self):
        """ Ensure username is unique """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_phone(self):
        """ Validate phone number format """
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^\+?\d{10,15}$', phone):
            raise ValidationError("Enter a valid phone number (e.g., +1234567890 or 0123456789).")
        return phone

    def save(self, commit=True):
        """ Save data to both User and Profile models """
        profile = super().save(commit=False)
        user = profile.user

        # Update user fields
        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile.save()
        
        return profile


class ExamForm(forms.ModelForm):
    TIME_LIMIT_CHOICES = [
        (30, "30 Minutes"),
        (60, "1 Hour"),
        (90, "1 Hour 30 Minutes"),
        (120, "2 Hours"),
        (150, "2 Hours 30 Minutes"),
        (180, "3 Hours"),
        # ('custom', "Custom"),  # Custom option added
    ]

    time_limit = forms.ChoiceField(
        choices=TIME_LIMIT_CHOICES,
        widget=forms.Select(attrs={"onchange": "toggleCustomTimeField()"}),  
        required=True
    )
    
    # Custom time limit field (hidden by default)
    """
    custom_time_limit = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter custom time in minutes', 'style': 'display:none;'})
    )
    """

    passing_grade = forms.IntegerField(
        required=True,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter passing grade (%)'})
    )

    class Meta:
        model = Exam
        fields = ['subject', 'date', 'time_limit', 'rules', 'expiry_date', 'passing_grade']  # Removed 'custom_time_limit'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefill custom time if a non-standard time is used
        """
        if self.instance and self.instance.time_limit not in [30, 60, 90, 120, 150, 180]:
            self.fields['time_limit'].initial = 'custom'
            self.fields['custom_time_limit'].initial = self.instance.time_limit
            self.fields['custom_time_limit'].widget.attrs['style'] = 'display:block;'  # Ensure it's visible
        else:
            self.fields['custom_time_limit'].initial = None  # Reset custom field if standard time is used
            self.fields['custom_time_limit'].widget.attrs['style'] = 'display:none;'
        """

    def clean(self):
        cleaned_data = super().clean()
        time_limit = cleaned_data.get("time_limit")
        """
        custom_time_limit = cleaned_data.get("custom_time_limit")

        # Validate custom time input if 'custom' is selected
        if time_limit == 'custom':
            if not custom_time_limit:
                self.add_error('custom_time_limit', "Please enter a valid custom time limit.")
            elif custom_time_limit < 1:
                self.add_error('custom_time_limit', "Custom time must be at least 1 minute.")
            else:
                cleaned_data["time_limit"] = custom_time_limit  # Store the custom time as an integer
        """

        passing_grade = cleaned_data.get("passing_grade")

        # Ensure passing grade is within the valid range
        if passing_grade is not None and (passing_grade < 0 or passing_grade > 100):
            self.add_error('passing_grade', "Passing grade must be between 0 and 100.")

        return cleaned_data

class QuestionForm(forms.ModelForm):
    CORRECT_ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]

    correct_answer = forms.ChoiceField(choices=CORRECT_ANSWER_CHOICES, label="Correct Answer")  # ✅ Dropdown
    marks = forms.IntegerField(min_value=1, required=True, label="Marks")  # ✅ Ensuring valid input

    class Meta:
        model = Question
        fields = [
            'text',
            'option_a_text', 'option_a_image',
            'option_b_text', 'option_b_image',
            'option_c_text', 'option_c_image',
            'option_d_text', 'option_d_image',
            'correct_answer',
            'marks'
        ]


class OptionForm(forms.ModelForm):  # Ensure this class exists
    class Meta:
        model = Option
        fields = '__all__'

