# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

"""Webhook endpoint for receiving WooCommerce events."""

import hashlib
import hmac
import json

import frappe


@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_webhook():
	"""Handle incoming WooCommerce webhook payloads.

	Verifies the HMAC-SHA256 signature, then dispatches to the appropriate
	sync handler based on the webhook topic.
	"""
	# Bypass CSRF validation — WooCommerce cannot provide a CSRF token
	frappe.flags.ignore_csrf = True

	settings = frappe.get_single("WooCommerce Server")
	if not settings.enabled:
		frappe.throw("WooCommerce integration is disabled", frappe.AuthenticationError)

	# Verify signature
	signature = frappe.request.headers.get("X-WC-Webhook-Signature", "")
	payload = frappe.request.get_data()

	if not _verify_signature(payload, signature, settings.webhook_secret):
		frappe.throw("Invalid webhook signature", frappe.AuthenticationError)

	# Get webhook topic
	topic = frappe.request.headers.get("X-WC-Webhook-Topic", "")
	data = json.loads(payload)

	# Handle webhook based on topic
	if topic.startswith("order."):
		_handle_order_webhook(topic, data, settings)
	elif topic.startswith("product."):
		_handle_product_webhook(topic, data, settings)
	elif topic.startswith("customer."):
		_handle_customer_webhook(topic, data, settings)
	elif topic.startswith("coupon."):
		_handle_coupon_webhook(topic, data, settings)

	return {"status": "ok"}


def _verify_signature(payload, signature, secret):
	"""Verify the WooCommerce webhook HMAC-SHA256 signature."""
	if not secret or not signature:
		return False

	import base64

	computed = hmac.HMAC(
		secret.encode("utf-8"),
		payload,
		hashlib.sha256,
	).digest()

	computed_b64 = base64.b64encode(computed).decode("utf-8")

	return hmac.compare_digest(computed_b64, signature)


def _handle_order_webhook(topic, data, settings):
	"""Handle order webhook events."""
	from woo_connect.woocommerce_connect.sync.order_sync import sync_orders_from_woocommerce

	frappe.enqueue(sync_orders_from_woocommerce, queue="long", timeout=600)


def _handle_product_webhook(topic, data, settings):
	"""Handle product webhook events."""
	from woo_connect.woocommerce_connect.sync.item_sync import sync_items_from_woocommerce

	frappe.enqueue(sync_items_from_woocommerce, queue="long", timeout=600)


def _handle_customer_webhook(topic, data, settings):
	"""Handle customer webhook events."""
	from woo_connect.woocommerce_connect.sync.customer_sync import sync_customers_from_woocommerce

	frappe.enqueue(sync_customers_from_woocommerce, queue="long", timeout=600)


def _handle_coupon_webhook(topic, data, settings):
	"""Handle coupon webhook events."""
	from woo_connect.woocommerce_connect.sync.discount_sync import sync_coupons_from_woocommerce

	frappe.enqueue(sync_coupons_from_woocommerce, queue="long", timeout=600)
