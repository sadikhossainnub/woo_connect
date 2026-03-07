# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeliveryParcel(Document):
	def validate(self):
		self.net_amount = (self.cod_amount or 0) - (self.delivery_charge or 0)

		# Auto-fill delivery charge from provider default
		if not self.delivery_charge and self.delivery_provider:
			default_charge = frappe.db.get_value(
				"Delivery Service Provider", self.delivery_provider, "default_delivery_charge"
			)
			if default_charge:
				self.delivery_charge = default_charge
				self.net_amount = (self.cod_amount or 0) - self.delivery_charge

	def on_submit(self):
		"""Book parcel via Steadfast API on submit."""
		self._book_with_steadfast()
		self._update_sales_invoice()

	def on_cancel(self):
		"""Update Sales Invoice on cancel."""
		if self.sales_invoice:
			frappe.db.set_value("Sales Invoice", self.sales_invoice, {
				"custom_tracking_number": "",
				"custom_delivery_status": "",
			})

	def _book_with_steadfast(self):
		"""Send parcel to Steadfast Courier via API."""
		provider = frappe.get_doc("Delivery Service Provider", self.delivery_provider)
		if not provider.api_key or not provider.api_secret:
			frappe.msgprint("Steadfast API credentials not configured. Parcel saved without booking.", indicator="orange")
			return

		try:
			from woo_connect.delivery_management.utils.steadfast_api import create_parcel

			result = create_parcel(provider, {
				"invoice": self.name,
				"recipient_name": self.customer_name,
				"recipient_phone": self.customer_phone,
				"recipient_address": self.customer_address,
				"cod_amount": self.cod_amount,
				"note": self.note or "",
				"weight": self.weight or 1,
			})

			if result and result.get("consignment"):
				consignment = result["consignment"]
				self.db_set("consignment_id", str(consignment.get("consignment_id", "")))
				self.db_set("tracking_code", str(consignment.get("tracking_code", "")))
				self.db_set("delivery_status", "In Transit")

				frappe.msgprint(
					f"Parcel booked with Steadfast! Tracking: {consignment.get('tracking_code', 'N/A')}",
					indicator="green",
					alert=True,
				)
			else:
				frappe.msgprint(
					f"Steadfast API response: {result}",
					indicator="orange",
					alert=True,
				)
		except Exception as e:
			frappe.msgprint(
				f"Could not book with Steadfast: {e!s}. Parcel saved locally.",
				indicator="orange",
				alert=True,
			)
			frappe.log_error(
				title=f"Steadfast Booking Error: {self.name}",
				message=frappe.get_traceback(),
			)

	def _update_sales_invoice(self):
		"""Update tracking info on linked Sales Invoice."""
		if not self.sales_invoice:
			return

		frappe.db.set_value("Sales Invoice", self.sales_invoice, {
			"custom_delivery_provider": self.delivery_provider,
			"custom_tracking_number": self.consignment_id or self.tracking_code or "",
			"custom_delivery_status": self.delivery_status,
		})

	@frappe.whitelist()
	def check_status(self):
		"""Check delivery status from Steadfast API."""
		if not self.consignment_id:
			frappe.throw("No Consignment ID to track")

		provider = frappe.get_doc("Delivery Service Provider", self.delivery_provider)
		from woo_connect.delivery_management.utils.steadfast_api import get_delivery_status

		result = get_delivery_status(provider, self.consignment_id)

		if result and result.get("delivery_status"):
			status_map = {
				"in_transit": "In Transit",
				"delivered": "Delivered",
				"partial_delivered": "Partial",
				"cancelled": "Cancelled",
				"hold": "Pending",
				"pending": "Pending",
			}
			new_status = status_map.get(result["delivery_status"].lower(), self.delivery_status)
			self.db_set("delivery_status", new_status)
			self._update_sales_invoice()

			frappe.msgprint(
				f"Status: {new_status}",
				indicator="green" if new_status == "Delivered" else "blue",
				alert=True,
			)
			return new_status

		return self.delivery_status
