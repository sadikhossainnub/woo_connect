frappe.ui.form.on("Delivery Parcel", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.consignment_id) {
            frm.add_custom_button(__("Check Status"), () => {
                frm.call("check_status").then((r) => {
                    if (r.message) {
                        frm.reload_doc();
                    }
                });
            });
        }
    },

    sales_invoice(frm) {
        if (frm.doc.sales_invoice) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Sales Invoice",
                    name: frm.doc.sales_invoice,
                },
                callback(r) {
                    if (r.message) {
                        let si = r.message;
                        frm.set_value("customer_name", si.customer_name || si.customer);
                        frm.set_value("cod_amount", si.grand_total);
                        frm.set_value("company", si.company);

                        // Try to get phone and address
                        if (si.contact_mobile) {
                            frm.set_value("customer_phone", si.contact_mobile);
                        }
                        if (si.customer_address) {
                            frappe.call({
                                method: "frappe.client.get",
                                args: {
                                    doctype: "Address",
                                    name: si.customer_address,
                                },
                                callback(addr_r) {
                                    if (addr_r.message) {
                                        let addr = addr_r.message;
                                        let full_addr = [
                                            addr.address_line1,
                                            addr.address_line2,
                                            addr.city,
                                            addr.state,
                                            addr.pincode,
                                        ].filter(Boolean).join(", ");
                                        frm.set_value("customer_address", full_addr);
                                        if (addr.phone) {
                                            frm.set_value("customer_phone", addr.phone);
                                        }
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }
    },

    cod_amount(frm) {
        frm.set_value("net_amount", (frm.doc.cod_amount || 0) - (frm.doc.delivery_charge || 0));
    },

    delivery_charge(frm) {
        frm.set_value("net_amount", (frm.doc.cod_amount || 0) - (frm.doc.delivery_charge || 0));
    },
});
