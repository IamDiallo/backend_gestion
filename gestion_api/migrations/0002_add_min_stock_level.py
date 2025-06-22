from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_api', '0001_add_min_stock_level'),
    ]

    # operations = [
    #     migrations.AddField(
    #         model_name='product',  # Changed from 'stock' to 'product'
    #         name='min_stock_level',
    #         field=models.PositiveIntegerField(
    #             default=10,
    #             help_text="Minimum stock level before alert is triggered"
    #         ),
    #     ),
    # ]
