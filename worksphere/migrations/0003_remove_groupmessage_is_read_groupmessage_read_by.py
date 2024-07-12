# Generated by Django 5.0.3 on 2024-07-12 01:52

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worksphere', '0002_alter_groupmessage_is_read'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='groupmessage',
            name='is_read',
        ),
        migrations.AddField(
            model_name='groupmessage',
            name='read_by',
            field=models.ManyToManyField(related_name='read_group_messages', to=settings.AUTH_USER_MODEL),
        ),
    ]