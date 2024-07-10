from django.db import models
from django.contrib.auth.models import User

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.CharField(max_length=100)
    client_id = models.CharField(max_length=500, blank=True, null=True)
    tenant_id = models.CharField(max_length=500, blank=True, null=True)
    client_secret = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'service')
        app_label = 'worksphere'  # Add this line