from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accounts', views.AccountViewSet, basename='account')
router.register(r'expenses', views.ExpenseViewSet, basename='expense')
router.register(r'client-payments', views.ClientPaymentViewSet, basename='clientpayment')
router.register(r'supplier-payments', views.SupplierPaymentViewSet, basename='supplierpayment')
router.register(r'account-transfers', views.AccountTransferViewSet, basename='accounttransfer')
router.register(r'cash-receipts', views.CashReceiptViewSet, basename='cashreceipt')
router.register(r'supplier-cash-payments', views.SupplierCashPaymentViewSet, basename='suppliercashpayment')
router.register(r'account-statements', views.AccountStatementViewSet, basename='accountstatement')

urlpatterns = [
    path('', include(router.urls)),
]
