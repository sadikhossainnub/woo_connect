# Copyright (c) 2026, Primetechbd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CODSettlement(Document):
	def validate(self):
		self._calculate_totals()

	def on_submit(self):
		self._create_journal_entry()
		self._create_payment_entries()
		self._update_parcel_status()

	def on_cancel(self):
		self._cancel_journal_entry()

	def _calculate_totals(self):
		"""Calculate totals from child table items."""
		self.total_cod_collected = 0
		self.total_delivery_charges = 0

		for item in self.items:
			item.net_amount = (item.cod_amount or 0) - (item.delivery_charge or 0)
			self.total_cod_collected += item.cod_amount or 0
			self.total_delivery_charges += item.delivery_charge or 0

		self.net_settlement_amount = self.total_cod_collected - self.total_delivery_charges

	def _create_journal_entry(self):
		"""Create Journal Entry for COD settlement.

		Debit: Settlement Bank Account (net amount received)
		Debit: Delivery Charge Expense Account (delivery charges)
		Credit: COD Receivable Account (total COD collected)
		"""
		provider = frappe.get_doc("Delivery Service Provider", self.delivery_provider)

		if not provider.settlement_payment_account:
			frappe.throw("Please set Settlement Payment Account in Delivery Service Provider")
		if not provider.delivery_charge_account:
			frappe.throw("Please set Delivery Charge Account in Delivery Service Provider")
		if not provider.cod_receivable_account:
			frappe.throw("Please set COD Receivable Account in Delivery Service Provider")

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.posting_date = self.settlement_date
		je.company = self.company
		je.user_remark = f"COD Settlement from {self.delivery_provider} | Ref: {self.reference_number or self.name}"
		je.cheque_no = self.reference_number or self.name
		je.cheque_date = self.settlement_date

		# Debit: Bank Account (net settlement amount)
		je.append("accounts", {
			"account": provider.settlement_payment_account,
			"debit_in_account_currency": self.net_settlement_amount,
			"credit_in_account_currency": 0,
		})

		# Debit: Delivery Charge Expense (total delivery charges)
		if self.total_delivery_charges > 0:
			je.append("accounts", {
				"account": provider.delivery_charge_account,
				"debit_in_account_currency": self.total_delivery_charges,
				"credit_in_account_currency": 0,
			})

		# Credit: COD Receivable (total COD collected)
		je.append("accounts", {
			"account": provider.cod_receivable_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": self.total_cod_collected,
		})

		je.flags.ignore_permissions = True
		je.save()
		je.submit()

		self.db_set("journal_entry", je.name)
		frappe.msgprint(
			f"Journal Entry <a href='/app/journal-entry/{je.name}'>{je.name}</a> created.",
			indicator="green",
			alert=True,
		)

	def _create_payment_entries(self):
		"""Create Payment Entries against each Sales Invoice to mark them as paid."""
		provider = frappe.get_doc("Delivery Service Provider", self.delivery_provider)

		for item in self.items:
			if not item.sales_invoice:
				continue

			# Check if invoice is submitted and has outstanding
			si = frappe.get_doc("Sales Invoice", item.sales_invoice)
			if si.docstatus != 1 or si.outstanding_amount <= 0:
				continue

			try:
				from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

				pe = get_payment_entry("Sales Invoice", item.sales_invoice)
				pe.paid_amount = item.cod_amount
				pe.received_amount = item.cod_amount
				pe.reference_no = self.reference_number or self.name
				pe.reference_date = self.settlement_date
				pe.mode_of_payment = "Cash"

				if provider.settlement_payment_account:
					pe.paid_to = provider.settlement_payment_account

				pe.flags.ignore_permissions = True
				pe.flags.ignore_mandatory = True
				pe.save()
				pe.submit()
			except Exception as e:
				frappe.log_error(
					title=f"COD Settlement PE Error: {item.sales_invoice}",
					message=frappe.get_traceback(),
				)

	def _update_parcel_status(self):
		"""Mark Delivery Parcels as settled."""
		for item in self.items:
			if item.delivery_parcel:
				frappe.db.set_value("Delivery Parcel", item.delivery_parcel, "delivery_status", "Delivered")

	def _cancel_journal_entry(self):
		"""Cancel linked Journal Entry on settlement cancellation."""
		if self.journal_entry:
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.cancel()
			self.db_set("journal_entry", "")
