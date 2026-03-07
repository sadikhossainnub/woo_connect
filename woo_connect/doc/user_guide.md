# WooCommerce Connect — User Guide

A complete guide on how to install, configure, and use the ERPNext WooCommerce Connector.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Syncing Data](#4-syncing-data)
5. [Webhook Setup (Real-Time Sync)](#5-webhook-setup-real-time-sync)
6. [Coupons & Discounts](#6-coupons--discounts)
7. [Loyalty Points](#7-loyalty-points)
8. [Sync Logs](#8-sync-logs)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Before installing this connector, ensure you have:

- **ERPNext** installed and running on your Frappe bench
- **WooCommerce store** with REST API enabled
- **WooCommerce API keys** (Consumer Key & Consumer Secret)

### Generating WooCommerce API Keys

1. In your WordPress admin, go to **WooCommerce → Settings → Advanced → REST API**
2. Click **Add Key**
3. Set a description (e.g. "ERPNext Connector")
4. Select a user with admin privileges
5. Set permissions to **Read/Write**
6. Click **Generate API Key**
7. Copy the **Consumer Key** and **Consumer Secret** (you won't see the secret again!)

---

## 2. Installation

```bash
# Navigate to your bench directory
cd $BENCH_DIR

# Get the app
bench get-app /path/to/woo_connect

# Install on your site
bench install-app woo_connect

# Run migration to create DocTypes
bench migrate
```

---

## 3. Configuration

### Step 1: Open WooCommerce Server Settings

Navigate to the search bar in ERPNext and type **"WooCommerce Server"**, or go to:

```
Setup → WooCommerce Server
```

### Step 2: Connection Settings

| Field | Description | Example |
|---|---|---|
| **Enabled** | Master switch to enable/disable the connector | ✅ |
| **WooCommerce URL** | Your store URL (no trailing slash) | `https://mystore.com` |
| **API Key** | Consumer Key from WooCommerce | `ck_abc123...` |
| **API Secret** | Consumer Secret from WooCommerce | `cs_xyz789...` |
| **Verify SSL** | Keep enabled for production sites | ✅ |

> **Tip:** When you save the settings with "Enabled" checked, the connector automatically tests the connection and shows a success/failure message.

### Step 3: Default Values

These defaults are used when creating new records in ERPNext from WooCommerce data:

| Field | Description | Required |
|---|---|---|
| **Company** | Your ERPNext company | ✅ |
| **Default Warehouse** | Warehouse for WooCommerce operations (items, stock, orders) | ✅ |
| **Default Price List** | Price list for syncing item prices | Optional |
| **Default UOM** | Unit of measure for new items (default: Nos) | Optional |
| **Default Item Group** | Item group for new items | Optional |
| **Cost Center** | Cost center for transactions | Optional |

### Step 4: Accounts

| Field | Description |
|---|---|
| **Tax Account** | Fallback account for WooCommerce tax charges |
| **Freight / Shipping Account** | Account for shipping charges |

### Step 5: Sync Options

Toggle which data types to sync:

| Option | Description |
|---|---|
| **Sync Items** | Sync products between WooCommerce ↔ ERPNext |
| **Sync Customers** | Pull customers from WooCommerce → ERPNext |
| **Sync Orders** | Pull orders from WooCommerce → Sales Orders |
| **Sync Invoices** | Create Sales Invoices from completed orders |
| **Sync Payments** | Create Payment Entries from paid orders |
| **Sync Stock** | Push stock levels from ERPNext → WooCommerce |
| **Sync Coupons** | Pull coupons from WooCommerce → Pricing Rules |

### Step 6: Mapping Tables

#### Tax Mappings

Map WooCommerce tax classes to ERPNext Sales Tax Templates:

| WC Tax Class | Tax Template |
|---|---|
| `standard` | Standard Tax - MyCompany |
| `reduced-rate` | Reduced Tax - MyCompany |

#### Payment Method Mappings

Map WooCommerce payment gateways to ERPNext payment modes:

| WC Payment Method | Mode of Payment | Payment Account |
|---|---|---|
| `bacs` | Bank Transfer | Bank Account |
| `paypal` | PayPal | PayPal Account |
| `stripe` | Credit Card | Stripe Account |
| `cod` | Cash | Cash Account |

#### Warehouse Mappings

Map WooCommerce stock locations to ERPNext warehouses (if you have multiple locations):

| WC Location Name | Warehouse |
|---|---|
| `Main Store` | Stores - MC |
| `Warehouse B` | WH-B - MC |

---

## 4. Syncing Data

### Automatic Sync (Scheduled)

The connector automatically runs sync jobs on a schedule:

| Schedule | Sync Tasks |
|---|---|
| **Every hour** | Items, Customers, Orders, Invoices, Payments, Coupons, Loyalty Points |
| **Daily** | Stock levels (ERPNext → WooCommerce) |

No manual action required — just enable the sync options and the scheduler handles everything.

### Manual Sync (On-Demand)

On the **WooCommerce Server** form, click the **Sync** dropdown button to trigger any sync manually:

- **Sync Items** — Pull products from WooCommerce or push items to WooCommerce
- **Sync Customers** — Pull customers and their addresses
- **Sync Orders** — Pull new orders as Sales Orders
- **Sync Stock** — Push current stock levels to WooCommerce
- **Sync Invoices** — Create Sales Invoices for completed orders
- **Sync Payments** — Create Payment Entries for paid orders
- **Sync Coupons** — Pull coupon codes to ERPNext

Each sync runs as a **background job** so you can continue using ERPNext while it runs.

### Pushing Items to WooCommerce

To push an ERPNext Item to WooCommerce:

1. Open the **Item** form
2. Check the **"Sync to WooCommerce"** checkbox
3. Save
4. Click **Sync Items** on the WooCommerce Server form (or wait for the scheduler)

The item will be created/updated in WooCommerce and the **WooCommerce ID** field will be populated.

---

## 5. Webhook Setup (Real-Time Sync)

For instant sync when events happen in WooCommerce (instead of waiting for the hourly schedule):

### Step 1: Copy the Webhook Secret

On your WooCommerce Server form, find the auto-generated **Webhook Secret** field.

### Step 2: Add Webhooks in WooCommerce

1. Go to **WooCommerce → Settings → Advanced → Webhooks**
2. Click **Add Webhook** for each event you want:

| Name | Topic | Delivery URL |
|---|---|---|
| Order Created | Order created | `https://your-erpnext-site/api/method/woo_connect.woocommerce_connect.api.webhooks.handle_webhook` |
| Order Updated | Order updated | Same URL |
| Product Created | Product created | Same URL |
| Customer Created | Customer created | Same URL |
| Coupon Created | Coupon created | Same URL |

3. Set **Secret** to the webhook secret from ERPNext
4. Set **Status** to Active
5. Click **Save**

---

## 6. Coupons & Discounts

### Syncing Coupons

When **Sync Coupons** is enabled, the connector pulls all WooCommerce coupons and creates:

- **Pricing Rules** — with the correct discount type and amount
- **Coupon Codes** — linked to the Pricing Rule

WooCommerce coupon types are mapped as follows:

| WC Type | ERPNext Pricing Rule |
|---|---|
| `percent` | Discount Percentage |
| `fixed_cart` | Discount Amount (on transaction) |
| `fixed_product` | Discount Amount (on item) |

Coupon metadata is also synced: usage limits, expiry dates, and min/max amount restrictions.

### Order Discounts

When an order is synced, any applied coupon discounts are automatically set as **Additional Discount** on the Sales Order.

---

## 7. Loyalty Points

### Setup

1. Create a **Loyalty Program** in ERPNext (HR → Loyalty Program)
2. On the WooCommerce Server form, enable **"Enable Loyalty Points"**
3. Select the **Loyalty Program** you created

### How It Works

- The connector reads loyalty point balances from WooCommerce customer meta data
- It creates **Loyalty Point Entry** records in ERPNext to match the WC balance
- When orders are synced, loyalty point redemptions are applied to the Sales Order

> **Note:** This feature works with WooCommerce loyalty plugins that store point balances in customer meta data (e.g. WooCommerce Points and Rewards, YITH Points and Rewards).

---

## 8. Sync Logs

Every sync operation is logged in the **WC Sync Log** DocType. To view logs:

- Click **"View Sync Logs"** button on the WooCommerce Server form, or
- Navigate to **WC Sync Log** list from the search bar

Each log entry shows:

| Field | Description |
|---|---|
| **Sync Type** | Item, Customer, Order, Invoice, Payment, Stock, Coupon, or Loyalty |
| **Direction** | Push (ERPNext → WC) or Pull (WC → ERPNext) |
| **Status** | Success, Failed, or Skipped |
| **WooCommerce ID** | The WC resource ID |
| **ERPNext Document** | Link to the created/updated ERPNext document |
| **Message** | Details or error message |
| **Request/Response Data** | Full JSON payloads (collapsible) |

Use the **filters** to quickly find failed syncs and diagnose issues.

---

## 9. Troubleshooting

### Connection Failed

- Verify your **WooCommerce URL** is correct (no trailing slash, include `https://`)
- Check your **API Key** and **API Secret** are correct
- Ensure **Verify SSL** is unchecked if your store uses a self-signed certificate
- Make sure WooCommerce REST API is enabled and permalinks are set to something other than "Plain"

### Items Not Syncing

- Ensure **Sync Items** is enabled
- For pushing items, check the **"Sync to WooCommerce"** checkbox on the Item form
- Check WC Sync Logs for error details

### Orders Not Appearing

- Ensure **Sync Orders** is enabled
- Only orders with status `processing`, `completed`, or `on-hold` are synced
- Orders already synced (with matching `woocommerce_id`) are skipped

### Invoices/Payments Not Created

- **Invoices** are only created for orders with WooCommerce status `completed`
- **Payment Entries** require a submitted Sales Invoice with outstanding amount
- Ensure you have set up **Payment Method Mappings** for your WC payment gateways

### Stock Quantities Wrong

- Stock sync pushes the **actual quantity** from the **default warehouse**
- If using multiple warehouses, set up **Warehouse Mappings**
- Stock sync runs daily by default; use manual sync for immediate updates

### Webhook Not Working

- Verify the webhook URL is publicly accessible (not behind a firewall)
- Check the webhook secret matches in both WooCommerce and ERPNext
- Look at WooCommerce webhook delivery logs for error responses

### General Tips

- Always check **WC Sync Log** for detailed error messages
- Check **Error Log** in ERPNext for Python tracebacks
- Use **manual sync buttons** to test individual sync types
- Start with a small dataset to verify mappings before enabling scheduled sync
