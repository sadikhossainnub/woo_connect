# WooCommerce Connect — API Documentation

Complete reference for all APIs, whitelisted methods, webhook endpoints, sync functions, and utility modules.

---

## Table of Contents

1. [Webhook API](#1-webhook-api)
2. [Whitelisted Methods (WooCommerce Server)](#2-whitelisted-methods-woocommerce-server)
3. [Sync Functions](#3-sync-functions)
4. [API Client Utilities](#4-api-client-utilities)
5. [Data Models (DocTypes)](#5-data-models-doctypes)
6. [Custom Fields](#6-custom-fields)
7. [Scheduler Events](#7-scheduler-events)

---

## 1. Webhook API

### `POST` /api/method/woo_connect.woocommerce_connect.api.webhooks.handle_webhook

Receives webhook payloads from WooCommerce for real-time synchronisation.

**Authentication:** Guest-accessible (no Frappe session required). Uses HMAC-SHA256 signature verification.

**Headers:**

| Header | Required | Description |
|---|---|---|
| `X-WC-Webhook-Signature` | ✅ | Base64-encoded HMAC-SHA256 of the payload using the webhook secret |
| `X-WC-Webhook-Topic` | ✅ | Event topic (e.g. `order.created`, `product.updated`) |
| `Content-Type` | ✅ | `application/json` |

**Supported Topics:**

| Topic Prefix | Handler | Triggers |
|---|---|---|
| `order.*` | Order sync | `order.created`, `order.updated`, `order.deleted` |
| `product.*` | Item sync | `product.created`, `product.updated`, `product.deleted` |
| `customer.*` | Customer sync | `customer.created`, `customer.updated` |
| `coupon.*` | Coupon sync | `coupon.created`, `coupon.updated` |

**Request Body:** Raw WooCommerce webhook JSON payload.

**Response:**

```json
{
  "status": "ok"
}
```

**Error Responses:**

| Status | Reason |
|---|---|
| `403` | Integration disabled or invalid signature |
| `500` | Internal processing error (check Error Log) |

**Signature Verification:**

The webhook secret is auto-generated and stored in `WooCommerce Server → Webhook Secret`. The signature is verified using:

```
HMAC-SHA256(webhook_secret, raw_request_body) → Base64 encoded → compared with X-WC-Webhook-Signature
```

---

## 2. Whitelisted Methods (WooCommerce Server)

All methods are called on the `WooCommerce Server` Single DocType instance. They require `System Manager` role.

### `run_sync_items`

Enqueues a background job to sync items between WooCommerce and ERPNext.

```python
# Frappe client call
frappe.call({
    method: "run_sync_items",
    doc: frm.doc,
})
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_customers`

Enqueues customer sync (WooCommerce → ERPNext).

```python
frappe.call({ method: "run_sync_customers", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_orders`

Enqueues order sync (WooCommerce → Sales Orders).

```python
frappe.call({ method: "run_sync_orders", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_stock`

Enqueues stock push (ERPNext Bin quantities → WooCommerce `stock_quantity`).

```python
frappe.call({ method: "run_sync_stock", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_invoices`

Enqueues invoice creation for completed WooCommerce orders.

```python
frappe.call({ method: "run_sync_invoices", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_payments`

Enqueues payment entry creation for paid WooCommerce orders.

```python
frappe.call({ method: "run_sync_payments", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_coupons`

Enqueues coupon sync (WooCommerce → Pricing Rules + Coupon Codes).

```python
frappe.call({ method: "run_sync_coupons", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

### `run_sync_categories`

Enqueues category sync (WooCommerce categories → ERPNext Item Groups).

```python
frappe.call({ method: "run_sync_categories", doc: frm.doc })
```

**Queue:** `long` | **Timeout:** 1500s

---

## 3. Sync Functions

Standalone Python functions that can be called directly or via the scheduler.

### Item Sync — `woo_connect.woocommerce_connect.sync.item_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_items_from_woocommerce()` | Pull | Fetches all published WC products → creates/updates ERPNext Items |
| `sync_items_to_woocommerce()` | Push | Pushes Items with `custom_woocommerce_sync=1` → creates/updates WC products |
| `sync_categories_from_woocommerce()` | Pull | Fetches WC product categories → creates Item Groups + populates mappings |

**WC API Endpoint:** `GET /wp-json/wc/v3/products`, `GET /wp-json/wc/v3/products/categories`

**Field Mapping (Pull — WC → ERPNext):**

| WooCommerce Field | ERPNext Field |
|---|---|
| `id` | `custom_woocommerce_id` |
| `name` | `item_name` |
| `sku` | `item_code` (fallback: `WC-{id}`) |
| `description` | `description` |
| `regular_price` / `price` | Item Price (via price list) |
| `weight` | `weight_per_unit` |
| `manage_stock` | `is_stock_item` |
| `categories[0]` | `item_group` (via category mapping) |

**Field Mapping (Push — ERPNext → WC):**

| ERPNext Field | WooCommerce Field |
|---|---|
| `item_name` | `name` |
| `item_code` | `sku` |
| `description` | `description`, `short_description` |
| `weight_per_unit` | `weight` |
| `is_stock_item` | `manage_stock` |
| Item Price rate | `regular_price` |

---

### Stock Sync — `woo_connect.woocommerce_connect.sync.stock_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_stock_to_woocommerce()` | Push | Reads Bin actual_qty → updates WC `stock_quantity` |

**WC API Endpoint:** `PUT /wp-json/wc/v3/products/{id}`

**Data Sent:**
```json
{
  "stock_quantity": 150,
  "manage_stock": true
}
```

---

### Customer Sync — `woo_connect.woocommerce_connect.sync.customer_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_customers_from_woocommerce()` | Pull | Fetches WC customers → creates Customer + Contact + Address |

**WC API Endpoint:** `GET /wp-json/wc/v3/customers`

**What Gets Created:**

| WC Data | ERPNext DocType | Notes |
|---|---|---|
| Customer profile | Customer | `customer_type=Individual` |
| Email + phone | Contact | Linked to Customer |
| `billing` address | Address (Billing) | Linked to Customer |
| `shipping` address | Address (Shipping) | Linked to Customer |

**Field Mapping:**

| WooCommerce | ERPNext Customer |
|---|---|
| `id` | `custom_woocommerce_id` |
| `first_name` + `last_name` | `customer_name` |
| `email` | Contact `email_id` |
| `billing.phone` | Contact `phone` |
| `billing.address_1` | Address `address_line1` |
| `billing.city` | Address `city` |
| `billing.country` (ISO code) | Address `country` (resolved to name) |

---

### Address Sync — `woo_connect.woocommerce_connect.sync.address_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_addresses_from_woocommerce()` | Pull | Fetches addresses from WC orders → creates/updates ERPNext Address |

**WC API Endpoint:** `GET /wp-json/wc/v3/orders`

---

### Order Sync — `woo_connect.woocommerce_connect.sync.order_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_orders_from_woocommerce()` | Pull | Fetches WC orders → creates submitted Sales Orders |

**WC API Endpoint:** `GET /wp-json/wc/v3/orders?status=processing,completed,on-hold`

**What Gets Created:**

| Component | Handling |
|---|---|
| Line items | Sales Order Items (matched by `woocommerce_id` or SKU) |
| Shipping total | Added as `WC-Shipping` service item |
| Tax | Applied via tax mapping table or fallback to `tax_account` |
| Coupons | Applied as `discount_amount` (Additional Discount) |
| Loyalty points | Applied via `loyalty_program` + `loyalty_points` fields |

**Field Mapping:**

| WooCommerce | ERPNext Sales Order |
|---|---|
| `id` | `custom_woocommerce_id` |
| `status` | `custom_woocommerce_status` |
| `number` | `po_no` (prefixed `WC-`) |
| `date_created` | `transaction_date`, `delivery_date` |
| `line_items[].product_id` | Item lookup by `custom_woocommerce_id` |
| `line_items[].quantity` | `qty` |
| `line_items[].price` | `rate` |
| `coupon_lines[].discount` | `discount_amount` (summed) |

---

### Invoice Sync — `woo_connect.woocommerce_connect.sync.invoice_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_invoices_from_woocommerce()` | Pull | Creates Sales Invoice from existing Sales Order for completed orders |

**Prerequisites:** Sales Order must exist and be submitted. Uses ERPNext's `make_sales_invoice()` helper.

---

### Payment Sync — `woo_connect.woocommerce_connect.sync.payment_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_payments_from_woocommerce()` | Pull | Creates Payment Entry from existing Sales Invoice for paid orders |

**Prerequisites:** Sales Invoice must exist, be submitted, and have `outstanding_amount > 0`. Uses ERPNext's `get_payment_entry()` helper.

**Payment Method Resolution:**
```
WC payment_method → Payment Method Mappings table → Mode of Payment + Account
```

---

### Discount Sync — `woo_connect.woocommerce_connect.sync.discount_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_coupons_from_woocommerce()` | Pull | Fetches WC coupons → creates Pricing Rules + Coupon Codes |

**WC API Endpoint:** `GET /wp-json/wc/v3/coupons`

**Coupon Type Mapping:**

| WC `discount_type` | ERPNext `rate_or_discount` |
|---|---|
| `percent` | Discount Percentage |
| `fixed_cart` | Discount Amount |
| `fixed_product` | Discount Amount |

**Synced Metadata:** `amount`, `date_expires`, `minimum_amount`, `maximum_amount`, `usage_limit`, `usage_limit_per_user`

---

### Loyalty Sync — `woo_connect.woocommerce_connect.sync.loyalty_sync`

| Function | Direction | Description |
|---|---|---|
| `sync_loyalty_points_from_woocommerce()` | Pull | Reads WC customer meta → adjusts ERPNext Loyalty Point Entries |

**Supported WC meta keys:** `wc_points_balance`, `_wc_points_balance`, `loyalty_points_balance`, `_loyalty_points`, `points_balance`

**Logic:** Compares WC balance vs. ERPNext balance → creates adjustment Loyalty Point Entry.

---

## 4. API Client Utilities

Module: `woo_connect.woocommerce_connect.utils.api_client`

### `get_wc_api(settings=None)`

Returns a configured `WooCommerceAPI` instance (from the `woocommerce` pip package).

```python
from woo_connect.woocommerce_connect.utils.api_client import get_wc_api

api = get_wc_api()
response = api.get("products", params={"per_page": 10})
products = response.json()
```

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `settings` | Document \| None | `None` | WooCommerce Server doc. Auto-fetched if `None`. |

**Returns:** `WooCommerceAPI` instance configured with `wc/v3`, 40s timeout.

---

### `get_all_wc_resources(endpoint, params=None)`

Fetches **all pages** of a WC resource automatically.

```python
from woo_connect.woocommerce_connect.utils.api_client import get_all_wc_resources

all_products = get_all_wc_resources("products", params={"status": "publish"})
all_orders = get_all_wc_resources("orders", params={"status": "completed"})
```

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `endpoint` | str | — | WC API endpoint (e.g. `products`, `orders`, `customers`) |
| `params` | dict \| None | `None` | Query parameters. `per_page` defaults to 100. |

**Returns:** `list[dict]` — all resources across all pages.

**Pagination:** Uses `X-WP-TotalPages` header to detect last page.

---

### `create_sync_log(...)`

Creates a `WC Sync Log` entry for tracking sync operations.

```python
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log

create_sync_log(
    sync_type="Item",
    direction="Pull",
    status="Success",
    wc_id="123",
    erpnext_doctype="Item",
    erpnext_docname="ITEM-001",
    message="Synced product: Blue T-Shirt",
    request_data={"id": 123, "name": "Blue T-Shirt"},
    response_data=None,
)
```

**Parameters:**

| Param | Type | Required | Options |
|---|---|---|---|
| `sync_type` | str | ✅ | `Item`, `Customer`, `Order`, `Invoice`, `Payment`, `Stock`, `Coupon`, `Loyalty` |
| `direction` | str | ✅ | `Push`, `Pull` |
| `status` | str | ✅ | `Success`, `Failed`, `Skipped` |
| `wc_id` | str \| None | — | WooCommerce resource ID |
| `erpnext_doctype` | str \| None | — | ERPNext DocType name |
| `erpnext_docname` | str \| None | — | ERPNext document name |
| `message` | str \| None | — | Description or error message |
| `request_data` | dict \| str \| None | — | Request payload (auto JSON-serialised) |
| `response_data` | dict \| str \| None | — | Response payload (auto JSON-serialised) |

---

## 5. Data Models (DocTypes)

### WooCommerce Server (Single)

Settings and configuration. One instance per site.

| Field | Type | Description |
|---|---|---|
| `enabled` | Check | Master on/off switch |
| `woocommerce_url` | Data (URL) | Store URL |
| `api_key` | Data | Consumer Key |
| `api_secret` | Password | Consumer Secret |
| `verify_ssl` | Check | SSL verification |
| `company` | Link → Company | Default company |
| `default_warehouse` | Link → Warehouse | WooCommerce warehouse |
| `default_price_list` | Link → Price List | For item prices |
| `default_uom` | Link → UOM | Default: Nos |
| `default_item_group` | Link → Item Group | Fallback item group |
| `cost_center` | Link → Cost Center | For transactions |
| `tax_account` | Link → Account | Fallback tax account |
| `freight_account` | Link → Account | Shipping charges account |
| `sync_items` | Check | Enable item sync |
| `sync_customers` | Check | Enable customer sync |
| `sync_orders` | Check | Enable order sync |
| `sync_invoices` | Check | Enable invoice creation |
| `sync_payments` | Check | Enable payment creation |
| `sync_stock` | Check | Enable stock push |
| `sync_coupons` | Check | Enable coupon sync |
| `sync_categories` | Check | Enable category → Item Group sync |
| `enable_loyalty_points` | Check | Enable loyalty point sync |
| `loyalty_program` | Link → Loyalty Program | ERPNext loyalty program |
| `default_discount_account` | Link → Account | For coupon postings |
| `webhook_secret` | Data (read-only) | Auto-generated HMAC secret |
| `tax_mappings` | Table → WC Tax Mapping | |
| `payment_method_mappings` | Table → WC Payment Method Mapping | |
| `warehouse_mappings` | Table → WC Warehouse Mapping | |
| `coupon_mappings` | Table → WC Coupon Mapping | |
| `category_mappings` | Table → WC Category Mapping | |

### WC Sync Log

| Field | Type |
|---|---|
| `sync_type` | Select |
| `direction` | Select |
| `status` | Select |
| `wc_id` | Data |
| `erpnext_doctype` | Link → DocType |
| `erpnext_docname` | Dynamic Link |
| `message` | Small Text |
| `request_data` | Code (JSON) |
| `response_data` | Code (JSON) |

### Child Tables

| DocType | Fields |
|---|---|
| **WC Tax Mapping** | `wc_tax_class`, `tax_template` (Link → Sales Taxes and Charges Template) |
| **WC Payment Method Mapping** | `wc_payment_method`, `mode_of_payment` (Link → Mode of Payment), `payment_account` (Link → Account) |
| **WC Warehouse Mapping** | `wc_location_name`, `warehouse` (Link → Warehouse) |
| **WC Coupon Mapping** | `wc_coupon_code`, `discount_type` (Select), `pricing_rule` (Link), `coupon_code` (Link) |
| **WC Category Mapping** | `wc_category_id`, `wc_category_name` (read-only), `item_group` (Link → Item Group) |

---

## 6. Custom Fields

Added to core ERPNext DocTypes via fixtures:

| DocType | Field | Type | Description |
|---|---|---|---|
| **Item** | `custom_woocommerce_id` | Data (read-only) | WC product ID |
| **Item** | `custom_woocommerce_sync` | Check | Flag to push item to WC |
| **Customer** | `custom_woocommerce_id` | Data (read-only) | WC customer ID |
| **Address** | `custom_woocommerce_id` | Data (read-only) | WC address reference |
| **Sales Order** | `custom_woocommerce_id` | Data (read-only) | WC order ID |
| **Sales Order** | `custom_woocommerce_status` | Data (read-only) | WC order status |
| **Sales Invoice** | `custom_woocommerce_id` | Data (read-only) | WC order ID |
| **Payment Entry** | `custom_woocommerce_id` | Data (read-only) | WC order ID |

---

## 7. Scheduler Events

Configured in `hooks.py`:

| Schedule | Function | Description |
|---|---|---|
| `hourly_long` | `item_sync.sync_items_from_woocommerce` | Pull WC products |
| `hourly_long` | `customer_sync.sync_customers_from_woocommerce` | Pull WC customers |
| `hourly_long` | `order_sync.sync_orders_from_woocommerce` | Pull WC orders |
| `hourly_long` | `invoice_sync.sync_invoices_from_woocommerce` | Create invoices |
| `hourly_long` | `payment_sync.sync_payments_from_woocommerce` | Create payments |
| `hourly_long` | `discount_sync.sync_coupons_from_woocommerce` | Pull WC coupons |
| `hourly_long` | `loyalty_sync.sync_loyalty_points_from_woocommerce` | Sync loyalty points |
| `hourly_long` | `item_sync.sync_categories_from_woocommerce` | Sync WC categories |
| `daily` | `stock_sync.sync_stock_to_woocommerce` | Push stock levels |

All scheduler functions check `settings.enabled` and the corresponding `sync_*` flag before executing. If disabled, they return immediately.
