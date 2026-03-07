// Copyright (c) 2026, Primetechbd and contributors
// For license information, please see license.txt

frappe.ui.form.on("WooCommerce Server", {
	refresh(frm) {
		if (!frm.doc.__islocal && frm.doc.enabled) {
			// Add sync buttons
			frm.add_custom_button(__("Sync Items"), () => {
				frm.call("run_sync_items").then(() => {
					frappe.show_alert({message: __("Item sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Customers"), () => {
				frm.call("run_sync_customers").then(() => {
					frappe.show_alert({message: __("Customer sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Orders"), () => {
				frm.call("run_sync_orders").then(() => {
					frappe.show_alert({message: __("Order sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Stock"), () => {
				frm.call("run_sync_stock").then(() => {
					frappe.show_alert({message: __("Stock sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Invoices"), () => {
				frm.call("run_sync_invoices").then(() => {
					frappe.show_alert({message: __("Invoice sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Payments"), () => {
				frm.call("run_sync_payments").then(() => {
					frappe.show_alert({message: __("Payment sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			frm.add_custom_button(__("Sync Coupons"), () => {
				frm.call("run_sync_coupons").then(() => {
					frappe.show_alert({message: __("Coupon sync queued"), indicator: "blue"});
				});
			}, __("Sync"));

			// View sync logs
			frm.add_custom_button(__("View Sync Logs"), () => {
				frappe.set_route("List", "WC Sync Log");
			});
		}
	}
});
