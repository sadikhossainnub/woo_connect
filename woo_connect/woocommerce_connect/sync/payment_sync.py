# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Payment Entries from WooCommerce paid orders to ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_payments_from_woocommerce():
	"""Create Payment Entries for paid WooCommerce orders that have Sales Invoices in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_payments:
		return

	orders = get_all_wc_resources("orders", params={"status": "completed", "per_page": 50})

	for wc_order in orders:
		try:
			wc_order_id = str(wc_order.get("id"))

			# Check if Sales Invoice exists
			si_name = frappe.db.get_value("Sales Invoice", {"custom_woocommerce_id": wc_order_id}, "name")
			if not si_name:
				continue

			# Skip if Payment Entry already exists
			if frappe.db.exists("Payment Entry", {"custom_woocommerce_id": wc_order_id}):
				continue

			# Check if invoice is submitted and unpaid
			si_doc = frappe.get_doc("Sales Invoice", si_name)
			if si_doc.docstatus != 1 or si_doc.outstanding_amount <= 0:
				continue

			pe_name = _create_payment_entry(si_doc, wc_order, settings)
			if pe_name:
				create_sync_log(
					sync_type="Payment",
					direction="Pull",
					status="Success",
					wc_id=wc_order_id,
					erpnext_doctype="Payment Entry",
					erpnext_docname=pe_name,
					message=f"Payment created for WC Order #{wc_order.get('number')}",
				)
		except Exception as e:
			create_sync_log(
				sync_type="Payment",
				direction="Pull",
				status="Failed",
				wc_id=wc_order.get("id"),
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Payment Sync Error: #{wc_order.get('number')}",
				message=frappe.get_traceback(),
			)


def _create_payment_entry(si_doc, wc_order, settings):
	"""Create a Payment Entry for a Sales Invoice."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	wc_payment_method = wc_order.get("payment_method", "")
	mode_of_payment, payment_account = _get_payment_mapping(wc_payment_method, settings)

	pe = get_payment_entry("Sales Invoice", si_doc.name)
	pe.custom_woocommerce_id = str(wc_order.get("id"))

	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
	if payment_account:
		pe.paid_to = payment_account

	pe.reference_no = f"WC-{wc_order.get('number', wc_order.get('id'))}"
	pe.reference_date = (wc_order.get("date_paid") or wc_order.get("date_created") or "")[:10]

	pe.flags.ignore_permissions = True
	pe.flags.ignore_mandatory = True
	pe.save()
	pe.submit()
	frappe.db.commit()

	return pe.name


def _get_payment_mapping(wc_payment_method, settings):
	"""Get ERPNext Mode of Payment and Account from payment method mapping."""
	for mapping in settings.payment_method_mappings:
		if mapping.wc_payment_method.lower() == wc_payment_method.lower():
			return mapping.mode_of_payment, mapping.payment_account

	return None, None
