# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Addresses from WooCommerce orders to ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_addresses_from_woocommerce():
	"""Pull billing/shipping addresses from WooCommerce orders and sync to ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled:
		return

	orders = get_all_wc_resources("orders", params={"per_page": 50})

	for order in orders:
		try:
			customer_name = frappe.db.get_value(
				"Customer",
				{"custom_woocommerce_id": str(order.get("customer_id"))},
				"name",
			)
			if not customer_name:
				continue

			wc_order_id = str(order.get("id"))

			billing = order.get("billing", {})
			if billing and billing.get("address_1"):
				_sync_address(billing, customer_name, "Billing", f"order-{wc_order_id}-billing")

			shipping = order.get("shipping", {})
			if shipping and shipping.get("address_1"):
				_sync_address(shipping, customer_name, "Shipping", f"order-{wc_order_id}-shipping")

			create_sync_log(
				sync_type="Customer",
				direction="Pull",
				status="Success",
				wc_id=wc_order_id,
				erpnext_doctype="Address",
				message=f"Address synced for order {wc_order_id}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Customer",
				direction="Pull",
				status="Failed",
				wc_id=order.get("id"),
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Address Sync Error: Order {order.get('id')}",
				message=frappe.get_traceback(),
			)


def _sync_address(address_data, customer_name, address_type, wc_address_id):
	"""Create or update an Address from WooCommerce order address data."""
	existing = frappe.db.get_value("Address", {"custom_woocommerce_id": wc_address_id}, "name")

	if existing:
		address = frappe.get_doc("Address", existing)
	else:
		address = frappe.new_doc("Address")
		address.address_title = f"{customer_name}-{address_type}"
		address.address_type = address_type

	address.address_line1 = address_data.get("address_1", "")
	address.address_line2 = address_data.get("address_2", "")
	address.city = address_data.get("city", "")
	address.state = address_data.get("state", "")
	address.pincode = address_data.get("postcode", "")
	address.country = _get_country(address_data.get("country", ""))
	address.phone = address_data.get("phone", "")
	address.email_id = address_data.get("email", "")
	address.custom_woocommerce_id = wc_address_id

	if not any(l.link_doctype == "Customer" and l.link_name == customer_name for l in address.links):
		address.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	address.flags.ignore_permissions = True
	address.flags.ignore_mandatory = True
	address.save()
	frappe.db.commit()


def _get_country(country_code):
	"""Convert ISO country code to ERPNext country name."""
	if not country_code:
		return frappe.db.get_default("country") or "United States"

	country = frappe.db.get_value("Country", {"code": country_code.lower()}, "name")
	return country or frappe.db.get_default("country") or "United States"
