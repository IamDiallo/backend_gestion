# Generated by Django 4.2.20 on 2025-07-27 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_api', '0020_auto_20250727_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='quote',
            name='is_converted',
            field=models.BooleanField(default=False, help_text='Whether this quote has been converted to a sale'),
        ),
    ]
