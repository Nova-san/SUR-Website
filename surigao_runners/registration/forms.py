from django import forms
from datetime import date
from .models import Runner, Distance, Event
from django.core.exceptions import ValidationError
import re


class RunnerRegistrationForm(forms.ModelForm):
    class Meta:
        model = Runner
        fields = [
            'event', 'distance', 'name', 'email', 'contact_number',
            'age', 'gender', 'shirt_size',
            'emergency_contact_name', 'emergency_contact_number',
            'proof_of_payment'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today()
        self.fields['event'].queryset = Event.objects.filter(date__gte=today)
        self.fields['distance'].queryset = Distance.objects.none()

        if 'event' in self.data:
            try:
                event_id = int(self.data.get('event'))
                self.fields['distance'].queryset = Distance.objects.filter(event_id=event_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and getattr(self.instance, 'event', None):
            self.fields['distance'].queryset = self.instance.event.distances.all()

    def clean_name(self):
        raw = self.cleaned_data.get('name', '').strip()
        parts = raw.split()
        if len(parts) >= 2:
            # Assume last word is the surname
            first_name = " ".join(parts[:-1])
            last_name = parts[-1]
            return f"{last_name}, {first_name}"
        return raw  # fallback for single names

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        event = self.cleaned_data.get('event')

        if event and Runner.objects.filter(email=email, event=event).exists():
            raise ValidationError("❌ This email is already registered for this event.")
        return email

    def clean_contact_number(self):
        number = self.cleaned_data.get('contact_number', '').strip()
        if not re.match(r'^(09\d{9}|\+639\d{9})$', number):
            raise forms.ValidationError("❌ Invalid number. Use format 09XXXXXXXXX or +639XXXXXXXXX.")
        return number

    def clean_proof_of_payment(self):
        file = self.cleaned_data.get('proof_of_payment')
        if file:
            if not file.content_type.startswith('image/'):
                raise ValidationError("❌ Only image files are allowed (JPG, PNG, etc).")
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("❌ File size must be under 5MB.")
        return file

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        event = cleaned_data.get('event')

        if name and email and event:
            existing = Runner.objects.filter(name__iexact=name, event=event)
            for runner in existing:
                if runner.email.lower() != email:
                    raise forms.ValidationError(
                        "⚠️ This name is already registered for this event using a different email address. "
                        "Please use the same email or double-check your details."
                    )
        return cleaned_data


class RunnerExportForm(forms.Form):
    AGE_CATEGORY_CHOICES = [
        ('20_below', '20 and below'),
        ('21_29', '21–29'),
        ('30_39', '30–39'),
        ('40_49', '40–49'),
        ('50_59', '50–59'),
        ('60_75', '60–75'),
    ]

    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        required=False,
        label="Event",
        empty_label="Select an event"
    )

    distance = forms.ModelChoiceField(
        queryset=Distance.objects.none(),
        required=False,
        label="Distance",
        empty_label="Select a distance"
    )

    shirt_size = forms.ChoiceField(
        choices=[('', 'Select a shirt size')] + list(Runner.SHIRT_SIZES),
        required=False,
        label="Shirt Size"
    )

    gender = forms.ChoiceField(
        choices=[('', 'Select gender')] + list(Runner.GENDER_CHOICES),
        required=False,
        label="Gender"
    )

    is_verified = forms.ChoiceField(
        choices=[('', 'Select verification status'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        label="Verified?"
    )

    age_category = forms.ChoiceField(
        choices=[('', 'Select age category')] + AGE_CATEGORY_CHOICES,
        required=False,
        label="Age Category"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today()
        self.fields['event'].queryset = Event.objects.filter(date__gte=today)
        self.fields['distance'].queryset = Distance.objects.none()

        if 'event' in self.data:
            try:
                event_id = int(self.data.get('event'))
                self.fields['distance'].queryset = Distance.objects.filter(event_id=event_id)
            except (ValueError, TypeError):
                pass
        elif self.initial.get('event'):
            try:
                event = self.initial.get('event')
                event_id = event.id if hasattr(event, 'id') else int(event)
                self.fields['distance'].queryset = Distance.objects.filter(event_id=event_id)
            except Exception:
                pass



class EventForm(forms.ModelForm):
    class Meta:
        model  = Event
        fields = ['name','date','poster','description']

class DistanceForm(forms.ModelForm):
    PRESET_DISTANCES = [
        ('3', '3 KM'),
        ('5', '5 KM'),
        ('10', '10 KM'),
        ('21', '21 KM'),
        ('42', '42 KM'),
        ('50', '50 KM'),
    ]

    label = forms.CharField(label="Distance (KM)")

    class Meta:
        model = Distance
        fields = ['event', 'label', 'fee']

    def clean_label(self):
        raw_label = self.cleaned_data['label']

        # Extract the numeric part (e.g. from "5K", "10km", "21 KM")
        match = re.search(r'(\d+)', raw_label)
        if not match:
            raise ValidationError("Please include a numeric distance (e.g. '5K', '21km', '10 KM').")

        numeric_label = match.group(1)  # "5" from "5K", "10" from "10 KM"
        return numeric_label

class EventSelectForm(forms.Form):
    AGE_CATEGORY_CHOICES = [
        ('', '—'),
        ('20_below', '20 and below'),
        ('21_29', '21–29'),
        ('30_39', '30–39'),
        ('40_49', '40–49'),
        ('50_59', '50–59'),
        ('60_75', '60–75'),
    ]

    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        label="Event",
        required=True
    )
    distance = forms.ModelChoiceField(
        queryset=Distance.objects.all(),
        required=False,
        label="Distance"
    )
    shirt_size = forms.ChoiceField(
        choices=[('', '—')] + Runner.SHIRT_SIZES,
        required=False,
        label="Shirt Size"
    )
    gender = forms.ChoiceField(
        choices=[('', '—')] + Runner.GENDER_CHOICES,
        required=False,
        label="Gender"
    )
    is_verified = forms.ChoiceField(
        choices=[('', '—'), ('yes', 'Yes'), ('no','No')],
        required=False,
        label="Verified?"
    )
    age_category = forms.ChoiceField(
        choices=AGE_CATEGORY_CHOICES,
        required=False,
        label="Age Category"
    )

    search = forms.CharField(
        required=False,
        label="Search Name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Juan Dela Cruz"})
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today()
        self.fields['event'].queryset = Event.objects.filter(date__gte=today)
        self.fields['distance'].queryset = Distance.objects.none()

        if 'event' in self.data:
            try:
                event_id = int(self.data.get('event'))
                self.fields['distance'].queryset = Distance.objects.filter(event_id=event_id)
            except (ValueError, TypeError):
                pass
