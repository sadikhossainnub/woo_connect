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
	email = wc_customer.get("email") or wc_customer.get("billing", {}).get("email")
	phone = wc_customer.get("billing", {}).get("phone") or wc_customer.get("shipping", {}).get("phone")
	wc_id = str(wc_customer.get("id"))
	
	existing = None
	if email:
		existing = _get_customer_by_email(email)
	if not existing and phone:
		existing = _get_customer_by_phone(phone)

	first_name = wc_customer.get("first_name") or wc_customer.get("billing", {}).get("first_name", "")
	last_name = wc_customer.get("last_name") or wc_customer.get("billing", {}).get("last_name", "")
	full_name = f"{first_name} {last_name}".strip() or email or phone or f"WC Customer {wc_id}"

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

	# No longer saving custom_woocommerce_id
	customer.flags.ignore_permissions = True
	customer.flags.ignore_mandatory = True
	customer.save()

	# Create or update Contact
	contact_name = _create_or_update_contact(wc_customer, customer.name)

	# Create or update Address (billing)
	billing = wc_customer.get("billing", {})
	addr_name = None
	if billing and (billing.get("address_1") or billing.get("city") or billing.get("phone")):
		addr_name = _create_or_update_address(billing, customer.name, "Billing")

	# Create or update Address (shipping)
	shipping = wc_customer.get("shipping", {})
	if shipping and (shipping.get("address_1") or shipping.get("city") or shipping.get("phone")):
		_create_or_update_address(shipping, customer.name, "Shipping")

	# Update primary contact, address and mobile number on Customer
	customer_updated = False
	if contact_name and customer.customer_primary_contact != contact_name:
		customer.customer_primary_contact = contact_name
		customer_updated = True
	if addr_name and customer.customer_primary_address != addr_name:
		customer.customer_primary_address = addr_name
		customer_updated = True
	
	phone = wc_customer.get("billing", {}).get("phone") or wc_customer.get("shipping", {}).get("phone")
	if phone and customer.get("mobile_no") != phone:
		customer.mobile_no = phone
		customer_updated = True
		
	if customer_updated:
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


def _get_customer_by_phone(phone):
	"""Find a customer by phone through linked contacts."""
	contacts = frappe.get_all("Contact Phone", filters={"phone": phone}, fields=["parent"])
	for contact in contacts:
		links = frappe.get_all("Dynamic Link", 
			filters={"parent": contact.parent, "link_doctype": "Customer"}, 
			fields=["link_name"]
		)
		if links:
			return links[0].link_name
	return None


def _create_or_update_contact(wc_customer, customer_name):
	"""Create or update a Contact linked to the Customer."""
	email = wc_customer.get("email") or wc_customer.get("billing", {}).get("email")
	phone = wc_customer.get("billing", {}).get("phone") or wc_customer.get("shipping", {}).get("phone")
	if not email and not phone:
		return None

	existing_contact = None
	if email:
		existing_contact = frappe.db.get_value("Contact", {"email_id": email}, "name")
	
	if not existing_contact and phone:
		contact_phones = frappe.get_all("Contact Phone", filters={"phone": phone}, fields=["parent"], limit=1)
		if contact_phones:
			existing_contact = contact_phones[0].parent

	if existing_contact:
		contact = frappe.get_doc("Contact", existing_contact)
	else:
		contact = frappe.new_doc("Contact")
		contact.first_name = wc_customer.get("first_name") or wc_customer.get("billing", {}).get("first_name") or email or phone or "Unknown"

	contact.first_name = wc_customer.get("first_name") or wc_customer.get("billing", {}).get("first_name") or email or phone or "Unknown"
	contact.last_name = wc_customer.get("last_name") or wc_customer.get("billing", {}).get("last_name") or ""
	contact.is_primary_contact = 1

	if getattr(contact, "phone_nos", None) is None:
		contact.phone_nos = []
	if getattr(contact, "email_ids", None) is None:
		contact.email_ids = []

	# Add email if not already present
	if email and not any(e.email_id == email for e in contact.email_ids):
		contact.append("email_ids", {"email_id": email, "is_primary": 1})

	# Add phone if available
	if phone and not any(p.phone == phone for p in contact.phone_nos):
		contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1, "is_primary_mobile_no": 1})

	# Link to customer
	if not any(l.link_doctype == "Customer" and l.link_name == customer_name for l in contact.links):
		contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	contact.flags.ignore_permissions = True
	contact.flags.ignore_mandatory = True
	contact.save()
	return contact.name


def _create_or_update_address(address_data, customer_name, address_type):
	"""Create or update an Address linked to the Customer."""
	# Without custom_woocommerce_id, we can only try to find by title or linked customer + type
	address_title = f"{customer_name}-{address_type}"
	
	existing = frappe.db.get_value("Address", {"address_title": address_title}, "name")

	if existing:
		address = frappe.get_doc("Address", existing)
	else:
		address = frappe.new_doc("Address")
		address.address_title = address_title
		address.address_type = address_type

	address.address_line1 = address_data.get("address_1") or "N/A"
	address.address_line2 = address_data.get("address_2", "")
	address.city = address_data.get("city", "")
	address.state = address_data.get("state", "")
	address.pincode = address_data.get("postcode", "")
	address.country = _get_country(address_data.get("country", ""))
	address.phone = address_data.get("phone", "")
	address.email_id = address_data.get("email", "")
	address.is_primary_address = 1 if address_type == "Billing" else 0
	address.is_shipping_address = 1 if address_type == "Shipping" else 0

	# Link to customer
	if not any(l.link_doctype == "Customer" and l.link_name == customer_name for l in address.links):
		address.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	address.flags.ignore_permissions = True
	address.flags.ignore_mandatory = True
	address.save()
	return address.name


def _get_country(country_code):
	"""Convert ISO country code to ERPNext country name."""
	if not country_code:
		return frappe.db.get_default("country") or "United States"

	country = frappe.db.get_value("Country", {"code": country_code.lower()}, "name")
	return country or frappe.db.get_default("country") or "United States"
