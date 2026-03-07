# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Items between WooCommerce and ERPNext."""

import frappe
from woo_connect.woocommerce_connect.utils.api_client import (
	create_sync_log,
	get_all_wc_resources,
	get_wc_api,
)


def sync_items_from_woocommerce():
	"""Pull products from WooCommerce and create/update Items in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_items:
		return

	products = get_all_wc_resources("products", params={"status": "publish"})

	for product in products:
		try:
			_create_or_update_item(product, settings)
			create_sync_log(
				sync_type="Item",
				direction="Pull",
				status="Success",
				wc_id=product.get("id"),
				erpnext_doctype="Item",
				erpnext_docname=_get_item_name_by_wc_id(product.get("id")),
				message=f"Synced product: {product.get('name')}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Item",
				direction="Pull",
				status="Failed",
				wc_id=product.get("id"),
				message=str(e),
				request_data=product,
			)
			frappe.log_error(
				title=f"WC Item Sync Error: {product.get('name')}",
				message=frappe.get_traceback(),
			)


def sync_items_to_woocommerce():
	"""Push Items from ERPNext to WooCommerce."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_items:
		return

	api = get_wc_api(settings)

	# Get items marked for WooCommerce sync
	items = frappe.get_all(
		"Item",
		filters={"custom_woocommerce_sync": 1},
		fields=["name", "item_name", "description", "standard_rate", "weight_per_unit", "custom_woocommerce_id"],
	)

	for item in items:
		try:
			item_doc = frappe.get_doc("Item", item.name)
			product_data = _prepare_product_data(item_doc, settings)

			if item.custom_woocommerce_id:
				# Update existing product
				response = api.put(f"products/{item.custom_woocommerce_id}", product_data)
			else:
				# Create new product
				response = api.post("products", product_data)

			if response.status_code in (200, 201):
				wc_product = response.json()
				frappe.db.set_value("Item", item.name, "custom_woocommerce_id", str(wc_product.get("id")))
				frappe.db.commit()

				create_sync_log(
					sync_type="Item",
					direction="Push",
					status="Success",
					wc_id=wc_product.get("id"),
					erpnext_doctype="Item",
					erpnext_docname=item.name,
					message=f"Pushed item: {item.item_name}",
				)
			else:
				create_sync_log(
					sync_type="Item",
					direction="Push",
					status="Failed",
					erpnext_doctype="Item",
					erpnext_docname=item.name,
					message=f"API Error: {response.status_code}",
					response_data=response.json() if response.text else None,
				)
		except Exception as e:
			create_sync_log(
				sync_type="Item",
				direction="Push",
				status="Failed",
				erpnext_doctype="Item",
				erpnext_docname=item.name,
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Item Push Error: {item.item_name}",
				message=frappe.get_traceback(),
			)


def _create_or_update_item(product, settings):
	"""Create or update an ERPNext Item from a WooCommerce product."""
	wc_id = str(product.get("id"))
	existing_item = _get_item_name_by_wc_id(wc_id)

	if existing_item:
		item = frappe.get_doc("Item", existing_item)
	else:
		item = frappe.new_doc("Item")
		item.item_code = product.get("sku") or f"WC-{wc_id}"
		item.item_group = settings.default_item_group or "All Item Groups"
		item.stock_uom = settings.default_uom or "Nos"
		item.is_stock_item = 1 if product.get("manage_stock") else 0

	item.item_name = product.get("name")
	item.description = product.get("description") or product.get("short_description") or product.get("name")
	item.custom_woocommerce_id = wc_id
	item.custom_woocommerce_sync = 1

	if product.get("weight"):
		item.weight_per_unit = float(product.get("weight"))

	item.flags.ignore_permissions = True
	item.save()

	# Set item price if available
	regular_price = product.get("regular_price") or product.get("price")
	if regular_price and settings.default_price_list:
		_set_item_price(item.name, regular_price, settings.default_price_list)

	frappe.db.commit()
	return item.name


def _get_item_name_by_wc_id(wc_id):
	"""Get Item name by WooCommerce ID."""
	if not wc_id:
		return None
	return frappe.db.get_value("Item", {"custom_woocommerce_id": str(wc_id)}, "name")


def _prepare_product_data(item_doc, settings):
	"""Convert ERPNext Item to WooCommerce product data."""
	data = {
		"name": item_doc.item_name,
		"description": item_doc.description or "",
		"short_description": item_doc.description or "",
		"sku": item_doc.item_code,
		"manage_stock": bool(item_doc.is_stock_item),
	}

	if item_doc.weight_per_unit:
		data["weight"] = str(item_doc.weight_per_unit)

	# Get price
	if settings.default_price_list:
		price = frappe.db.get_value(
			"Item Price",
			{"item_code": item_doc.name, "price_list": settings.default_price_list},
			"price_list_rate",
		)
		if price:
			data["regular_price"] = str(price)

	return data


def _set_item_price(item_code, price, price_list):
	"""Set or update Item Price."""
	existing = frappe.db.get_value(
		"Item Price",
		{"item_code": item_code, "price_list": price_list},
		"name",
	)

	if existing:
		frappe.db.set_value("Item Price", existing, "price_list_rate", float(price))
	else:
		item_price = frappe.new_doc("Item Price")
		item_price.item_code = item_code
		item_price.price_list = price_list
		item_price.price_list_rate = float(price)
		item_price.flags.ignore_permissions = True
		item_price.save()
