# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Steadfast Courier API client."""

import json

import frappe
import requests


def _get_headers(provider):
	"""Get API headers with authentication."""
	return {
		"Api-Key": provider.api_key,
		"Secret-Key": provider.get_password("api_secret"),
		"Content-Type": "application/json",
	}


def create_parcel(provider, data):
	"""Create a delivery order in Steadfast.

	Args:
		provider: Delivery Service Provider document
		data: dict with recipient_name, recipient_phone, recipient_address, cod_amount, note, weight

	Returns:
		dict with API response including consignment details
	"""
	url = f"{provider.api_base_url.rstrip('/')}/create_order"

	payload = {
		"invoice": data.get("invoice", ""),
		"recipient_name": data.get("recipient_name", ""),
		"recipient_phone": data.get("recipient_phone", ""),
		"recipient_address": data.get("recipient_address", ""),
		"cod_amount": data.get("cod_amount", 0),
		"note": data.get("note", ""),
	}

	try:
		response = requests.post(url, headers=_get_headers(provider), json=payload, timeout=30)
		result = response.json()

		if response.status_code == 200 and result.get("status") == 200:
			return result

		frappe.log_error(
			title="Steadfast Create Order Error",
			message=f"Status: {response.status_code}\nResponse: {json.dumps(result, indent=2)}",
		)
		return result

	except Exception as e:
		frappe.log_error(
			title="Steadfast API Error",
			message=frappe.get_traceback(),
		)
		raise


def get_delivery_status(provider, consignment_id):
	"""Check delivery status by consignment ID.

	Args:
		provider: Delivery Service Provider document
		consignment_id: Steadfast consignment ID

	Returns:
		dict with delivery status details
	"""
	url = f"{provider.api_base_url.rstrip('/')}/status_by_cid/{consignment_id}"

	try:
		response = requests.get(url, headers=_get_headers(provider), timeout=30)
		result = response.json()

		if response.status_code == 200:
			return result.get("delivery_status") if isinstance(result, dict) else result

		return None

	except Exception as e:
		frappe.log_error(
			title=f"Steadfast Status Check Error: {consignment_id}",
			message=frappe.get_traceback(),
		)
		return None


def get_balance(provider):
	"""Check Steadfast account balance.

	Args:
		provider: Delivery Service Provider document

	Returns:
		float balance amount
	"""
	url = f"{provider.api_base_url.rstrip('/')}/get_balance"

	try:
		response = requests.get(url, headers=_get_headers(provider), timeout=30)
		result = response.json()

		if response.status_code == 200:
			return result.get("current_balance", 0)

		return 0

	except Exception as e:
		frappe.log_error(
			title="Steadfast Balance Check Error",
			message=frappe.get_traceback(),
		)
		return 0


def bulk_create_parcels(provider, parcels):
	"""Create multiple delivery orders in bulk.

	Args:
		provider: Delivery Service Provider document
		parcels: list of dicts with parcel data

	Returns:
		dict with API response
	"""
	url = f"{provider.api_base_url.rstrip('/')}/create_order/bulk-order"

	try:
		response = requests.post(url, headers=_get_headers(provider), json=parcels, timeout=60)
		return response.json()

	except Exception as e:
		frappe.log_error(
			title="Steadfast Bulk Order Error",
			message=frappe.get_traceback(),
		)
		raise
