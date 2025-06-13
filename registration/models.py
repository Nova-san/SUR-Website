from django.db import models
from django.core.mail import send_mail
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

# Event model: Represents a running event
class Event(models.Model):
    name = models.CharField(max_length=255)  # Event name
    date = models.DateField()  # Event date
    description = models.TextField(blank=True, null=True)  # Optional description
    poster = models.ImageField(upload_to='event_posters/', blank=True, null=True)  # Optional event poster
    registration_deadline = models.DateField(null=True, blank=True)  # Optional deadline

    def __str__(self):
        return f"{self.name} on {self.date}"  # String representation

# Distance model: Represents a distance category for an event
class Distance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='distances')  # Related event
    label = models.CharField(max_length=10)  # Distance label (e.g., "5", "21")
    fee = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # Optional fee

    def __str__(self):
        return f"{self.label} KM – {self.event.name}"  # String representation

# Runner model: Represents a participant in an event
class Runner(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    SHIRT_SIZES = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)  # Registered event
    distance = models.ForeignKey(Distance, on_delete=models.CASCADE)  # Chosen distance
    first_name = models.CharField("First Name (with middle initial/name)", max_length=100)
    last_name = models.CharField("Last Name", max_length=100)
    email = models.EmailField(unique=True)  # Unique email for each runner
    contact_number = models.CharField(max_length=15)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    shirt_size = models.CharField(max_length=3, choices=SHIRT_SIZES)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True, null=True)
    proof_of_payment = models.ImageField(upload_to='receipts/')  # Payment receipt image
    is_verified = models.BooleanField(default=False)  # Admin verification status
    created_at = models.DateTimeField(auto_now_add=True)  # Registration timestamp
    bib_number = models.CharField(max_length=20, blank=True, null=True)  # Optional bib number

    @property
    def full_name(self):
        # Returns the runner's full name in "Last, First" format
        return f"{self.last_name}, {self.first_name}"   

    def generate_bib_number(distance):
        """
        Generates the next available bib number for a given distance.
        Format: "<distance_label> - 0001"
        Example: "10 - 0007"
        """
        prefix = str(distance.label).strip()
        existing_bibs = (
            Runner.objects
            .filter(distance=distance, bib_number__startswith=f"{prefix} -")
            .values_list('bib_number', flat=True)
        )

        max_number = 0
        for bib in existing_bibs:
            try:
                suffix = bib.split(" - ")[1]
                number = int(suffix)
                if number > max_number:
                    max_number = number
            except (IndexError, ValueError):
                continue

        next_number = max_number + 1
        return f"{prefix} - {next_number:04d}"


# Signal handler: Sends verification email when a runner is marked as verified
@receiver(pre_save, sender=Runner)
def send_verification_email(sender, instance, **kwargs_):
    if instance.pk:
        old = Runner.objects.get(pk=instance.pk)
        # Only send email if is_verified changed from False to True
        if not old.is_verified and instance.is_verified:
            subject = "✅ SUR Registration Verified – You're In!"

            context = {
                "name": instance.first_name,
                "event": instance.event.name,
                "distance": instance.distance.label,
                "date": instance.event.date.strftime("%B %d, %Y"),
            }

            # Plain text email body
            text_body = (
                f"Hi {instance.first_name},\n\n"
                f"🎉 Your registration for the following event has been officially verified:\n\n"
                f"🏁 Event: {context['event']}\n"
                f"📏 Distance: {context['distance']}\n"
                f"📅 Date: {context['date']}\n\n"
                f"You're now officially part of the race!\n"
                f"Please keep your email active for further race day details and instructions.\n\n"
                f"If you have questions, feel free to reach out to us or message the SUR Facebook Page.\n\n"
                f"See you at the starting line!\n"
                f"— Surigao Ultra Runners Team 🏃‍♂️💚"
            )

            # HTML email body using a template
            html_body = render_to_string("emails/verification_email.html", context)

            # Compose and send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                to=[instance.email]
            )
            email.attach_alternative(html_body, "text/html")
            email.send()

def generate_bib_number(distance):
    """
    Generates the next available bib number for a given distance.
    Format: "<distance_label> - 0001"
    Example: "10 - 0007"
    """
    prefix = str(distance.label).strip()
    existing_bibs = (
        Runner.objects
        .filter(distance=distance, bib_number__startswith=f"{prefix} -")
        .values_list('bib_number', flat=True)
    )

    max_number = 0
    for bib in existing_bibs:
        try:
            suffix = bib.split(" - ")[1]
            number = int(suffix)
            if number > max_number:
                max_number = number
        except (IndexError, ValueError):
            continue

    next_number = max_number + 1
    return f"{prefix} - {next_number:04d}"
