from django.db import models
from worksphere.models.user import CustomUser


class SlackAuth(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Slack Auth"
