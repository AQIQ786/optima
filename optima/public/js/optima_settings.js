frappe.ui.form.on('Optima Settings', {
    refresh: function(frm) {
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'optima.optima.utils.connection.test_connection',
                callback: function(r) {
                    if (r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: r.message.message
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Failed'),
                            indicator: 'red',
                            message: r.message.message
                        });
                    }
                }
            });
        });

        frm.add_custom_button(__('Sync Items'), function() {
            frappe.call({
                method: 'optima.optima.utils.sync.sync_items',
                freeze: true,
                freeze_message: __('Syncing Items...'),
                callback: function(r) {
                    if (r.message.success) {
                        frappe.show_alert({
                            message: __('Items synced successfully'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.throw(r.message.message);
                    }
                }
            });
        }, __('Sync'));

        frm.add_custom_button(__('Sync Customers'), function() {
            frappe.call({
                method: 'optima.optima.utils.sync.sync_customers',
                freeze: true,
                freeze_message: __('Syncing Customers...'),
                callback: function(r) {
                    if (r.message.success) {
                        frappe.show_alert({
                            message: __('Customers synced successfully'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.throw(r.message.message);
                    }
                }
            });
        }, __('Sync'));
    }
}); 