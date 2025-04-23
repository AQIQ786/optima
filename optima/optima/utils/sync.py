import frappe
from frappe import _
from datetime import datetime
from .connection import get_optima_connection
from .mapping import fetch_optima_items, fetch_optima_customers

def create_sync_log(sync_type, status, message=None):
    """Create a sync log entry."""
    log = frappe.get_doc({
        "doctype": "Optima Sync Log",
        "sync_type": sync_type,
        "status": status,
        "message": message or "Sync completed successfully",
        "sync_datetime": datetime.now()
    })
    log.insert(ignore_permissions=True)
    return log

@frappe.whitelist()
def sync_items():
    """Sync items from Optima to ERPNext."""
    try:
        items = fetch_optima_items()
        
        for item in items:
            # Check if mapping exists
            existing_mapping = frappe.get_all(
                "Optima Item Mapping",
                filters={"optima_item_code": item.ItemCode},
                fields=["name", "erpnext_item_code"]
            )
            
            if not existing_mapping:
                # Create new item in ERPNext if needed
                erpnext_item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": item.ItemCode,
                    "item_name": item.Description,
                    "standard_rate": item.UnitPrice,
                    "item_group": "Products"  # Set appropriate default
                })
                erpnext_item.insert(ignore_permissions=True)
                
                # Create mapping
                mapping = frappe.get_doc({
                    "doctype": "Optima Item Mapping",
                    "optima_item_code": item.ItemCode,
                    "erpnext_item_code": item.ItemCode
                })
                mapping.insert(ignore_permissions=True)
        
        create_sync_log("Items", "Success")
        return {"success": True, "message": "Items synced successfully"}
    
    except Exception as e:
        error_msg = f"Error syncing items: {str(e)}"
        create_sync_log("Items", "Failed", error_msg)
        return {"success": False, "message": error_msg}

@frappe.whitelist()
def sync_customers():
    """Sync customers from Optima to ERPNext."""
    try:
        customers = fetch_optima_customers()
        
        for customer in customers:
            # Check if mapping exists
            existing_mapping = frappe.get_all(
                "Optima Customer Mapping",
                filters={"optima_customer_code": customer.CustomerCode},
                fields=["name", "erpnext_customer"]
            )
            
            if not existing_mapping:
                # Create new customer in ERPNext if needed
                erpnext_customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": customer.CustomerName,
                    "customer_type": "Company",
                    "territory": "All Territories"
                })
                erpnext_customer.insert(ignore_permissions=True)
                
                # Create mapping
                mapping = frappe.get_doc({
                    "doctype": "Optima Customer Mapping",
                    "optima_customer_code": customer.CustomerCode,
                    "erpnext_customer": erpnext_customer.name
                })
                mapping.insert(ignore_permissions=True)
        
        create_sync_log("Customers", "Success")
        return {"success": True, "message": "Customers synced successfully"}
    
    except Exception as e:
        error_msg = f"Error syncing customers: {str(e)}"
        create_sync_log("Customers", "Failed", error_msg)
        return {"success": False, "message": error_msg}

def daily_sync():
    """Daily sync operation."""
    sync_items()
    sync_customers()
    # Update last sync datetime in settings
    settings = frappe.get_single("Optima Settings")
    settings.last_sync_datetime = datetime.now()
    settings.save()

def hourly_sync():
    """Hourly sync operation for time-sensitive data."""
    # Add any hourly sync operations here
    pass 

def check_optima_sync_status():
    """Check status of synced orders in Optima"""
    conn = get_optima_connection()
    cursor = conn.cursor()
    
    try:
        # Get pending orders
        orders = frappe.get_all(
            "Optima Order",
            filters={"sync_status": "In Progress"},
            fields=["name", "optima_operation_id"]
        )
        
        for order in orders:
            # Check status in Optima
            cursor.execute("""
                SELECT SyncStatus, SyncNotes 
                FROM Optima_Orders 
                WHERE ID_OPERATIONS = %s
            """, (order.optima_operation_id,))
            
            result = cursor.fetchone()
            if result:
                status, notes = result
                
                optima_order = frappe.get_doc("Optima Order", order.name)
                if status == 1:
                    optima_order.sync_status = "Completed"
                    optima_order.status = "Synced"
                elif status < 0:
                    optima_order.sync_status = "Failed"
                    optima_order.status = "Failed"
                    optima_order.sync_message = notes
                
                optima_order.save()
                
    finally:
        cursor.close()
        conn.close()