# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Sales Invoices from WooCommerce completed orders to ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_invoices_from_woocommerce():
	"""Create Sales Invoices for completed WooCommerce orders that have Sales Orders in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_invoices:
		return

	orders = get_all_wc_resources("orders", params={"status": "completed", "per_page": 50})

	for wc_order in orders:
		try:
			wc_order_id = str(wc_order.get("id"))
			wc_order_no = f"WC-{wc_order.get('number', wc_order.get('id'))}"

			# Check if Sales Order exists by PO No
			so_name = frappe.db.get_value("Sales Order", {"po_no": wc_order_no}, "name")
			if not so_name:
				continue

			# Skip if invoice already created for this Sales Order
			if frappe.db.exists("Sales Invoice Item", {"sales_order": so_name}):
				continue

			# Check if Sales Order is submitted
			so_status = frappe.db.get_value("Sales Order", so_name, "docstatus")
			if so_status != 1:
				continue

			si_name = _create_sales_invoice(so_name, settings)
			create_sync_log(
				sync_type="Invoice",
				direction="Pull",
				status="Success",
				wc_id=wc_order_id,
				erpnext_doctype="Sales Invoice",
				erpnext_docname=si_name,
				message=f"Created Sales Invoice from WC Order #{wc_order.get('number')}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Invoice",
				direction="Pull",
				status="Failed",
				wc_id=wc_order.get("id"),
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Invoice Sync Error: #{wc_order.get('number')}",
				message=frappe.get_traceback(),
			)


def _create_sales_invoice(so_name, settings):
	"""Create a Sales Invoice from a Sales Order."""
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	si = make_sales_invoice(so_name)
	si.set_posting_time = 1
	si.flags.ignore_permissions = True
	si.flags.ignore_mandatory = True
	si.save()
	si.submit()
	frappe.db.commit()

	return si.name
