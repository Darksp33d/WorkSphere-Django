# Generated by Django 5.0.3 on 2024-07-11 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worksphere', '0005_alter_email_sender_alter_email_subject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='body',
            field=models.TextField(blank=True),
        ),
    ]
