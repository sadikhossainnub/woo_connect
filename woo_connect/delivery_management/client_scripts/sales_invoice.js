frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        // Add "Create Delivery Parcel" button on submitted Sales Invoices
        if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__("Create Delivery Parcel"), () => {
                frappe.new_doc("Delivery Parcel", {
                    sales_invoice: frm.doc.name,
                    customer_name: frm.doc.customer_name || frm.doc.customer,
                    cod_amount: frm.doc.grand_total,
                    company: frm.doc.company,
                });
            }, __("Create"));
        }
    }
});
