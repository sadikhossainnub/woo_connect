# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync stock levels from ERPNext to WooCommerce."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_wc_api


def sync_stock_to_woocommerce():
	"""Push stock quantities from ERPNext Bins to WooCommerce products."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_stock:
		return

	api = get_wc_api(settings)

	# Get all items with WooCommerce IDs
	items = frappe.get_all(
		"Item",
		filters={"custom_woocommerce_id": ["is", "set"]},
		fields=["name", "item_name", "custom_woocommerce_id"],
	)

	for item in items:
		try:
			# Get actual qty from the default warehouse
			qty = _get_stock_qty(item.name, settings.default_warehouse)

			product_data = {
				"stock_quantity": int(qty),
				"manage_stock": True,
			}

			response = api.put(f"products/{item.custom_woocommerce_id}", product_data)

			if response.status_code == 200:
				create_sync_log(
					sync_type="Stock",
					direction="Push",
					status="Success",
					wc_id=item.custom_woocommerce_id,
					erpnext_doctype="Item",
					erpnext_docname=item.name,
					message=f"Stock updated: {item.item_name} → {int(qty)}",
				)
			else:
				create_sync_log(
					sync_type="Stock",
					direction="Push",
					status="Failed",
					wc_id=item.custom_woocommerce_id,
					erpnext_doctype="Item",
					erpnext_docname=item.name,
					message=f"API Error: {response.status_code}",
					response_data=response.json() if response.text else None,
				)
		except Exception as e:
			create_sync_log(
				sync_type="Stock",
				direction="Push",
				status="Failed",
				wc_id=item.custom_woocommerce_id,
				erpnext_doctype="Item",
				erpnext_docname=item.name,
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Stock Sync Error: {item.item_name}",
				message=frappe.get_traceback(),
			)


def _get_stock_qty(item_code, warehouse):
	"""Get actual stock quantity for an item in a warehouse."""
	qty = frappe.db.get_value(
		"Bin",
		{"item_code": item_code, "warehouse": warehouse},
		"actual_qty",
	)
	return qty or 0
