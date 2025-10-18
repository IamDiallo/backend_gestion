# Dashboard App

## Overview

The **Dashboard App** is a dedicated Django app that provides aggregated, read-only views for dashboard display. It consolidates data from multiple domain apps (Inventory, Sales, Partners, Treasury, etc.) into optimized endpoints specifically designed for dashboard consumption.

---

## Architecture

```
Dashboard Layer (Aggregation & Presentation)
    ↓
apps/dashboard/
    ├── views.py           (Dashboard-specific views)
    ├── urls.py            (Dashboard endpoints)
    └── apps.py            (App configuration)
    
    ↓ Aggregates data from ↓

Domain Layer (Business Logic)
    ↓
apps/inventory/          (Products, Stock, Supplies)
apps/sales/              (Sales, Invoices, Quotes)
apps/partners/           (Clients, Suppliers, Employees)
apps/treasury/           (Accounts, Payments, Expenses)
apps/production/         (Productions, Materials)
```

---

## Endpoints

All dashboard endpoints are prefixed with `/api/dashboard/`

### Core Endpoints

#### 1. **Dashboard Stats**
- **URL:** `/api/dashboard/stats/`
- **Method:** GET
- **Auth:** Required
- **Description:** Overall dashboard statistics
- **Query Parameters:**
  - `period`: 'day', 'week', 'month', 'year', 'custom' (default: 'year')
  - `start_date`: Custom start date (YYYY-MM-DD) - required if period='custom'
  - `end_date`: Custom end date (YYYY-MM-DD) - required if period='custom'
- **Response:**
  ```json
  {
    "total_sales": 150000.00,
    "total_clients": 45,
    "total_products": 120,
    "total_suppliers": 25,
    "period": "month",
    "date_from": "2025-09-16",
    "date_to": "2025-10-16"
  }
  ```

#### 2. **Inventory Stats**
- **URL:** `/api/dashboard/inventory/`
- **Method:** GET
- **Auth:** Required
- **Description:** Inventory statistics and breakdowns
- **Query Parameters:**
  - `period`: 'day', 'week', 'month', 'year' (default: 'year')
- **Response:**
  ```json
  {
    "total_stock": 450,
    "low_stock_count": 12,
    "inventory_value": 850000.00,
    "total_value": 850000.00,
    "category_data": [
      {"category": "Électronique", "value": 350000.00},
      {"category": "Alimentaire", "value": 250000.00}
    ],
    "zone_data": [
      {"zone": "Magasin Principal", "value": 500000.00},
      {"zone": "Entrepôt", "value": 350000.00}
    ],
    "period": "year"
  }
  ```

#### 3. **Low Stock Products**
- **URL:** `/api/dashboard/low-stock/`
- **Method:** GET
- **Auth:** Required
- **Description:** Products with stock below minimum level
- **Response:**
  ```json
  [
    {
      "id": 15,
      "product_id": 8,
      "name": "Laptop Dell XPS 15",
      "category": "Électronique",
      "quantity": 2,
      "current_stock": 2,
      "threshold": 5,
      "min_stock_level": 5,
      "zone": "Magasin Principal",
      "unit": "pcs",
      "unit_symbol": "pcs"
    }
  ]
  ```

#### 4. **Recent Sales**
- **URL:** `/api/dashboard/recent-sales/`
- **Method:** GET
- **Auth:** Required
- **Description:** Most recent sales
- **Query Parameters:**
  - `limit`: Number of sales to return (default: 10)
- **Response:** Array of Sale objects (serialized)

### Additional Endpoints

#### 5. **Top Products**
- **URL:** `/api/dashboard/top-products/`
- **Method:** GET
- **Auth:** Required
- **Description:** Best-selling products
- **Query Parameters:**
  - `period`: 'day', 'week', 'month', 'year' (default: 'month')
  - `limit`: Number of products (default: 10)
- **Response:**
  ```json
  [
    {
      "id": 8,
      "name": "Laptop Dell XPS 15",
      "quantity": 45.0,
      "revenue": 675000.0
    }
  ]
  ```

#### 6. **Revenue Trend**
- **URL:** `/api/dashboard/revenue-trend/`
- **Method:** GET
- **Auth:** Required
- **Description:** Daily revenue trend over period
- **Query Parameters:**
  - `period`: 'week', 'month', 'year' (default: 'month')
- **Response:**
  ```json
  [
    {
      "date": "2025-09-16",
      "amount": 15000.0
    },
    {
      "date": "2025-09-17",
      "amount": 18500.0
    }
  ]
  ```

#### 7. **Client Activity**
- **URL:** `/api/dashboard/client-activity/`
- **Method:** GET
- **Auth:** Required
- **Description:** Recent client purchase activity
- **Query Parameters:**
  - `limit`: Number of clients (default: 10)
- **Response:**
  ```json
  [
    {
      "id": 12,
      "name": "Entreprise ABC",
      "last_sale_date": "2025-10-15",
      "total_amount": 125000.0,
      "sale_count": 8
    }
  ]
  ```

#### 8. **Pending Payments**
- **URL:** `/api/dashboard/pending-payments/`
- **Method:** GET
- **Auth:** Required
- **Description:** Summary of outstanding payments
- **Response:**
  ```json
  {
    "sales": {
      "count": 15,
      "total_amount": 250000.0,
      "paid_amount": 150000.0,
      "outstanding_amount": 100000.0
    },
    "supplies": {
      "count": 8,
      "total_amount": 120000.0,
      "paid_amount": 80000.0,
      "outstanding_amount": 40000.0
    },
    "total_outstanding": 140000.0
  }
  ```

---

## Design Principles

### 1. **Aggregation Layer**
- Dashboard app only aggregates data from domain apps
- No business logic or data manipulation
- Read-only operations

### 2. **Performance Optimization**
- Uses `select_related()` and `prefetch_related()` for efficient queries
- Optimized aggregations with Django ORM
- Limited result sets with sensible defaults

### 3. **Domain Separation**
- Domain apps maintain full CRUD operations
- Dashboard provides optimized read views
- Clear separation of concerns

### 4. **Flexibility**
- Parameterized endpoints (period, limit, etc.)
- Support for custom date ranges
- Extensible for future requirements

---

## Frontend Integration

The dashboard app endpoints are consumed by:
- `frontend/src/services/api/dashboard.api.ts`

Frontend functions map to backend endpoints:
- `fetchDashboardStats()` → `/api/dashboard/stats/`
- `fetchInventoryStats()` → `/api/dashboard/inventory/`
- `fetchLowStockProducts()` → `/api/dashboard/low-stock/`
- `fetchRecentSales()` → `/api/dashboard/recent-sales/`
- `fetchTopProducts()` → `/api/dashboard/top-products/`
- `fetchRevenueTrend()` → `/api/dashboard/revenue-trend/`

---

## Database Queries

Dashboard views use optimized queries:

```python
# Example: Low stock with minimal queries
Stock.objects.filter(
    quantity__lt=F('product__min_stock_level'),
    product__min_stock_level__gt=0
).select_related(
    'product', 
    'product__category', 
    'zone', 
    'product__unit'
).order_by('product__name')
```

---

## Migration from Legacy

### Before (Scattered):
- Dashboard logic in `gestion_api/views.py` (legacy)
- Inventory dashboard in `apps/inventory/dashboard_views.py`
- Sales dashboard in `apps/sales/dashboard_views.py`

### After (Consolidated):
- ✅ All dashboard logic in `apps/dashboard/views.py`
- ✅ Single unified URL structure `/api/dashboard/`
- ✅ Clean separation from domain apps
- ✅ Easier to maintain and extend

---

## Future Enhancements

Potential additions:
- `/api/dashboard/alerts/` - System alerts and notifications
- `/api/dashboard/performance/` - Business performance metrics
- `/api/dashboard/forecasting/` - Sales forecasting data
- `/api/dashboard/comparison/` - Period-over-period comparisons
- `/api/dashboard/export/` - Export dashboard data

---

## Testing

To test dashboard endpoints:

```bash
# Get dashboard stats
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/dashboard/stats/?period=month

# Get low stock products
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/dashboard/low-stock/

# Get top products for the week
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/dashboard/top-products/?period=week&limit=5
```

---

## Files

```
apps/dashboard/
├── __init__.py          # App initialization
├── apps.py              # App configuration
├── views.py             # Dashboard views (8 endpoints)
├── urls.py              # URL routing
├── admin.py             # Admin (not used)
├── models.py            # Models (not used - aggregation only)
└── tests.py             # Tests (to be implemented)
```

---

## Status

✅ **Complete** - Dashboard app fully implemented and integrated

- All 8 endpoints functional
- Registered in INSTALLED_APPS
- URL routing configured
- Ready for production use
