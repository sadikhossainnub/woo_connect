# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Sync Coupons/Discounts from WooCommerce to ERPNext."""

import frappe
from frappe.utils import getdate
from woo_connect.woocommerce_connect.utils.api_client import create_sync_log, get_all_wc_resources


def sync_coupons_from_woocommerce():
	"""Pull coupons from WooCommerce and create/update Pricing Rules and Coupon Codes in ERPNext."""
	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled or not settings.sync_coupons:
		return

	wc_coupons = get_all_wc_resources("coupons")

	for wc_coupon in wc_coupons:
		try:
			coupon_code = wc_coupon.get("code", "").upper()
			wc_id = str(wc_coupon.get("id"))

			pricing_rule_name, coupon_code_name = _create_or_update_coupon(wc_coupon, settings)

			# Update coupon mapping in settings
			_update_coupon_mapping(settings, coupon_code, wc_coupon.get("discount_type", ""), pricing_rule_name, coupon_code_name)

			create_sync_log(
				sync_type="Coupon",
				direction="Pull",
				status="Success",
				wc_id=wc_id,
				erpnext_doctype="Coupon Code",
				erpnext_docname=coupon_code_name,
				message=f"Synced coupon: {coupon_code}",
			)
		except Exception as e:
			create_sync_log(
				sync_type="Coupon",
				direction="Pull",
				status="Failed",
				wc_id=wc_coupon.get("id"),
				message=str(e),
				request_data=wc_coupon,
			)
			frappe.log_error(
				title=f"WC Coupon Sync Error: {wc_coupon.get('code')}",
				message=frappe.get_traceback(),
			)


def _create_or_update_coupon(wc_coupon, settings):
	"""Create or update a Pricing Rule and Coupon Code from WooCommerce coupon data."""
	coupon_code_str = wc_coupon.get("code", "").upper()
	wc_discount_type = wc_coupon.get("discount_type", "percent")
	amount = float(wc_coupon.get("amount", 0))

	# Map WC discount type to ERPNext
	if wc_discount_type == "percent":
		discount_type = "Discount Percentage"
		rate_or_discount = "Discount Percentage"
	else:
		discount_type = "Discount Amount"
		rate_or_discount = "Discount Amount"

	# Create or update Pricing Rule
	existing_pr = frappe.db.get_value(
		"Pricing Rule",
		{"title": f"WC-{coupon_code_str}"},
		"name",
	)

	if existing_pr:
		pr = frappe.get_doc("Pricing Rule", existing_pr)
	else:
		pr = frappe.new_doc("Pricing Rule")
		pr.title = f"WC-{coupon_code_str}"
		pr.apply_on = "Transaction"
		pr.selling = 1
		pr.coupon_code_based = 1
		pr.company = settings.company

	pr.rate_or_discount = rate_or_discount
	pr.price_or_product_discount = "Price"

	if discount_type == "Discount Percentage":
		pr.discount_percentage = amount
		pr.discount_amount = 0
	else:
		pr.discount_amount = amount
		pr.discount_percentage = 0

	# Set validity
	if wc_coupon.get("date_expires"):
		try:
			pr.valid_upto = getdate(wc_coupon.get("date_expires")[:10])
		except Exception:
			pass

	# Set min amount
	if wc_coupon.get("minimum_amount"):
		try:
			pr.min_amt = float(wc_coupon.get("minimum_amount"))
		except (ValueError, TypeError):
			pass

	# Set max amount
	if wc_coupon.get("maximum_amount"):
		try:
			pr.max_amt = float(wc_coupon.get("maximum_amount"))
		except (ValueError, TypeError):
			pass

	pr.flags.ignore_permissions = True
	pr.save()

	# Create or update Coupon Code
	existing_cc = frappe.db.get_value(
		"Coupon Code",
		{"coupon_code": coupon_code_str},
		"name",
	)

	if existing_cc:
		cc = frappe.get_doc("Coupon Code", existing_cc)
	else:
		cc = frappe.new_doc("Coupon Code")
		cc.coupon_name = f"WC-{coupon_code_str}"
		cc.coupon_code = coupon_code_str
		cc.coupon_type = "Promotional"

	cc.pricing_rule = pr.name

	# Set usage limits
	usage_limit = wc_coupon.get("usage_limit")
	if usage_limit:
		cc.maximum_use = int(usage_limit)

	usage_limit_per_user = wc_coupon.get("usage_limit_per_user")
	if usage_limit_per_user:
		cc.maximum_use = int(usage_limit_per_user)

	# Set validity
	if wc_coupon.get("date_expires"):
		try:
			cc.valid_upto = getdate(wc_coupon.get("date_expires")[:10])
		except Exception:
			pass

	cc.flags.ignore_permissions = True
	cc.save()
	frappe.db.commit()

	return pr.name, cc.name


def _update_coupon_mapping(settings, coupon_code, discount_type, pricing_rule_name, coupon_code_name):
	"""Update the coupon mapping in WooCommerce Server settings."""
	wc_type_map = {
		"percent": "Percentage",
		"fixed_cart": "Fixed Cart",
		"fixed_product": "Fixed Product",
	}

	# Check if mapping already exists
	for mapping in settings.coupon_mappings:
		if mapping.wc_coupon_code == coupon_code:
			mapping.pricing_rule = pricing_rule_name
			mapping.coupon_code = coupon_code_name
			mapping.discount_type = wc_type_map.get(discount_type, "Percentage")
			settings.save(ignore_permissions=True)
			return

	# Add new mapping
	settings.append("coupon_mappings", {
		"wc_coupon_code": coupon_code,
		"discount_type": wc_type_map.get(discount_type, "Percentage"),
		"pricing_rule": pricing_rule_name,
		"coupon_code": coupon_code_name,
	})
	settings.save(ignore_permissions=True)
	frappe.db.commit()
