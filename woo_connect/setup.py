import frappe

def after_install():
	create_cod_account_and_mop()

def create_cod_account_and_mop():
	mop_name = "COD"
	if not frappe.db.exists("Mode of Payment", mop_name):
		mop = frappe.new_doc("Mode of Payment")
		mop.mode_of_payment = mop_name
		mop.enabled = 1
		mop.type = "Cash"
		mop.insert(ignore_permissions=True)
	else:
		mop = frappe.get_doc("Mode of Payment", mop_name)

	companies = frappe.get_all("Company", fields=["name", "abbr", "default_currency"])
	
	mop_updated = False
	for company in companies:
		account_name = f"COD - {company.abbr}"
		
		if not frappe.db.exists("Account", account_name):
			# Priority 1: Cash In Hand group
			parent_account = frappe.db.get_value("Account", {"account_type": "Cash", "is_group": 1, "company": company.name})
			
			# Priority 2: Any Asset group
			if not parent_account:
				parent_account = frappe.db.get_value("Account", {"root_type": "Asset", "is_group": 1, "company": company.name})

			if parent_account:
				try:
					account = frappe.new_doc("Account")
					account.account_name = "COD"
					account.parent_account = parent_account
					account.company = company.name
					account.root_type = "Asset"
					account.report_type = "Balance Sheet"
					account.account_currency = company.default_currency
					account.account_type = "Cash"
					account.insert(ignore_permissions=True)
				except Exception:
					continue
			else:
				continue

		# Link Account to Mode of Payment
		if not any(d.company == company.name for d in mop.accounts):
			mop.append("accounts", {
				"company": company.name,
				"default_account": account_name
			})
			mop_updated = True

	if mop_updated:
		mop.save(ignore_permissions=True)

	frappe.db.commit()
