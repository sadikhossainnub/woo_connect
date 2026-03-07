# ERPNext WooCommerce Connector — Implementation Plan

Build a Frappe app (`woo_connect`) that synchronises Items, Stock, Customers, Addresses, Sales Orders, Sales Invoices, Payment Entries, **Discounts/Coupons**, and **Loyalty Points** between ERPNext and a WooCommerce store via the WooCommerce REST API v3.

## User Review Required

> [!IMPORTANT]
> **WooCommerce API library**: The plan uses the official `woocommerce` Python package (a thin REST wrapper). This will be added as a pip dependency in [pyproject.toml](file:///home/sayed/woo_connect/pyproject.toml).

> [!IMPORTANT]
> **Sync direction defaults**: Items sync bidirectionally; Stock pushes from ERPNext → WooCommerce; Orders, Customers, Addresses, Invoices, and Payments pull from WooCommerce → ERPNext. Please confirm if any direction should differ.

> [!WARNING]
> **Custom fields on core DocTypes**: The connector adds custom fields (e.g. `woocommerce_id`) to Item, Customer, Address, Sales Order, Sales Invoice, and Payment Entry. These fields are created via `fixtures` in [hooks.py](file:///home/sayed/woo_connect/woo_connect/hooks.py) so they install/uninstall cleanly.

---

## Proposed Changes

### 1 · WooCommerce Server (Settings DocType)

A **Single** DocType to store connection credentials and default mappings.

#### [NEW] [woocommerce_server.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/woocommerce_server/woocommerce_server.json)

| Field | Type | Notes |
|---|---|---|
| `enabled` | Check | Master enable/disable |
| `woocommerce_url` | Data (URL) | Store URL |
| `api_key` | Data | Consumer Key |
| `api_secret` | Password | Consumer Secret |
| `verify_ssl` | Check | Default ON |
| **Defaults section** | | |
| `company` | Link → Company | |
| `default_warehouse` | Link → Warehouse | |
| `default_price_list` | Link → Price List | |
| `default_uom` | Link → UOM | |
| `default_item_group` | Link → Item Group | |
| `cost_center` | Link → Cost Center | |
| `tax_account` | Link → Account | |
| `freight_account` | Link → Account | |
| **Sync Options** | | |
| `sync_items` | Check | |
| `sync_customers` | Check | |
| `sync_orders` | Check | |
| `sync_invoices` | Check | |
| `sync_payments` | Check | |
| `sync_stock` | Check | |
| `sync_coupons` | Check | Sync WC coupons → ERPNext Coupon Codes |
| **Loyalty & Discounts** | | |
| `enable_loyalty_points` | Check | Map WC loyalty points to ERPNext Loyalty Program |
| `loyalty_program` | Link → Loyalty Program | ERPNext Loyalty Program to use |
| `default_discount_account` | Link → Account | Account for coupon/discount postings |
| **Webhook** | | |
| `webhook_secret` | Data (read-only) | Auto-generated |
| **Child Tables** | | |
| `tax_mappings` | Table → WC Tax Mapping | WC tax class → ERPNext tax template |
| `payment_method_mappings` | Table → WC Payment Method Mapping | WC gateway → ERPNext MoP / Account |
| `warehouse_mappings` | Table → WC Warehouse Mapping | WC location → ERPNext warehouse |
| `coupon_mappings` | Table → WC Coupon Mapping | WC coupon code → ERPNext Pricing Rule / Coupon Code |

#### [NEW] [woocommerce_server.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/woocommerce_server/woocommerce_server.py)

Controller with:
- `validate()` — test API connection on save
- `generate_webhook_secret()` — auto-populate if empty
- Whitelisted button methods: `sync_items`, `sync_customers`, `sync_orders`, `sync_stock`, `sync_invoices`, `sync_payments`, `sync_coupons`

#### [NEW] [woocommerce_server.js](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/woocommerce_server/woocommerce_server.js)

Client script with manual sync buttons triggered from the Single form.

---

### 2 · Child Table DocTypes

#### [NEW] [wc_tax_mapping.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_tax_mapping/wc_tax_mapping.json)

Fields: `wc_tax_class` (Data), `tax_template` (Link → Sales Taxes and Charges Template)

#### [NEW] [wc_payment_method_mapping.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_payment_method_mapping/wc_payment_method_mapping.json)

Fields: `wc_payment_method` (Data), `mode_of_payment` (Link → Mode of Payment), `payment_account` (Link → Account)

#### [NEW] [wc_warehouse_mapping.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_warehouse_mapping/wc_warehouse_mapping.json)

Fields: `wc_location_name` (Data), `warehouse` (Link → Warehouse)

#### [NEW] [wc_coupon_mapping.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_coupon_mapping/wc_coupon_mapping.json)

Fields: `wc_coupon_code` (Data), `discount_type` (Select: Percentage / Fixed Cart / Fixed Product), `pricing_rule` (Link → Pricing Rule), `coupon_code` (Link → Coupon Code)

---

### 3 · WC Sync Log DocType

#### [NEW] [wc_sync_log.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_sync_log/wc_sync_log.json)

Logs every sync event.

| Field | Type |
|---|---|
| `sync_type` | Select (Item / Customer / Order / Invoice / Payment / Stock / Coupon / Loyalty) |
| `direction` | Select (Push / Pull) |
| `wc_id` | Data |
| `erpnext_doctype` | Data |
| `erpnext_docname` | Dynamic Link |
| `status` | Select (Success / Failed / Skipped) |
| `message` | Small Text |
| `request_data` | Code (JSON) |
| `response_data` | Code (JSON) |

#### [NEW] [wc_sync_log.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/doctype/wc_sync_log/wc_sync_log.py)

Minimal controller.

---

### 4 · Custom Fields (fixtures)

#### [NEW] [custom_field.json](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/fixtures/custom_field.json)

Adds to **Item**: `woocommerce_id`, `woocommerce_sync`  
Adds to **Customer**: `woocommerce_id`  
Adds to **Address**: `woocommerce_id`  
Adds to **Sales Order**: `woocommerce_id`, `woocommerce_status`  
Adds to **Sales Invoice**: `woocommerce_id`  
Adds to **Payment Entry**: `woocommerce_id`  

These will be exported as fixture JSON and referenced in [hooks.py](file:///home/sayed/woo_connect/woo_connect/hooks.py) via `fixtures`.

---

### 5 · WooCommerce API Client

#### [NEW] [api_client.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/utils/api_client.py)

Wrapper around the `woocommerce` Python package (`WooCommerce` class from `woocommerce.api`).

Key methods: `get()`, `post()`, `put()`, `delete()`, auto-paging `get_all()`.

---

### 6 · Sync Service Modules

Each module lives under `woo_connect/woo_connect/woocommerce_connect/sync/`.

#### [NEW] [item_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/item_sync.py)
- `sync_items_from_woocommerce()` — pull products → create/update Items
- `sync_items_to_woocommerce()` — push Items → create/update WC products
- Maps: name, SKU, price, description, weight, stock status, images, categories

#### [NEW] [stock_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/stock_sync.py)
- `sync_stock_to_woocommerce()` — read Bin qty → update WC `stock_quantity`

#### [NEW] [customer_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/customer_sync.py)
- `sync_customers_from_woocommerce()` — pull WC customers → create/update ERPNext Customer + Contact

#### [NEW] [address_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/address_sync.py)
- `sync_addresses_from_woocommerce()` — pull billing/shipping from WC orders → create/update ERPNext Address

#### [NEW] [order_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/order_sync.py)
- `sync_orders_from_woocommerce()` — pull WC orders → create Sales Orders with items, taxes, shipping
- Applies WC coupon lines as Additional Discount or item-level discounts
- Redeems loyalty points if WC order contains loyalty point redemption metadata

#### [NEW] [invoice_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/invoice_sync.py)
- `sync_invoices_from_woocommerce()` — create Sales Invoice from completed WC orders

#### [NEW] [payment_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/payment_sync.py)
- `sync_payments_from_woocommerce()` — create Payment Entry for paid WC orders

#### [NEW] [discount_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/discount_sync.py)
- `sync_coupons_from_woocommerce()` — pull WC coupons → create/update ERPNext Pricing Rules + Coupon Codes
- Maps WC coupon types: `percent`, `fixed_cart`, `fixed_product` → ERPNext Pricing Rule discount types
- Syncs coupon metadata: usage limits, expiry dates, min/max amounts, product/category restrictions

#### [NEW] [loyalty_sync.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/loyalty_sync.py)
- `sync_loyalty_points_from_woocommerce()` — pull WC loyalty points balances → update ERPNext Loyalty Point Entry
- Creates Loyalty Point entries for customers with WC loyalty point earn/redeem transactions
- Maps WC loyalty plugin points to the configured ERPNext Loyalty Program

---

### 7 · Webhook Endpoint

#### [NEW] [webhooks.py](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/api/webhooks.py)

Frappe whitelisted API (`@frappe.whitelist(allow_guest=True)`) to receive WooCommerce webhook payloads for order creation/update events. Verifies HMAC signature using the webhook secret.

---

### 8 · Hooks & Configuration

#### [MODIFY] [hooks.py](file:///home/sayed/woo_connect/woo_connect/hooks.py)

```diff
+required_apps = ["frappe", "erpnext"]
+
+fixtures = [
+    {"dt": "Custom Field", "filters": [["module", "=", "Woocommerce Connect"]]}
+]
+
+scheduler_events = {
+    "hourly_long": [
+        "woo_connect.woocommerce_connect.sync.item_sync.sync_items_from_woocommerce",
+        "woo_connect.woocommerce_connect.sync.customer_sync.sync_customers_from_woocommerce",
+        "woo_connect.woocommerce_connect.sync.order_sync.sync_orders_from_woocommerce",
+        "woo_connect.woocommerce_connect.sync.discount_sync.sync_coupons_from_woocommerce",
+        "woo_connect.woocommerce_connect.sync.loyalty_sync.sync_loyalty_points_from_woocommerce",
+    ],
+    "daily": [
+        "woo_connect.woocommerce_connect.sync.stock_sync.sync_stock_to_woocommerce",
+    ],
+}
```

#### [MODIFY] [pyproject.toml](file:///home/sayed/woo_connect/pyproject.toml)

Add `woocommerce` to `dependencies`.

---

## Verification Plan

### Manual Verification

Since this connector requires a live WooCommerce instance and an ERPNext site, automated unit tests without mocking the external API aren't practical for an initial build. Here is the recommended manual testing approach:

1. **Install the app** on your bench:
   ```bash
   cd $BENCH_DIR
   bench get-app /home/sayed/woo_connect
   bench install-app woo_connect
   bench migrate
   ```
2. **Configure WooCommerce Server**: Navigate to *WooCommerce Server* in ERPNext, enter your WC store URL, API key, and API secret. Set default Company, Warehouse, UOM, Item Group, Price List.
3. **Test connection**: Save the settings — the `validate()` method will verify the API connection.
4. **Test Item sync**: Click "Sync Items" button and verify Items are created in ERPNext with `woocommerce_id` populated.
5. **Test Customer sync**: Click "Sync Customers" and verify Customers/Contacts are created.
6. **Test Order sync**: Click "Sync Orders" and verify Sales Orders are created with correct items and totals.
7. **Test Stock sync**: Click "Sync Stock" and check WooCommerce product stock quantities match ERPNext Bin quantities.
8. **Test Invoice sync**: Click "Sync Invoices" for completed orders.
9. **Test Payment sync**: Click "Sync Payments" for paid orders.
10. **Check WC Sync Log**: Verify log entries are created for each sync operation.
11. **Test Webhook**: Configure a webhook in WooCommerce (Settings → Advanced → Webhooks) pointing to `https://your-site/api/method/woo_connect.woocommerce_connect.api.webhooks.handle_webhook` with the secret from settings.

> [!TIP]
> If you don't have a live WooCommerce store, you can use a local WordPress + WooCommerce Docker setup or a staging site to test.
