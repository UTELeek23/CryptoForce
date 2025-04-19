from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import User, Problem, Submission
from tinymce.widgets import TinyMCE

class LoginForm(AuthenticationForm):
    """Form for user login"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class RegisterForm(UserCreationForm):
    """Form for user registration"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Tell us about yourself', 'rows': 3})
    )
    country = forms.CharField(
        required=False,
        initial="Global",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your country'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'bio', 'country', 'avatar')
        
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
        
    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.bio = self.cleaned_data['bio']
        user.country = self.cleaned_data['country']
        
        if commit:
            user.save()
            # Create initial ELO history record
            from .models import EloHistory
            EloHistory.objects.create(
                user=user,
                elo_before=1500,
                elo_after=1500,
                change=0,
                change_type='INITIAL',
                description='Initial ELO rating'
            )
            
        return user

class EditProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Tell us about yourself', 'rows': 3})
    )
    
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your country'})
    )
    
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password to confirm changes'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'bio', 'country', 'avatar')
        
    def clean_current_password(self):
        """Validate that the current password is correct"""
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.instance.check_password(current_password):
            raise forms.ValidationError("The current password is incorrect.")
        return current_password
    
    def save(self, commit=True):
        """Save the model instance with the updated data"""
        user = super().save(commit=False)
        if commit:
            user.save()
            if 'avatar' in self.changed_data and self.cleaned_data['avatar']:
                # If the avatar has changed and a new one was uploaded, save it
                user.avatar = self.cleaned_data['avatar']
                user.save()
        return user

class ProblemForm(forms.ModelForm):
    """Form for creating and editing problems"""
    title = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Problem Title'})
    )
    
    description = forms.CharField(
        required=True,
        widget=TinyMCE()
    )
    
    difficulty = forms.IntegerField(
        required=True,
        initial=1500,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Difficulty Rating (ELO)',
            'min': 1000,
            'max': 3000
        })
    )
    
    DIFFICULTY_CHOICES = [
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
        ('EXPERT', 'Expert'),
    ]
    
    difficulty_level = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    points = forms.IntegerField(
        required=True,
        initial=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Points',
            'min': 50,
            'max': 1000
        })
    )
    
    flag = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Flag (e.g., crypto_force{flag_text})'
        })
    )
    
    category = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Category (e.g., Cryptography, Web Exploitation)'
        })
    )
    
    solution = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Solution or writeup (optional)',
            'rows': 4
        })
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Problem
        fields = ('title', 'description', 'difficulty', 'difficulty_level', 'points', 'flag', 'category', 'solution', 'is_active')

    def clean_flag(self):
        flag = self.cleaned_data.get('flag')
        # Check if flag follows the correct format
        if not flag.startswith('crypto_force{') or not flag.endswith('}'):
            raise forms.ValidationError(
                "Flag must follow the format: crypto_force{flag_text}"
            )
        return flag

class HintForm(forms.Form):
    """Form for creating problem hints"""
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Hint content',
            'rows': 3
        })
    )
    
    cost = forms.IntegerField(
        required=True,
        initial=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Point cost',
            'min': 0,
            'max': 100
        })
    )

class SubmissionForm(forms.ModelForm):
    """Form for submitting solutions to problems"""
    submitted_flag = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control flag-input',
            'placeholder': 'crypto_force{...}'
        })
    )
    
    class Meta:
        model = Submission
        fields = ('submitted_flag',)