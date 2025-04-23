import frappe
from frappe import _
from optima.optima.utils.order_sync import enqueue_optima_order_sync

def on_submit(doc, method):
    """Handle Sales Order submission"""
    if not doc.custom_send_to_optima:  # Ensure this field is correctly set in your custom fields
        return
        
    try:
        # Queue the sync process with retry
        enqueue_optima_order_sync(doc.name)
        
        # Update initial status
        doc.db_set('custom_optima_sync_status', 'Pending')
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Optima Sync Error: {str(e)}", "Optima Sales Order Submit")
        doc.db_set('custom_optima_sync_status', 'Failed')
        doc.db_set('custom_optima_sync_error', str(e))
        frappe.db.commit()