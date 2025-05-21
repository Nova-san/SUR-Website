from django.test import TestCase

from django.core.mail import send_mail
send_mail(
    subject='Test from SUR app',
    message='If you get this, SMTP works!',
    from_email='Surigao Ultra Runners <suractive@yahoo.com>',
    recipient_list=['your_email@gmail.com'],
    fail_silently=False,
)
