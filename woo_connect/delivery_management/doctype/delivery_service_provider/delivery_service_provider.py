# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeliveryServiceProvider(Document):
	def validate(self):
		if self.is_new():
			self._auto_create_accounts()

	def _auto_create_accounts(self):
		"""Auto-create delivery-related accounts in Chart of Accounts if they don't exist."""
		if not self.company:
			return

		accounts_to_create = [
			{
				"account_name": "COD Receivable",
				"parent_account_group": "Current Assets",
				"account_type": "Receivable",
				"field": "cod_receivable_account",
			},
			{
				"account_name": "Delivery Charges",
				"parent_account_group": "Indirect Expenses",
				"account_type": "Expense Account",
				"field": "delivery_charge_account",
			},
			{
				"account_name": "COD Settlement",
				"parent_account_group": "Bank Accounts",
				"account_type": "Bank",
				"field": "settlement_payment_account",
			},
		]

		company_abbr = frappe.get_cached_value("Company", self.company, "abbr")

		for acc_info in accounts_to_create:
			account_name = f"{acc_info['account_name']} - {company_abbr}"

			if frappe.db.exists("Account", account_name):
				# Account exists, just set the field
				self.set(acc_info["field"], account_name)
				continue

			# Find parent account
			parent_account = frappe.db.get_value(
				"Account",
				{
					"account_name": acc_info["parent_account_group"],
					"company": self.company,
					"is_group": 1,
				},
				"name",
			)

			if not parent_account:
				frappe.msgprint(
					f"Could not find parent account '{acc_info['parent_account_group']}' for company {self.company}. "
					f"Please set '{acc_info['account_name']}' account manually.",
					indicator="orange",
					alert=True,
				)
				continue

			try:
				account = frappe.new_doc("Account")
				account.account_name = acc_info["account_name"]
				account.parent_account = parent_account
				account.account_type = acc_info["account_type"]
				account.company = self.company
				account.is_group = 0
				account.flags.ignore_permissions = True
				account.insert()

				self.set(acc_info["field"], account.name)
				frappe.msgprint(
					f"Created account: {account.name}",
					indicator="green",
					alert=True,
				)
			except Exception as e:
				frappe.msgprint(
					f"Could not create account '{acc_info['account_name']}': {e!s}",
					indicator="red",
					alert=True,
				)

	@frappe.whitelist()
	def check_balance(self):
		"""Check Steadfast account balance."""
		from woo_connect.delivery_management.utils.steadfast_api import get_balance

		balance = get_balance(self)
		frappe.msgprint(
			f"Steadfast Balance: ৳{balance}",
			indicator="green",
			alert=True,
		)
		return balance
