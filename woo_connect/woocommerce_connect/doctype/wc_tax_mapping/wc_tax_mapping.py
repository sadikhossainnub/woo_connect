# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WCTaxMapping(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		tax_template: DF.Link
		wc_tax_class: DF.Data
	# end: auto-generated types

	pass
