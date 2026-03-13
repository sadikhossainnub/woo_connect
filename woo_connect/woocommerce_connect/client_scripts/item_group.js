frappe.ui.form.on('Item Group', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Publish to WooCommerce'), function() {
				frappe.call({
					method: 'woo_connect.woocommerce_connect.sync.item_sync.push_item_group_to_woocommerce',
					args: {
						item_group_name: frm.doc.name
					},
					callback: function(r) {
						if (r.message && r.message.status === 'Success') {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			}, __('WooCommerce'));
		}
	}
});
