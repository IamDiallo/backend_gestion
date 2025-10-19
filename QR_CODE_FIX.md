# QR Code Fix - Product Reference Issue

## Problem
The QR code generation for products was failing with the error:
```
AttributeError: 'Product' object has no attribute 'code'
```

## Root Cause
The `ProductViewSet.qr_code()` method in `backend/apps/inventory/views.py` was trying to access `product.code`, but the Product model uses `product.reference` as the field name.

## Solution Applied

### Backend Changes (`apps/inventory/views.py`)

**Before:**
```python
qr.add_data(f"Product: {product.name} - Code: {product.code}")
```

**After:**
```python
qr.add_data(f"Product: {product.name} - Reference: {product.reference}")
```

### Additional Improvements

1. **Changed response format** from JSON with base64 to direct image response:
   - Before: Returned `{'qr_code': 'data:image/png;base64,...', 'product': {...}}`
   - After: Returns PNG image directly with `content_type='image/png'`

2. **Benefits:**
   - Simpler frontend handling (already implemented in `ProductQRCode.tsx`)
   - Smaller response size (no base64 encoding overhead)
   - Better browser compatibility
   - Can be used directly in `<img>` tags or downloaded

## Frontend (No Changes Needed)

The frontend components were already properly configured:

1. **`ProductQRCode.tsx`** - Expects blob response ✓
2. **`Products.tsx`** - Download QR code functionality working ✓
3. **`InventoryAPI.fetchProductQRCode()`** - Returns blob ✓

## Testing

Test the following scenarios:

1. **In Product Edit Dialog:**
   - Open any product for editing
   - QR code should display immediately
   - "Télécharger" button should work

2. **In Products Grid:**
   - Click QR icon on any product row
   - Should download QR code as PNG file

3. **QR Code Content:**
   - Scan the QR code
   - Should show: `Product: [Product Name] - Reference: [Reference]`

## API Endpoint

```
GET /api/inventory/products/{id}/qr_code/
```

**Response:**
- Content-Type: `image/png`
- Body: PNG image binary data

## Files Modified

1. `backend/apps/inventory/views.py` - Fixed attribute name and response format

---
**Date:** October 19, 2025
**Status:** ✅ Fixed
