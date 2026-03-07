frappe.ui.form.on("Delivery Service Provider", {
    refresh(frm) {
        if (!frm.is_new() && frm.doc.api_key) {
            frm.add_custom_button(__("Check Balance"), () => {
                frm.call("check_balance").then((r) => {
                    if (r.message !== undefined) {
                        frappe.show_alert({
                            message: __("Steadfast Balance: ৳") + r.message,
                            indicator: "green"
                        });
                    }
                });
            });
        }
    }
});
