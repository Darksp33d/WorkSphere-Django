from django.db import models
from ..models.user import CustomUser

class APIKey(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    service = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    tenant_id = models.CharField(max_length=255)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'service')