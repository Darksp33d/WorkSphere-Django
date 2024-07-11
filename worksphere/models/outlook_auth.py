from django.db import models
from ..models.user import CustomUser as User

class OutlookAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()