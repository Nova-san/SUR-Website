from django.db import models
from django.core.mail import send_mail
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

class Event(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    poster = models.ImageField(upload_to='event_posters/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} on {self.date}"


class Distance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='distances')
    label = models.CharField(max_length=10)  # Allow just numbers like "5", "21"
    fee = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.label} KM – {self.event.name}"

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

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    distance = models.ForeignKey(Distance, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=15)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    shirt_size = models.CharField(max_length=3, choices=SHIRT_SIZES)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True, null=True)
    proof_of_payment = models.ImageField(upload_to='receipts/')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=Runner)
def send_verification_email(sender, instance, **kwargs):
    if instance.pk:
        old = Runner.objects.get(pk=instance.pk)
        if not old.is_verified and instance.is_verified:
            subject = "✅ SUR Registration Verified – You're In!"

            context = {
                "name": instance.name,
                "event": instance.event.name,
                "distance": instance.distance.label,
                "date": instance.event.date.strftime("%B %d, %Y"),
            }

            text_body = (
                f"Hi {context['name']},\n\n"
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

            html_body = render_to_string("emails/verification_email.html", context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                to=[instance.email]
            )
            email.attach_alternative(html_body, "text/html")
            email.send()


