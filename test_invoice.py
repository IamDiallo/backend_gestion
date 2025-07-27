from gestion_api.models import Invoice, Sale
from datetime import date, timedelta

print('Testing invoice creation...')
sales = Sale.objects.all()
print(f'Found {sales.count()} sales')

if sales.exists():
    sale = sales.first()
    print(f'Using sale: {sale.reference}')
    
    try:
        invoice = Invoice.objects.create(
            reference='TEST-001',
            sale=sale,
            date=date.today(),
            due_date=date.today() + timedelta(days=30),
            amount=1000,
            paid_amount=0,
            balance=1000
        )
        print(f'Invoice created successfully: {invoice.reference}')
        invoice.delete()
        print('Test invoice deleted')
    except Exception as e:
        print(f'Error creating invoice: {e}')
else:
    print('No sales found to test with')
