# Generated by Django 4.2.20 on 2025-05-03 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_api', '0003_alter_stock_options_remove_stock_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stock',
            name='min_stock_level',
        ),
        migrations.AlterField(
            model_name='stock',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
