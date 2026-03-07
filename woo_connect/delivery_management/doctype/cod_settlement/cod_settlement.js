frappe.ui.form.on("COD Settlement", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Get Delivered Parcels"), () => {
                if (!frm.doc.delivery_provider || !frm.doc.period_from || !frm.doc.period_to) {
                    frappe.msgprint(__("Please set Delivery Provider, Period From and Period To first."));
                    return;
                }

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Delivery Parcel",
                        filters: {
                            delivery_provider: frm.doc.delivery_provider,
                            posting_date: ["between", [frm.doc.period_from, frm.doc.period_to]],
                            docstatus: 1,
                            delivery_status: ["in", ["Delivered", "In Transit"]],
                        },
                        fields: ["name", "sales_invoice", "customer_name", "cod_amount", "delivery_charge"],
                        limit_page_length: 0,
                    },
                    callback(r) {
                        if (r.message && r.message.length > 0) {
                            frm.clear_table("items");
                            r.message.forEach((parcel) => {
                                let row = frm.add_child("items");
                                row.delivery_parcel = parcel.name;
                                row.sales_invoice = parcel.sales_invoice;
                                row.customer = parcel.customer_name;
                                row.cod_amount = parcel.cod_amount;
                                row.delivery_charge = parcel.delivery_charge;
                                row.net_amount = (parcel.cod_amount || 0) - (parcel.delivery_charge || 0);
                            });
                            frm.refresh_field("items");
                            frm.trigger("calculate_totals");
                            frappe.show_alert({
                                message: __("{0} parcels added", [r.message.length]),
                                indicator: "green"
                            });
                        } else {
                            frappe.show_alert({
                                message: __("No delivered parcels found for this period"),
                                indicator: "orange"
                            });
                        }
                    }
                });
            }, __("Get"));
        }
    },

    calculate_totals(frm) {
        let total_cod = 0;
        let total_charges = 0;
        (frm.doc.items || []).forEach((item) => {
            item.net_amount = (item.cod_amount || 0) - (item.delivery_charge || 0);
            total_cod += item.cod_amount || 0;
            total_charges += item.delivery_charge || 0;
        });
        frm.set_value("total_cod_collected", total_cod);
        frm.set_value("total_delivery_charges", total_charges);
        frm.set_value("net_settlement_amount", total_cod - total_charges);
    },
});

frappe.ui.form.on("COD Settlement Item", {
    cod_amount(frm) {
        frm.trigger("calculate_totals");
    },
    delivery_charge(frm) {
        frm.trigger("calculate_totals");
    },
    items_remove(frm) {
        frm.trigger("calculate_totals");
    },
});
