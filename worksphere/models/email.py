from django.db import models
from worksphere.models.user import CustomUser


class Email(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='outlook_emails')
    email_id = models.CharField(max_length=255, unique=True)
    sender = models.CharField(max_length=255, default='Unknown')
    subject = models.CharField(max_length=255, default='(No subject)')
    body = models.TextField(blank=True)
    received_date_time = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-received_date_time']
