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
			item_name = _create_or_update_item(product, settings)
			create_sync_log(
				sync_type="Item",
				direction="Pull",
				status="Success",
				wc_id=product.get("id"),
				erpnext_doctype="Item",
				erpnext_docname=item_name,
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
		fields=["name", "item_name", "description", "standard_rate", "weight_per_unit"],
	)

	for item in items:
		try:
			item_doc = frappe.get_doc("Item", item.name)
			product_data = _prepare_product_data(item_doc, settings)
			
			wc_id = _get_wc_id_by_sku(api, item_doc.item_code)

			if wc_id:
				# Update existing product
				response = api.put(f"products/{wc_id}", product_data)
			else:
				# Create new product
				response = api.post("products", product_data)

			if response.status_code in (200, 201):
				wc_product = response.json()
				# We no longer save the ID to custom_woocommerce_id
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

@frappe.whitelist()
def push_item_to_woocommerce(item_name):
	"""Push a single Item from ERPNext to WooCommerce."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled:
		frappe.throw("WooCommerce integration is disabled")

	api = get_wc_api(settings)
	item_doc = frappe.get_doc("Item", item_name)
	product_data = _prepare_product_data(item_doc, settings)

	try:
		wc_id = _get_wc_id_by_sku(api, item_doc.item_code)

		if wc_id:
			# Update existing product
			response = api.put(f"products/{wc_id}", product_data)
		else:
			# Create new product
			response = api.post("products", product_data)

		if response.status_code in (200, 201):
			wc_product = response.json()
			# No longer saving the ID to custom_woocommerce_id
			# Just mark for sync

			create_sync_log(
				sync_type="Item",
				direction="Push",
				status="Success",
				wc_id=wc_product.get("id"),
				erpnext_doctype="Item",
				erpnext_docname=item_name,
				message=f"Pushed item: {item_doc.item_name}",
			)
			return {"status": "Success", "message": f"Item {item_name} pushed to WooCommerce"}
		else:
			error_msg = f"API Error: {response.status_code}"
			response_data = response.json() if response.text else None
			create_sync_log(
				sync_type="Item",
				direction="Push",
				status="Failed",
				erpnext_doctype="Item",
				erpnext_docname=item_name,
				message=error_msg,
				response_data=response_data,
			)
			frappe.throw(f"Failed to push item to WooCommerce: {error_msg}")
	except Exception as e:
		create_sync_log(
			sync_type="Item",
			direction="Push",
			status="Failed",
			erpnext_doctype="Item",
			erpnext_docname=item_name,
			message=str(e),
		)
		frappe.log_error(
			title=f"WC Item Push Error: {item_doc.item_name}",
			message=frappe.get_traceback(),
		)
		frappe.throw(f"Failed to push item to WooCommerce: {e}")


def _create_or_update_item(product, settings):
	"""Create or update an ERPNext Item from a WooCommerce product."""
	wc_id = str(product.get("id"))
	sku = product.get("sku")
	
	existing_item = None
	if sku:
		existing_item = frappe.db.get_value("Item", {"item_code": sku}, "name")
	
	if not existing_item:
		# Fallback to name if SKU is empty but name matches? 
		# No, best to match by item_code which should be SKU
		pass

	if existing_item:
		item = frappe.get_doc("Item", existing_item)
	else:
		item = frappe.new_doc("Item")
		item.item_code = sku or f"WC-{wc_id}"
		item.item_group = _resolve_item_group(product, settings)
		item.stock_uom = settings.default_uom or "Nos"
		item.is_stock_item = 1 if product.get("manage_stock") else 0

	item.item_name = product.get("name")
	item.description = product.get("description") or product.get("short_description") or product.get("name")

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


@frappe.whitelist()
def push_item_group_to_woocommerce(item_group_name):
	"""Push a single Item Group from ERPNext to WooCommerce as a category."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled:
		frappe.throw("WooCommerce integration is disabled")

	api = get_wc_api(settings)
	item_group_doc = frappe.get_doc("Item Group", item_group_name)
	category_data = _prepare_category_data(item_group_doc, settings)

	try:
		wc_id = _get_wc_category_id_by_name(api, item_group_name)

		if wc_id:
			# Update existing category
			response = api.put(f"products/categories/{wc_id}", category_data)
		else:
			# Create new category
			response = api.post("products/categories", category_data)

		if response.status_code in (200, 201):
			wc_category = response.json()
			
			# Add to mapping if not exists
			_update_category_mapping(settings, str(wc_category.get("id")), item_group_name)

			create_sync_log(
				sync_type="Item",
				direction="Push",
				status="Success",
				wc_id=wc_category.get("id"),
				erpnext_doctype="Item Group",
				erpnext_docname=item_group_name,
				message=f"Pushed item group: {item_group_name}",
			)
			return {"status": "Success", "message": f"Item Group {item_group_name} pushed to WooCommerce"}
		else:
			error_msg = f"API Error: {response.status_code}"
			response_data = response.json() if response.text else None
			create_sync_log(
				sync_type="Item",
				direction="Push",
				status="Failed",
				erpnext_doctype="Item Group",
				erpnext_docname=item_group_name,
				message=error_msg,
				response_data=response_data,
			)
			frappe.throw(f"Failed to push item group to WooCommerce: {error_msg}")
	except Exception as e:
		create_sync_log(
			sync_type="Item",
			direction="Push",
			status="Failed",
			erpnext_doctype="Item Group",
			erpnext_docname=item_group_name,
			message=str(e),
		)
		frappe.log_error(
			title=f"WC Item Group Push Error: {item_group_name}",
			message=frappe.get_traceback(),
		)
		frappe.throw(f"Failed to push item group to WooCommerce: {e}")


def _prepare_category_data(item_group_doc, settings):
	"""Convert ERPNext Item Group to WooCommerce category data."""
	data = {
		"name": item_group_doc.item_group_name,
		"description": item_group_doc.description or "",
	}

	# Parent category matching is tricky without IDs. 
	# We'd have to search for the parent ID in WC by name.
	if item_group_doc.parent_item_group:
		api = get_wc_api(settings)
		parent_wc_id = _get_wc_category_id_by_name(api, item_group_doc.parent_item_group)
		if parent_wc_id:
			data["parent"] = int(parent_wc_id)

	return data


def _update_category_mapping(settings, wc_id, item_group):
	"""Update category mappings table in settings."""
	found = False
	for mapping in settings.category_mappings:
		if mapping.item_group == item_group:
			mapping.wc_category_id = wc_id
			found = True
			break
	
	if not found:
		settings.append("category_mappings", {
			"wc_category_id": wc_id,
			"wc_category_name": item_group,
			"item_group": item_group
		})
	
	settings.save(ignore_permissions=True)


def _get_wc_id_by_sku(api, sku):
	"""Search WooCommerce for a product ID by its SKU."""
	if not sku:
		return None
	response = api.get("products", params={"sku": sku})
	if response.status_code == 200:
		products = response.json()
		if products:
			return products[0].get("id")
	return None


def _get_wc_category_id_by_name(api, name):
	"""Search WooCommerce for a category ID by its name."""
	if not name:
		return None
	# WooCommerce API doesn't support direct filtering by name for categories easily in one call,
	# but we can try searching.
	response = api.get("products/categories", params={"search": name})
	if response.status_code == 200:
		categories = response.json()
		for cat in categories:
			if cat.get("name") == name:
				return cat.get("id")
	return None


def _prepare_product_data(item_doc, settings):
	"""Convert ERPNext Item to WooCommerce product data."""
	data = {
		"name": item_doc.item_name,
		"description": item_doc.description or "",
		"short_description": item_doc.description or "",
		"sku": item_doc.item_code,
		"manage_stock": bool(item_doc.is_stock_item),
	}

	if item_doc.get("weight_per_unit"):
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

	# Include item image
	if item_doc.get("image"):
		from frappe.utils import get_url
		image_url = get_url(item_doc.image)
		data["images"] = [{"src": image_url}]

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


def _resolve_item_group(product, settings):
	"""Resolve the ERPNext Item Group from WooCommerce product categories."""
	categories = product.get("categories", [])
	if not categories:
		return settings.default_item_group or "All Item Groups"

	# Check category mappings
	for wc_cat in categories:
		wc_cat_id = str(wc_cat.get("id", ""))
		for mapping in settings.category_mappings:
			if mapping.wc_category_id == wc_cat_id:
				return mapping.item_group

	# If no mapping found, try to auto-create Item Group from first category name
	if settings.sync_categories:
		first_cat = categories[0]
		cat_name = first_cat.get("name", "")
		if cat_name and not frappe.db.exists("Item Group", cat_name):
			ig = frappe.new_doc("Item Group")
			ig.item_group_name = cat_name
			ig.parent_item_group = settings.default_item_group or "All Item Groups"
			ig.flags.ignore_permissions = True
			ig.save()
			frappe.db.commit()
		if cat_name and frappe.db.exists("Item Group", cat_name):
			return cat_name

	return settings.default_item_group or "All Item Groups"


def sync_categories_from_woocommerce():
	"""Pull product categories from WooCommerce and create Item Groups + mappings."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_categories:
		return

	wc_categories = get_all_wc_resources("products/categories")

	for wc_cat in wc_categories:
		try:
			wc_cat_id = str(wc_cat.get("id"))
			cat_name = wc_cat.get("name", "").strip()

			if not cat_name or cat_name.lower() == "uncategorized":
				continue

			# Determine parent Item Group
			parent_group = settings.default_item_group or "All Item Groups"
			wc_parent_id = str(wc_cat.get("parent", 0))
			if wc_parent_id and wc_parent_id != "0":
				# Find parent mapping
				for mapping in settings.category_mappings:
					if mapping.wc_category_id == wc_parent_id:
						parent_group = mapping.item_group
						break

			# Create Item Group if it doesn't exist
			if not frappe.db.exists("Item Group", cat_name):
				ig = frappe.new_doc("Item Group")
				ig.item_group_name = cat_name
				ig.parent_item_group = parent_group
				ig.flags.ignore_permissions = True
				ig.save()

			# Add or update mapping in settings
			existing_mapping = False
			for mapping in settings.category_mappings:
				if mapping.wc_category_id == wc_cat_id:
					mapping.wc_category_name = cat_name
					mapping.item_group = cat_name
					existing_mapping = True
					break

			if not existing_mapping:
				settings.append("category_mappings", {
					"wc_category_id": wc_cat_id,
					"wc_category_name": cat_name,
					"item_group": cat_name,
				})

			create_sync_log(
				sync_type="Item",
				direction="Pull",
				status="Success",
				wc_id=wc_cat_id,
				erpnext_doctype="Item Group",
				erpnext_docname=cat_name,
				message=f"Synced category: {cat_name}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Item",
				direction="Pull",
				status="Failed",
				wc_id=wc_cat.get("id"),
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Category Sync Error: {wc_cat.get('name')}",
				message=frappe.get_traceback(),
			)

	settings.save(ignore_permissions=True)
	frappe.db.commit()
