# Generated by Django 4.2.20 on 2025-05-18 14:30

from django.db import migrations

def update_draft_workflow_states(apps, schema_editor):
    """
    Update any remaining sales with 'draft' workflow state to 'pending'
    """
    Sale = apps.get_model('gestion_api', 'Sale')
    
    # Find and update any sales that still have 'draft' as workflow_state
    draft_sales = Sale.objects.filter(workflow_state='draft')
    draft_sales.update(workflow_state='pending')
    
    # For completeness, make sure all sales have their workflow_state matching their status
    for sale in Sale.objects.all():
        if sale.workflow_state != sale.status:
            sale.workflow_state = sale.status
            sale.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_api', '0011_alter_accountpayment_options_and_more'),
    ]    
    operations = [
        migrations.RunPython(update_draft_workflow_states, migrations.RunPython.noop),
    ]
    
