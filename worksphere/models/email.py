from django.db import models
from django.contrib.auth.models import User

class Email(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outlook_emails')
    email_id = models.CharField(max_length=255, unique=True)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    received_date_time = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-received_date_time']