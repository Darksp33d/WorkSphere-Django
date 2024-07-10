# In models.py
from django.db import models
from django.contrib.auth.models import User

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.CharField(max_length=100)
    key = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'worksphere'
        unique_together = ('user', 'service')