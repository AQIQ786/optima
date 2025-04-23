// Copyright (c) 2024, Ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Order", {
	refresh(frm) {
        if (frm.doc.status == "Pending"){

            frm.add_custom_button(
                __("Sales Order"),
                function () {
                    erpnext.utils.map_current_doc({
                        method: "optima.optima.doctype.optima_order.optima_order.make_optima_order",
                        source_doctype: "Sales Order",
                        target: frm,
                        setters: [
                            {
                                label: "Customer",
                                fieldname: "customer",
                                fieldtype: "Link",
                                options: "Customer",
                            },
                        ],
                        get_query_filters: {
                            docstatus: 1,
                            company: frm.doc.company,
                        },
                    });
                },
                __("Get Items From"),
                "btn-default"
            );
            if (!frm.is_new() && !frm.is_dirty() && frm.doc.items){
                frm.add_custom_button(
                    __("Send to Optima Database"),
                    () => {
                        frappe.confirm('Are you sure you want to send the order to Optima?',
                            () => {
                                frappe.call({
                                    method: "optima.optima.doctype.optima_order.optima_order.send_to_optima",
                                    args: {
                                        "order": frm.doc.name
                                    },
                                    callback: function(r){
                                        if (r.message){
                                            frappe.msgprint(r.message.message)
                                        }
                                    }
                                })
                            })
                    }
                )
            }
            
        }
	},
});
