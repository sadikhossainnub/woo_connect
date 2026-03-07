# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Customers from WooCommerce to ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_customers_from_woocommerce():
	"""Pull customers from WooCommerce and create/update in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_customers:
		return

	customers = get_all_wc_resources("customers")

	for wc_customer in customers:
		try:
			customer_name = _create_or_update_customer(wc_customer, settings)
			create_sync_log(
				sync_type="Customer",
				direction="Pull",
				status="Success",
				wc_id=wc_customer.get("id"),
				erpnext_doctype="Customer",
				erpnext_docname=customer_name,
				message=f"Synced customer: {wc_customer.get('first_name')} {wc_customer.get('last_name')}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Customer",
				direction="Pull",
				status="Failed",
				wc_id=wc_customer.get("id"),
				message=str(e),
				request_data=wc_customer,
			)
			frappe.log_error(
				title=f"WC Customer Sync Error: {wc_customer.get('email')}",
				message=frappe.get_traceback(),
			)


def _create_or_update_customer(wc_customer, settings):
	"""Create or update an ERPNext Customer from WooCommerce data."""
	wc_id = str(wc_customer.get("id"))
	existing = frappe.db.get_value("Customer", {"custom_woocommerce_id": wc_id}, "name")

	first_name = wc_customer.get("first_name", "")
	last_name = wc_customer.get("last_name", "")
	full_name = f"{first_name} {last_name}".strip() or wc_customer.get("email", f"WC Customer {wc_id}")

	if existing:
		customer = frappe.get_doc("Customer", existing)
		customer.customer_name = full_name
	else:
		customer = frappe.new_doc("Customer")
		customer.customer_name = full_name
		customer.customer_type = "Individual"
		customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
		customer.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
		customer.company = settings.company

	customer.custom_woocommerce_id = wc_id
	customer.flags.ignore_permissions = True
	customer.flags.ignore_mandatory = True
	customer.save()

	# Create or update Contact
	_create_or_update_contact(wc_customer, customer.name)

	# Create or update Address (billing)
	billing = wc_customer.get("billing", {})
	if billing and billing.get("address_1"):
		_create_or_update_address(billing, customer.name, "Billing", wc_id)

	# Create or update Address (shipping)
	shipping = wc_customer.get("shipping", {})
	if shipping and shipping.get("address_1"):
		_create_or_update_address(shipping, customer.name, "Shipping", wc_id)

	frappe.db.commit()
	return customer.name


def _create_or_update_contact(wc_customer, customer_name):
	"""Create or update a Contact linked to the Customer."""
	email = wc_customer.get("email")
	if not email:
		return

	existing_contact = frappe.db.get_value(
		"Contact",
		{"email_id": email},
		"name",
	)

	if existing_contact:
		contact = frappe.get_doc("Contact", existing_contact)
	else:
		contact = frappe.new_doc("Contact")
		contact.first_name = wc_customer.get("first_name") or email
		contact.last_name = wc_customer.get("last_name", "")

	contact.first_name = wc_customer.get("first_name") or email
	contact.last_name = wc_customer.get("last_name", "")

	# Add email if not already present
	if not any(e.email_id == email for e in contact.email_ids):
		contact.append("email_ids", {"email_id": email, "is_primary": 1})

	# Add phone if available
	phone = wc_customer.get("billing", {}).get("phone")
	if phone and not any(p.phone == phone for p in contact.phone_nos):
		contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1})

	# Link to customer
	if not any(l.link_doctype == "Customer" and l.link_name == customer_name for l in contact.links):
		contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	contact.flags.ignore_permissions = True
	contact.save()


def _create_or_update_address(address_data, customer_name, address_type, wc_id):
	"""Create or update an Address linked to the Customer."""
	address_title = f"{customer_name}-{address_type}"
	wc_address_id = f"{wc_id}-{address_type.lower()}"

	existing = frappe.db.get_value("Address", {"custom_woocommerce_id": wc_address_id}, "name")

	if existing:
		address = frappe.get_doc("Address", existing)
	else:
		address = frappe.new_doc("Address")
		address.address_title = address_title
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

	# Link to customer
	if not any(l.link_doctype == "Customer" and l.link_name == customer_name for l in address.links):
		address.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	address.flags.ignore_permissions = True
	address.flags.ignore_mandatory = True
	address.save()


def _get_country(country_code):
	"""Convert ISO country code to ERPNext country name."""
	if not country_code:
		return frappe.db.get_default("country") or "United States"

	country = frappe.db.get_value("Country", {"code": country_code.lower()}, "name")
	return country or frappe.db.get_default("country") or "United States"
