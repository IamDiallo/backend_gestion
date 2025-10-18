# Stock Availability Check Endpoint

## Summary

Added a new endpoint to check stock availability for a specific product in a specific zone.

---

## Endpoint Details

### **Check Stock Availability**

- **URL:** `/api/inventory/stock/check_availability/`
- **Method:** GET
- **Auth:** Required
- **Description:** Checks if sufficient stock is available for a product in a specific zone

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product` | integer | Yes | Product ID |
| `zone` | integer | Yes | Zone ID |
| `quantity` | float | Yes | Quantity to check |

### Response Format

#### Success Response (Stock Available)
```json
{
  "available": true,
  "current_stock": 150.0,
  "requested_quantity": 100.0,
  "shortfall": 0.0,
  "product_id": 1,
  "zone_id": 1,
  "product_name": "Laptop Dell XPS 15",
  "zone_name": "Magasin Principal"
}
```

#### Success Response (Insufficient Stock)
```json
{
  "available": false,
  "current_stock": 50.0,
  "requested_quantity": 100.0,
  "shortfall": 50.0,
  "product_id": 1,
  "zone_id": 1,
  "product_name": "Laptop Dell XPS 15",
  "zone_name": "Magasin Principal"
}
```

#### Success Response (No Stock Record)
```json
{
  "available": false,
  "current_stock": 0,
  "requested_quantity": 100.0,
  "shortfall": 100.0,
  "product_id": 1,
  "zone_id": 1,
  "error": "No stock record found for this product in this zone"
}
```

#### Error Response (Missing Parameters)
```json
{
  "error": "product parameter is required"
}
```
Status: `400 Bad Request`

#### Error Response (Invalid Quantity)
```json
{
  "error": "quantity must be a valid number"
}
```
Status: `400 Bad Request`

---

## Usage Examples

### cURL
```bash
# Check if 100 units of product 1 are available in zone 1
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventory/stock/check_availability/?product=1&zone=1&quantity=100"
```

### JavaScript/TypeScript
```typescript
// Frontend API call
const checkStockAvailability = async (
  productId: number,
  zoneId: number,
  quantity: number
): Promise<{
  available: boolean;
  current_stock: number;
  requested_quantity: number;
  shortfall: number;
}> => {
  const response = await api.get('/inventory/stock/check_availability/', {
    params: {
      product: productId,
      zone: zoneId,
      quantity: quantity
    }
  });
  return response.data;
};
```

### Python
```python
import requests

response = requests.get(
    'http://localhost:8000/api/inventory/stock/check_availability/',
    params={
        'product': 1,
        'zone': 1,
        'quantity': 100
    },
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

data = response.json()
if data['available']:
    print(f"Stock available: {data['current_stock']} units")
else:
    print(f"Insufficient stock. Short by {data['shortfall']} units")
```

---

## Implementation Details

### Location
- **File:** `backend/apps/inventory/views.py`
- **ViewSet:** `StockViewSet`
- **Action:** `check_availability`

### Code
```python
@action(detail=False, methods=['get'])
def check_availability(self, request):
    """
    Check stock availability for a product in a specific zone
    """
    product_id = request.query_params.get('product')
    zone_id = request.query_params.get('zone')
    quantity = request.query_params.get('quantity')
    
    # Validation and stock checking logic
    # Returns availability status and details
```

### Database Query
```python
stock = Stock.objects.get(product_id=product_id, zone_id=zone_id)
```

---

## Use Cases

### 1. **Sales Order Validation**
Before creating a sale, check if products are available in the selected zone:
```typescript
const canCreateSale = await checkStockAvailability(productId, zoneId, orderQuantity);
if (!canCreateSale.available) {
  alert(`Insufficient stock. Only ${canCreateSale.current_stock} units available.`);
}
```

### 2. **Stock Transfer Planning**
Check source zone has sufficient stock before initiating transfer:
```typescript
const sourceAvailability = await checkStockAvailability(
  productId, 
  sourceZoneId, 
  transferQuantity
);
```

### 3. **Real-time Stock Display**
Show availability status in product selection UI:
```typescript
const availability = await checkStockAvailability(selectedProduct, selectedZone, 1);
if (availability.current_stock === 0) {
  showOutOfStockMessage();
}
```

### 4. **Inventory Alerts**
Check multiple products for low stock across zones:
```typescript
for (const product of criticalProducts) {
  const check = await checkStockAvailability(product.id, mainZone, product.threshold);
  if (!check.available) {
    triggerLowStockAlert(product, check.current_stock);
  }
}
```

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `available` | boolean | True if current_stock >= requested_quantity |
| `current_stock` | float | Current stock quantity in the zone |
| `requested_quantity` | float | Quantity requested to check |
| `shortfall` | float | Amount short (0 if available, otherwise difference) |
| `product_id` | integer | ID of the product |
| `zone_id` | integer | ID of the zone |
| `product_name` | string | Name of the product (if found) |
| `zone_name` | string | Name of the zone (if found) |
| `error` | string | Error message (optional, only if stock record not found) |

---

## Validation Rules

1. **product** parameter must be provided
2. **zone** parameter must be provided
3. **quantity** parameter must be provided
4. **quantity** must be a valid number (float)
5. All numeric parameters must be positive

---

## Error Handling

The endpoint handles the following error cases:

1. **Missing Parameters:** Returns 400 with error message
2. **Invalid Quantity:** Returns 400 if quantity is not numeric
3. **Stock Not Found:** Returns 200 with `available: false` and error message
4. **Database Errors:** Returns 500 with error details

---

## Integration Notes

### Frontend Integration
Add to `frontend/src/services/api/inventory.api.ts`:

```typescript
export const checkStockAvailability = async (
  productId: number,
  zoneId: number,
  quantity: number
): Promise<{
  available: boolean;
  current_stock: number;
  requested_quantity: number;
  shortfall: number;
  product_id: number;
  zone_id: number;
  product_name?: string;
  zone_name?: string;
  error?: string;
}> => {
  const response = await api.get('/inventory/stock/check_availability/', {
    params: { product: productId, zone: zoneId, quantity }
  });
  return response.data;
};
```

### Usage in Components
```typescript
import { InventoryAPI } from '../services/api';

// In your component
const handleCheckStock = async () => {
  const result = await InventoryAPI.checkStockAvailability(
    selectedProduct,
    selectedZone,
    orderQuantity
  );
  
  if (result.available) {
    proceedWithOrder();
  } else {
    showError(`Insufficient stock: ${result.shortfall} units short`);
  }
};
```

---

## Testing

### Manual Test
```bash
# Test with sufficient stock
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventory/stock/check_availability/?product=1&zone=1&quantity=10"

# Test with insufficient stock
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventory/stock/check_availability/?product=1&zone=1&quantity=10000"

# Test with missing parameters
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventory/stock/check_availability/?product=1"

# Test with invalid quantity
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventory/stock/check_availability/?product=1&zone=1&quantity=abc"
```

---

## Status

✅ **Implemented** - Endpoint is fully functional and ready for use

- Added to `StockViewSet` in `apps/inventory/views.py`
- Automatically registered via DRF router
- Available at `/api/inventory/stock/check_availability/`
- Includes comprehensive validation and error handling
