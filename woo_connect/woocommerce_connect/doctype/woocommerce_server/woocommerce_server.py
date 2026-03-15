# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document


class WooCommerceServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from woo_connect.woocommerce_connect.doctype.wc_coupon_mapping.wc_coupon_mapping import WCCouponMapping
		from woo_connect.woocommerce_connect.doctype.wc_payment_method_mapping.wc_payment_method_mapping import (
			WCPaymentMethodMapping,
		)
		from woo_connect.woocommerce_connect.doctype.wc_tax_mapping.wc_tax_mapping import WCTaxMapping
		from woo_connect.woocommerce_connect.doctype.wc_warehouse_mapping.wc_warehouse_mapping import (
			WCWarehouseMapping,
		)
		from woo_connect.woocommerce_connect.doctype.wc_category_mapping.wc_category_mapping import (
			WCCategoryMapping,
		)

		api_key: DF.Data
		api_secret: DF.Password
		category_mappings: DF.Table[WCCategoryMapping]
		company: DF.Link
		cost_center: DF.Link | None
		coupon_mappings: DF.Table[WCCouponMapping]
		default_discount_account: DF.Link | None
		default_item_group: DF.Link | None
		default_price_list: DF.Link | None
		default_uom: DF.Link | None
		default_warehouse: DF.Link
		enable_loyalty_points: DF.Check
		enabled: DF.Check
		freight_account: DF.Link | None
		loyalty_program: DF.Link | None
		payment_method_mappings: DF.Table[WCPaymentMethodMapping]
		sync_categories: DF.Check
		sync_coupons: DF.Check
		sync_customers: DF.Check
		sync_invoices: DF.Check
		sync_items: DF.Check
		sync_orders: DF.Check
		sync_payments: DF.Check
		sync_stock: DF.Check
		tax_account: DF.Link | None
		tax_mappings: DF.Table[WCTaxMapping]
		verify_ssl: DF.Check
		warehouse_mappings: DF.Table[WCWarehouseMapping]
		webhook_secret: DF.Data | None
		woocommerce_url: DF.Data
	# end: auto-generated types

	def validate(self):
		self.woocommerce_url = self.woocommerce_url.rstrip("/")

		if not self.webhook_secret:
			self.webhook_secret = secrets.token_hex(20)

		if self.enabled:
			self.test_connection()

	def test_connection(self):
		"""Test connection to WooCommerce store."""
		from woo_connect.woocommerce_connect.utils.api_client import get_wc_api

		try:
			api = get_wc_api(self)
			response = api.get("system_status")
			if response.status_code != 200:
				frappe.throw(
					f"WooCommerce connection failed: {response.status_code} - {response.text}"
				)
			frappe.msgprint("WooCommerce connection successful!", indicator="green", alert=True)
		except Exception as e:
			frappe.throw(f"Failed to connect to WooCommerce: {e!s}")

	@frappe.whitelist()
	def run_sync_items(self):
		"""Manually trigger item sync."""
		from woo_connect.woocommerce_connect.sync.item_sync import (
			sync_items_from_woocommerce,
			sync_items_to_woocommerce,
		)

		frappe.enqueue(sync_items_from_woocommerce, queue="long", timeout=1500)
		frappe.enqueue(sync_items_to_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Item sync (Pull & Push) has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_customers(self):
		"""Manually trigger customer sync."""
		from woo_connect.woocommerce_connect.sync.customer_sync import sync_customers_from_woocommerce

		frappe.enqueue(sync_customers_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Customer sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_orders(self):
		"""Manually trigger order sync."""
		from woo_connect.woocommerce_connect.sync.order_sync import sync_orders_from_woocommerce

		frappe.enqueue(sync_orders_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Order sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_stock(self):
		"""Manually trigger stock sync."""
		from woo_connect.woocommerce_connect.sync.stock_sync import sync_stock_to_woocommerce

		frappe.enqueue(sync_stock_to_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Stock sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_invoices(self):
		"""Manually trigger invoice sync."""
		from woo_connect.woocommerce_connect.sync.invoice_sync import sync_invoices_from_woocommerce

		frappe.enqueue(sync_invoices_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Invoice sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_payments(self):
		"""Manually trigger payment sync."""
		from woo_connect.woocommerce_connect.sync.payment_sync import sync_payments_from_woocommerce

		frappe.enqueue(sync_payments_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Payment sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_coupons(self):
		"""Manually trigger coupon sync."""
		from woo_connect.woocommerce_connect.sync.discount_sync import sync_coupons_from_woocommerce

		frappe.enqueue(sync_coupons_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Coupon sync has been queued.", indicator="blue", alert=True)

	@frappe.whitelist()
	def run_sync_categories(self):
		"""Manually trigger category sync."""
		from woo_connect.woocommerce_connect.sync.item_sync import sync_categories_from_woocommerce

		frappe.enqueue(sync_categories_from_woocommerce, queue="long", timeout=1500)
		frappe.msgprint("Category sync has been queued.", indicator="blue", alert=True)
