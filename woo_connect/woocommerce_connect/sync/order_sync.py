# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Orders from WooCommerce to ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_orders_from_woocommerce():
	"""Pull orders from WooCommerce and create Sales Orders in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_orders:
		return

	orders = get_all_wc_resources(
		"orders",
		params={"status": "processing,completed,on-hold", "per_page": 50},
	)

	for wc_order in orders:
		try:
			wc_order_id = str(wc_order.get("id"))
			wc_order_no = f"WC-{wc_order.get('number', wc_order_id)}"

			# Skip if already synced (using PO No as identifier)
			if frappe.db.exists("Sales Order", {"po_no": wc_order_no}):
				continue

			so_name = _create_sales_order(wc_order, settings)
			create_sync_log(
				sync_type="Order",
				direction="Pull",
				status="Success",
				wc_id=wc_order_id,
				erpnext_doctype="Sales Order",
				erpnext_docname=so_name,
				message=f"Created Sales Order from WC Order #{wc_order.get('number')}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Order",
				direction="Pull",
				status="Failed",
				wc_id=wc_order.get("id"),
				message=str(e),
				request_data=wc_order,
			)
			frappe.log_error(
				title=f"WC Order Sync Error: #{wc_order.get('number')}",
				message=frappe.get_traceback(),
			)


def _create_sales_order(wc_order, settings):
	"""Create a Sales Order from WooCommerce order data."""
	customer_name = _get_or_create_customer(wc_order, settings)

	so = frappe.new_doc("Sales Order")
	so.customer = customer_name
	so.company = settings.company
	from frappe.utils import add_days
	
	transaction_date = (wc_order.get("date_created") or "")[:10]
	so.transaction_date = transaction_date
	so.delivery_date = add_days(transaction_date, 3) if transaction_date else None
	# No longer saving custom_woocommerce_id
	so.po_no = f"WC-{wc_order.get('number', wc_order.get('id'))}"
	so.set_warehouse = settings.default_warehouse

	if settings.cost_center:
		so.cost_center = settings.cost_center

	# Add line items
	for line_item in wc_order.get("line_items", []):
		item_code = _get_item_code(line_item, settings)
		so.append("items", {
			"item_code": item_code,
			"qty": line_item.get("quantity", 1),
			"rate": float(line_item.get("price", 0)),
			"warehouse": settings.default_warehouse,
			"delivery_date": so.delivery_date,
		})

	# Add shipping as a line item if applicable
	shipping_total = float(wc_order.get("shipping_total", 0))
	if shipping_total > 0 and settings.freight_account:
		shipping_item = _get_or_create_shipping_item()
		so.append("items", {
			"item_code": shipping_item,
			"qty": 1,
			"rate": shipping_total,
			"warehouse": settings.default_warehouse,
			"delivery_date": so.delivery_date,
		})

	# Apply taxes
	_apply_taxes(so, wc_order, settings)

	# Apply coupon discounts
	_apply_coupon_discounts(so, wc_order, settings)

	# Apply loyalty points if applicable
	_apply_loyalty_points(so, wc_order, settings)

	so.flags.ignore_permissions = True
	so.flags.ignore_mandatory = True
	so.save()
	so.submit()
	frappe.db.commit()

	return so.name


def _get_or_create_customer(wc_order, settings):
	"""Get or create the customer for a WooCommerce order."""
	billing = wc_order.get("billing", {})
	email = billing.get("email")
	
	if email:
		existing = _get_customer_by_email(email)
		if existing:
			return existing

	# Create guest customer from billing info
	first_name = billing.get("first_name", "")
	last_name = billing.get("last_name", "")
	full_name = f"{first_name} {last_name}".strip() or email or f"WC Guest {wc_order.get('id')}"

	customer = frappe.new_doc("Customer")
	customer.customer_name = full_name
	customer.customer_type = "Individual"
	customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
	customer.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
	customer.company = settings.company

	# No longer saving custom_woocommerce_id
	customer.flags.ignore_permissions = True
	customer.flags.ignore_mandatory = True
	customer.save()
	frappe.db.commit()

	return customer.name


def _get_customer_by_email(email):
	"""Find a customer by email through linked contacts."""
	contacts = frappe.get_all("Contact", filters={"email_id": email}, fields=["name"])
	for contact in contacts:
		links = frappe.get_all("Dynamic Link", 
			filters={"parent": contact.name, "link_doctype": "Customer"}, 
			fields=["link_name"]
		)
		if links:
			return links[0].link_name
	return None


def _get_item_code(line_item, settings):
	"""Get the ERPNext Item Code for a WooCommerce line item."""
	sku = line_item.get("sku")
	
	if sku:
		existing = frappe.db.get_value("Item", {"item_code": sku}, "name")
		if existing:
			return existing

	# Create a new item
	item = frappe.new_doc("Item")
	item.item_code = sku or f"WC-{line_item.get('product_id')}"
	item.item_name = line_item.get("name", f"WC Product {line_item.get('product_id')}")
	item.item_group = settings.default_item_group or "All Item Groups"
	item.stock_uom = settings.default_uom or "Nos"
	item.is_stock_item = 1
	# No longer saving custom_woocommerce_id
	item.flags.ignore_permissions = True
	item.save()
	frappe.db.commit()

	return item.name


def _get_or_create_shipping_item():
	"""Get or create a Shipping item for freight charges."""
	if not frappe.db.exists("Item", "WC-Shipping"):
		item = frappe.new_doc("Item")
		item.item_code = "WC-Shipping"
		item.item_name = "WooCommerce Shipping"
		item.item_group = "All Item Groups"
		item.stock_uom = "Nos"
		item.is_stock_item = 0
		item.flags.ignore_permissions = True
		item.save()
		frappe.db.commit()

	return "WC-Shipping"


def _apply_taxes(so, wc_order, settings):
	"""Apply tax charges from WooCommerce order to Sales Order."""
	tax_total = float(wc_order.get("total_tax", 0))
	if tax_total <= 0:
		return

	# Check for tax mapping
	tax_lines = wc_order.get("tax_lines", [])
	for tax_mapping in settings.tax_mappings:
		for tax_line in tax_lines:
			if tax_line.get("rate_code", "").lower() == tax_mapping.wc_tax_class.lower():
				so.taxes_and_charges = tax_mapping.tax_template
				so.set_taxes()
				return

	# Fallback: add tax as a direct charge
	if settings.tax_account:
		so.append("taxes", {
			"charge_type": "Actual",
			"account_head": settings.tax_account,
			"tax_amount": tax_total,
			"description": "WooCommerce Tax",
			"cost_center": settings.cost_center,
		})


def _apply_coupon_discounts(so, wc_order, settings):
	"""Apply WooCommerce coupon discounts to the Sales Order."""
	coupon_lines = wc_order.get("coupon_lines", [])
	if not coupon_lines:
		return

	total_discount = sum(float(c.get("discount", 0)) for c in coupon_lines)
	if total_discount > 0:
		so.discount_amount = total_discount
		so.additional_discount_account = settings.default_discount_account


def _apply_loyalty_points(so, wc_order, settings):
	"""Apply loyalty points redemption from WooCommerce order."""
	if not settings.enable_loyalty_points or not settings.loyalty_program:
		return

	# Check meta_data for loyalty points redemption
	meta_data = wc_order.get("meta_data", [])
	for meta in meta_data:
		if meta.get("key") in ("_wc_points_redeemed", "_loyalty_points_redeemed", "points_redeemed"):
			points = int(meta.get("value", 0))
			if points > 0:
				so.loyalty_program = settings.loyalty_program
				so.loyalty_points = points
				break
