from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.core.validators import MinValueValidator

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gestion_api', '0008_add_payment_status_to_sale'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='workflow_state',
            field=models.CharField(choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('ready_for_delivery', 'Ready for Delivery'), ('partially_delivered', 'Partially Delivered'), ('delivered', 'Delivered'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=50),
        ),
        migrations.AddField(
            model_name='sale',
            name='delivery_notes',
            field=models.ManyToManyField(blank=True, related_name='sales', to='gestion_api.deliverynote'),
        ),
        migrations.CreateModel(
            name='AccountPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, validators=[MinValueValidator(0)])),
                ('date', models.DateField()),
                ('reference', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gestion_api.client')),
                ('sale', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='gestion_api.sale')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
