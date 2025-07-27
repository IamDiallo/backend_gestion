from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gestion_api import views
from .views import debug_permissions, ProductCategoryViewSet

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'permissions', views.PermissionViewSet)
router.register(r'zones', views.ZoneViewSet)
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'clients', views.ClientViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'sales', views.SaleViewSet)
router.register(r'productions', views.ProductionViewSet)
router.register(r'stock-supplies', views.StockSupplyViewSet)
router.register(r'stock-transfers', views.StockTransferViewSet)
router.register(r'inventories', views.InventoryViewSet)
router.register(r'stock-cards', views.StockCardViewSet)
router.register(r'delivery-notes', views.DeliveryNoteViewSet)
router.register(r'charge-types', views.ChargeTypeViewSet)
router.register(r'sale-charges', views.SaleChargeViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'client-groups', views.ClientGroupViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'quotes', views.QuoteViewSet)
# Uncomment these now that they have their corresponding viewsets
router.register(r'currencies', views.CurrencyViewSet)
router.register(r'exchange-rates', views.ExchangeRateViewSet)
router.register(r'payment-methods', views.PaymentMethodViewSet)
router.register(r'accounts', views.AccountViewSet)
router.register(r'price-groups', views.PriceGroupViewSet)
router.register(r'expense-categories', views.ExpenseCategoryViewSet)
router.register(r'expenses', views.ExpenseViewSet)
router.register(r'client-payments', views.ClientPaymentViewSet)
router.register(r'supplier-payments', views.SupplierPaymentViewSet)
router.register(r'account-transfers', views.AccountTransferViewSet)
router.register(r'units-of-measure', views.UnitOfMeasureViewSet)
# Add these new routers
router.register(r'cash-flows', views.CashFlowViewSet)
router.register(r'bank-reconciliations', views.BankReconciliationViewSet)
router.register(r'financial-reports', views.FinancialReportViewSet)
router.register(r'product-categories', ProductCategoryViewSet)
router.register(r'stocks', views.StockViewSet)
router.register(r'cash-receipts', views.CashReceiptViewSet)
router.register(r'account-statements', views.AccountStatementViewSet)  # Add AccountStatementViewSet

urlpatterns = [
    # Stock-specific endpoints MUST come before router.urls to avoid conflicts
    path('stocks/check_availability/', views.StockAvailabilityView.as_view(), name='stock-availability-check'),
    path('stocks/by_zone/<int:zone_id>/', views.StockViewSet.as_view({'get': 'by_zone'}), name='stocks-by-zone'),
    
    # Sales-specific endpoints
    path('sales/recalculate_payment_amounts/', views.SaleViewSet.as_view({'post': 'recalculate_payment_amounts'}), name='sales-recalculate-payments'),
    
    # Include router URLs after specific endpoints
    path('', include(router.urls)),
    
    path('dashboard/stats/', views.dashboard_stats),
    path('dashboard/recent-sales/', views.dashboard_recent_sales),
    path('dashboard/low-stock/', views.dashboard_low_stock),
    path('dashboard/inventory/', views.inventory_dashboard),  # Add new inventory dashboard endpoint
    path('reports/sales/', views.reports_sales),
    path('permissions/categorized/', views.PermissionViewSet.as_view({'get': 'categorized'})),
    path('users/<int:pk>/update_groups/', views.UserViewSet.as_view({'post': 'update_groups'})),
    # Update the permissions endpoint to use the renamed method user_permissions
    path('users/me/permissions/', views.UserViewSet.as_view({'get': 'user_permissions'})),
      # Groups endpoints
    path('groups/', include([
        path('', views.GroupViewSet.as_view({'get': 'list', 'post': 'create'}), name='group-list'),
        path('<int:pk>/', views.GroupViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), name='group-detail'),
        path('<int:pk>/users/', views.GroupViewSet.as_view({'get': 'users'}), name='group-users'),
        path('<int:pk>/add-permissions/', views.GroupViewSet.as_view({'post': 'add_permissions'}), name='group-add-permissions'),
        path('<int:pk>/remove-permissions/', views.GroupViewSet.as_view({'post': 'remove_permissions'}), name='group-remove-permissions'),
    ])),
    
    # Debug endpoints
    path('debug/groups/', views.DebugGroupView.as_view(), name='debug-groups'),
    path('debug/permissions/', views.DebugPermissionView.as_view(), name='debug-permissions'),
]