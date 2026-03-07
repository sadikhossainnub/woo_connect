# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WCSyncLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		direction: DF.Literal["", "Push", "Pull"]
		erpnext_docname: DF.DynamicLink | None
		erpnext_doctype: DF.Link | None
		message: DF.SmallText | None
		request_data: DF.Code | None
		response_data: DF.Code | None
		status: DF.Literal["", "Success", "Failed", "Skipped"]
		sync_type: DF.Literal["", "Item", "Customer", "Order", "Invoice", "Payment", "Stock", "Coupon", "Loyalty"]
		wc_id: DF.Data | None
	# end: auto-generated types

	pass
