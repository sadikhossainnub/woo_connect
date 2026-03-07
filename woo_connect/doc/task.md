# WooCommerce Connector for ERPNext

## Planning
- [x] Explore existing codebase
- [x] Research WooCommerce REST API and connector patterns
- [x] Write implementation plan
- [x] Get user approval on plan

## DocTypes
- [x] WooCommerce Server (Single Settings DocType)
- [x] WooCommerce Server child tables (tax, payment, warehouse, coupon mapping)
- [x] WC Sync Log (logging DocType)

## Core Infrastructure
- [x] WooCommerce API Client (Python wrapper using [woocommerce](file:///home/sayed/woo_connect/woo_connect/woocommerce_connect/sync/stock_sync.py#10-72) package)
- [x] Custom fields on Item, Customer, Address, Sales Order, Sales Invoice, Payment Entry

## Sync Services
- [x] Item sync (ERPNext ↔ WooCommerce)
- [x] Stock sync (ERPNext → WooCommerce)
- [x] Customer sync (WooCommerce → ERPNext)
- [x] Address sync (WooCommerce → ERPNext)
- [x] Sales Order sync (WooCommerce → ERPNext)
- [x] Sales Invoice sync (WooCommerce → ERPNext)
- [x] Payment Entry sync (WooCommerce → ERPNext)
- [x] Discount/Coupon sync (WooCommerce → ERPNext Pricing Rules & Coupon Codes)
- [x] Loyalty Points sync (WooCommerce → ERPNext Loyalty Program)

## Hooks & Integration
- [x] Scheduler events for periodic sync
- [x] Webhook endpoint for real-time sync
- [x] hooks.py updates (required_apps, fixtures, scheduler)
- [x] pyproject.toml (woocommerce dependency)

## Verification
- [/] File structure review
- [ ] Manual testing with user guidance
