# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Loyalty Points from WooCommerce to ERPNext."""

import frappe
from frappe.utils import now_datetime
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_loyalty_points_from_woocommerce():
	"""Pull loyalty points data from WooCommerce and create Loyalty Point Entries in ERPNext.

	This works with WooCommerce loyalty/points plugins that expose
	customer point balances through the WC REST API customers endpoint
	meta_data or through a custom endpoint.
	"""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.enable_loyalty_points or not settings.loyalty_program:
		return

	customers = get_all_wc_resources("customers")

	for wc_customer in customers:
		try:
			wc_id = str(wc_customer.get("id"))
			customer_name = frappe.db.get_value("Customer", {"custom_woocommerce_id": wc_id}, "name")

			if not customer_name:
				continue

			# Look for loyalty points in customer meta_data
			points = _get_loyalty_points_from_meta(wc_customer)
			if points is None or points <= 0:
				continue

			_sync_loyalty_points(customer_name, points, settings)

			create_sync_log(
				sync_type="Loyalty",
				direction="Pull",
				status="Success",
				wc_id=wc_id,
				erpnext_doctype="Customer",
				erpnext_docname=customer_name,
				message=f"Synced {points} loyalty points for {customer_name}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Loyalty",
				direction="Pull",
				status="Failed",
				wc_id=wc_customer.get("id"),
				message=str(e),
			)
			frappe.log_error(
				title=f"WC Loyalty Sync Error: Customer {wc_customer.get('id')}",
				message=frappe.get_traceback(),
			)


def _get_loyalty_points_from_meta(wc_customer):
	"""Extract loyalty points from WooCommerce customer meta_data.

	Supports common WC loyalty plugins that store points in customer meta.
	"""
	meta_data = wc_customer.get("meta_data", [])
	loyalty_keys = (
		"wc_points_balance",
		"_wc_points_balance",
		"loyalty_points_balance",
		"_loyalty_points",
		"points_balance",
	)

	for meta in meta_data:
		if meta.get("key") in loyalty_keys:
			try:
				return int(float(meta.get("value", 0)))
			except (ValueError, TypeError):
				return None

	return None


def _sync_loyalty_points(customer_name, wc_points, settings):
	"""Create or adjust Loyalty Point Entry for a customer to match WC balance."""
	loyalty_program = settings.loyalty_program
	company = settings.company

	# Get current ERPNext loyalty points balance
	current_points = _get_current_points(customer_name, loyalty_program, company)

	# Calculate difference
	diff = wc_points - current_points
	if diff == 0:
		return

	# Create a Loyalty Point Entry to adjust balance
	lpe = frappe.new_doc("Loyalty Point Entry")
	lpe.loyalty_program = loyalty_program
	lpe.loyalty_program_tier = _get_default_tier(loyalty_program)
	lpe.customer = customer_name
	lpe.loyalty_points = abs(diff)
	lpe.purchase_amount = 0
	lpe.expiry_date = frappe.utils.add_years(now_datetime(), 1)
	lpe.company = company
	lpe.posting_date = frappe.utils.today()

	if diff < 0:
		# Points were redeemed in WooCommerce
		lpe.loyalty_points = -abs(diff)

	lpe.flags.ignore_permissions = True
	lpe.save()
	frappe.db.commit()


def _get_current_points(customer_name, loyalty_program, company):
	"""Get current loyalty points balance for a customer."""
	points = frappe.db.sql(
		"""
		SELECT IFNULL(SUM(loyalty_points), 0)
		FROM `tabLoyalty Point Entry`
		WHERE customer = %s
		AND loyalty_program = %s
		AND company = %s
		AND expiry_date >= CURDATE()
		""",
		(customer_name, loyalty_program, company),
	)

	return int(points[0][0]) if points else 0


def _get_default_tier(loyalty_program):
	"""Get the first tier from the Loyalty Program."""
	tier = frappe.db.get_value(
		"Loyalty Program Collection",
		{"parent": loyalty_program},
		"tier_name",
		order_by="min_total_points asc",
	)
	return tier
