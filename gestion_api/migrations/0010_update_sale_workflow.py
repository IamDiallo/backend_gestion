from django.db import migrations

def update_sale_statuses(apps, schema_editor):
    """
    Update existing sales to use the new workflow status values
    """
    Sale = apps.get_model('gestion_api', 'Sale')
    
    # Map old statuses to new ones
    status_mapping = {
        'draft': 'pending',
        'confirmed': 'confirmed',
        # Keep delivered as is
        # Keep cancelled as is
    }
    
    # Update sales with old status values
    for old_status, new_status in status_mapping.items():
        Sale.objects.filter(status=old_status).update(
            status=new_status, 
            workflow_state=new_status
        )
    
    # Update workflow state for delivered sales to match status
    Sale.objects.filter(status='delivered').update(workflow_state='delivered')
    Sale.objects.filter(status='cancelled').update(workflow_state='cancelled')
    
    # Update sales with payment status 'paid' to have the correct workflow state
    Sale.objects.filter(payment_status='paid', status='confirmed').update(
        status='paid',
        workflow_state='paid'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_api', '0009_add_accountpayment'),
    ]

    operations = [
        migrations.RunPython(update_sale_statuses, migrations.RunPython.noop),
    ]
