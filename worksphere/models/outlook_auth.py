from django.db import models
from worksphere.models.user import CustomUser


class OutlookAuth(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()