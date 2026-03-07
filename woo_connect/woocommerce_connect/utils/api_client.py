# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""WooCommerce REST API client wrapper."""

import frappe
from woocommerce import API as WooCommerceAPI


def get_wc_api(settings=None):
	"""Return a configured WooCommerce API instance.

	Args:
		settings: Optional WooCommerce Server document. If None, fetches from DB.

	Returns:
		WooCommerceAPI instance
	"""
	if not settings:
		settings = frappe.get_single("WooCommerce Server")

	return WooCommerceAPI(
		url=settings.woocommerce_url,
		consumer_key=settings.api_key,
		consumer_secret=settings.get_password("api_secret"),
		version="wc/v3",
		timeout=40,
		verify_ssl=bool(settings.verify_ssl),
	)


def get_all_wc_resources(endpoint, params=None):
	"""Fetch all pages of a WooCommerce resource.

	Args:
		endpoint: WC API endpoint, e.g. 'products'
		params: Optional dict of query parameters

	Returns:
		list of all resource dicts
	"""
	api = get_wc_api()
	params = params or {}
	params.setdefault("per_page", 100)
	page = 1
	all_resources = []

	while True:
		params["page"] = page
		response = api.get(endpoint, params=params)

		if response.status_code != 200:
			frappe.log_error(
				title=f"WooCommerce API Error: {endpoint}",
				message=f"Status: {response.status_code}\nResponse: {response.text}",
			)
			break

		data = response.json()
		if not data:
			break

		all_resources.extend(data)

		# Check if there are more pages
		total_pages = int(response.headers.get("X-WP-TotalPages", 1))
		if page >= total_pages:
			break

		page += 1

	return all_resources


def create_sync_log(
	sync_type,
	direction,
	status,
	wc_id=None,
	erpnext_doctype=None,
	erpnext_docname=None,
	message=None,
	request_data=None,
	response_data=None,
):
	"""Create a WC Sync Log entry.

	Args:
		sync_type: Item, Customer, Order, Invoice, Payment, Stock, Coupon, Loyalty
		direction: Push or Pull
		status: Success, Failed, or Skipped
		wc_id: WooCommerce resource ID
		erpnext_doctype: ERPNext DocType name
		erpnext_docname: ERPNext document name
		message: Details / error message
		request_data: Request payload (dict or string)
		response_data: Response payload (dict or string)
	"""
	import json

	log = frappe.new_doc("WC Sync Log")
	log.sync_type = sync_type
	log.direction = direction
	log.status = status
	log.wc_id = str(wc_id) if wc_id else None
	log.erpnext_doctype = erpnext_doctype
	log.erpnext_docname = erpnext_docname
	log.message = message

	if request_data:
		log.request_data = json.dumps(request_data, indent=2, default=str) if isinstance(request_data, dict) else str(request_data)
	if response_data:
		log.response_data = json.dumps(response_data, indent=2, default=str) if isinstance(response_data, dict) else str(response_data)

	log.insert(ignore_permissions=True)
	frappe.db.commit()
