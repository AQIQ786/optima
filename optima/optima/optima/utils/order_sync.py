import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue
from .connection import get_optima_connection
import random
from datetime import datetime, timedelta

@frappe.whitelist()
def enqueue_optima_order_sync(sales_order):
    """Enqueue the Optima order sync process."""
    enqueue(
        method="optima.optima.utils.order_sync.sync_sales_order_to_optima_by_name",
        queue="long",
        timeout=300,
        job_name=f"sync_optima_order_{sales_order}",
        sales_order=sales_order
    )
    
    frappe.msgprint(
        msg=_('Order sync has been queued and will be sent to Optima in the background.'),
        title=_('Order Sync Queued'),
        indicator='blue'
    )

def sync_sales_order_to_optima_by_name(sales_order):
    """Wrapper function to sync sales order by name."""
    doc = frappe.get_doc("Sales Order", sales_order)
    return sync_sales_order_to_optima(doc)

def prepare_order_header(doc, shipping_details):
    """Prepare order header data matching Optima_Orders schema."""
    return {
        "CLIENTE": 44934,  # Assuming a default customer ID; replace with actual logic if available
        "NAZIONI_CODICE": None,
        "RIF": doc.name[:12],  # Truncate to 12 characters to match SQL type
        "RIFCLI": doc.po_no or '',
        "DATAORD": doc.transaction_date,
        "DATACONS": doc.delivery_date,
        "DATAINIZIO": doc.transaction_date,
        "DATAFINE": doc.delivery_date,
        "DEF": 'Y',  # Confirmed order
        "NOTES": "Test",  # Default value, can be customized
        "DESCR1_SPED": shipping_details.get("address_line1", "")[:40],
        "DESCR2_SPED": doc.customer_name[:40],
        "INDIRI_SPED": shipping_details.get("address_line1", "")[:64],
        "CAP_SPED": (shipping_details.get("pincode") or "")[:30],
        "LOCALITA_SPED": (shipping_details.get("city") or "")[:30],
        "PROV_SPED": (shipping_details.get("state") or "")[:30],
        "COMMESSA_CLI": doc.name[:50],
        "RIFINTERNO": doc.name[:50],
        "RIFAGENTE": frappe.session.user[:50],
        "DESCR_TIPICAUDOC": 'Sales Order'
    }

def prepare_order_line(idx, item, order_id):
    """Prepare order line data matching Optima_OrderLines schema."""
    return {
        "ID_ORDINI": order_id,
        "RIGA": idx,
        "QTAPZ": item.qty,
        "DESCR_MAT_COMP": item.description[:512] if item.description else item.item_name[:512],
        "COD_ART_CLIENTE": item.item_code[:512],
        "DESCMAT": item.description[:1024] if item.description else item.item_name[:1024],
        "SAGOMA": 'RECT',  # Default rectangle shape
        "CODICE_ANAGRAFICA": item.item_code[:32],
        "CATEGORIE": item.item_group[:255] if item.item_group else '',
        "DIMXPZ": item.get('width', 20),
        "DIMYPZ": item.get('height', 50),
        "ID_UM": 0,  # 0=mm
        "PRODOTTI_CODICE": item.item_code[:32],
        "isrect": 1  # 1=Rectangle, 0=Shaped
    }

def get_next_order_id(cursor):
    """Get the next available order ID from OPTIMA_Orders."""
    try:
        cursor.execute("SELECT ISNULL(MAX(ID_ORDINI), 1000) + 1 FROM CONNECTOR_ORDERS.dbo.OPTIMA_Orders")
        next_id = cursor.fetchone()[0]
        return next_id
    except Exception as e:
        frappe.log_error(f"Error generating order ID: {str(e)}")
        raise

def create_optima_order(doc, order_id, header, shipping_details):
    """Create or update Optima Order document."""
    # Check if Optima Order already exists
    optima_order = frappe.get_all(
        "Optima Order", 
        filters={"sales_order": doc.name}, 
        limit=1
    )
    
    order_data = {
        "sales_order": doc.name,
        "customer": doc.customer,
        "customer_reference": doc.po_no or "",
        "order_date": header["DATAORD"],
        "delivery_date": header["DATACONS"],
        "status": "Pending",
        "sync_status": "In Progress",
        "delivery_address": shipping_details.get("address_line1", ""),
        "delivery_city": shipping_details.get("city", ""),
        "delivery_country": shipping_details.get("country", ""),
        "optima_order_id": order_id,
        "internal_reference": doc.name,
        "agent_reference": frappe.session.user,
        "notes": header.get("NOTES", "")
    }

    if optima_order:
        # Update existing order
        existing_order = frappe.get_doc("Optima Order", optima_order[0].name)
        existing_order.update(order_data)
        existing_order.sync_status = "Completed"
        existing_order.save()
        return existing_order
    else:
        # Create new order
        order_data.update({
            "doctype": "Optima Order",
            "items": []
        })
        
        # Add items
        for item in doc.items:
            order_data["items"].append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "description": item.description or item.item_name,
                "optima_sync_status": "Pending"
            })
        
        new_order = frappe.get_doc(order_data)
        new_order.insert(ignore_permissions=True)
        return new_order

def create_sync_log(doc, operation_id, status, message=None):
    """Create Optima Sync Log entry."""
    log_data = {
        "doctype": "Optima Sync Log",
        "reference_doctype": doc.doctype,
        "reference_name": doc.name,
        "operation_id": operation_id,
        "user": frappe.session.user,
        "status": status,
        "message": message if message else ""
    }
    
    log = frappe.get_doc(log_data)
    log.insert(ignore_permissions=True)
    return log

def sync_sales_order_to_optima(doc):
    """Sync Sales Order to Optima."""
    sync_log = None
    
    with get_optima_connection() as conn:
        try:
            cursor = conn.cursor()
            
            # Create sync log
            sync_log = create_sync_log(doc, None, "Pending")
            
            # Get shipping details with default values
            shipping_address = frappe.get_doc("Address", doc.shipping_address_name) if doc.shipping_address_name else None
            shipping_details = {
                "address_line1": (shipping_address.address_line1 if shipping_address else "") or "",
                "city": (shipping_address.city if shipping_address else "") or "",
                "pincode": (shipping_address.pincode if shipping_address else "") or "",
                "state": (shipping_address.state if shipping_address else "") or "",
                "country": (shipping_address.country if shipping_address else "") or ""
            }

            # Generate order reference (12 chars max)
            order_ref = f"S{datetime.now().strftime('%y%m%d%H%M')}"  # e.g. S2411141023
            
            # Insert into OPTIMA_Orders
            cursor.execute("""
                INSERT INTO OPTIMA_Orders (
                    CLIENTE, RIFCLI, DATAORD, DATACONS, DEF, NOTES, ID_ORDINI,
                    DESCR_TIPICAUDOC, DESCR1_SPED, DESCR2_SPED, INDIRI_SPED,
                    CAP_SPED, LOCALITA_SPED, PROV_SPED
                ) VALUES (
                    1, %s, %s, %s, 'Y', %s, 1,
                    'SALES', %s, %s, %s,
                    %s, %s, %s
                )
            """, (
                order_ref,  # RIFCLI
                doc.transaction_date,  # DATAORD
                doc.delivery_date or (doc.transaction_date + timedelta(days=7)),  # DATACONS
                doc.name[:64],  # NOTES
                shipping_details["address_line1"][:40] or "",  # DESCR1_SPED
                doc.customer_name[:40] or "",  # DESCR2_SPED
                shipping_details["address_line1"][:64] or "",  # INDIRI_SPED
                shipping_details["pincode"][:30] or "",  # CAP_SPED
                shipping_details["city"][:30] or "",  # LOCALITA_SPED
                shipping_details["state"][:30] or ""  # PROV_SPED
            ))
            
            # Get the ID of inserted order
            cursor.execute("SELECT @@IDENTITY")
            order_id = cursor.fetchone()[0]
            
            # Insert order lines into OPTIMA_OrderLines
            for idx, item in enumerate(doc.items, 1):
                cursor.execute("""
                    INSERT INTO OPTIMA_OrderLines (
                        ID_ORDINI, RIGA, QTAPZ, DESCR_MAT_COMP,
                        COD_ART_CLIENTE, DESCMAT, SAGOMA, CODICE_ANAGRAFICA,
                        DIMXPZ, DIMYPZ, ID_UM, isrect, PRODOTTI_CODICE
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, 'RECT', %s,
                        %s, %s, 0, 1, %s
                    )
                """, (
                    order_id,  # ID_ORDINI
                    idx,  # RIGA
                    int(item.qty),  # QTAPZ
                    item.description[:512] or item.item_name[:512],  # DESCR_MAT_COMP
                    item.item_code[:512],  # COD_ART_CLIENTE
                    item.description[:1024] or item.item_name[:1024],  # DESCMAT
                    item.item_code[:32],  # CODICE_ANAGRAFICA
                    float(item.get('width', 1000)),  # DIMXPZ
                    float(item.get('height', 2000)),  # DIMYPZ
                    item.item_code[:32]  # PRODOTTI_CODICE
                ))
            
            # Commit transaction
            conn.commit()

            # Create or update Optima Order
            optima_order = frappe.get_all(
                "Optima Order",
                filters={"sales_order": doc.name},
                limit=1
            )

            order_data = {
                "sales_order": doc.name,
                "customer": doc.customer,
                "customer_reference": doc.po_no or "",
                "order_date": doc.transaction_date,
                "delivery_date": doc.delivery_date,
                "status": "Completed",
                "sync_status": "Completed",
                "sync_message": f"Order synced successfully. Optima Order ID: {order_id}",
                "order_number": order_ref,
                "internal_reference": doc.name,
                "agent_reference": frappe.session.user,
                "notes": doc.name[:64],
                "delivery_description_1": shipping_details["address_line1"][:40] or "",
                "delivery_description_2": doc.customer_name[:40] or "",
                "delivery_address": shipping_details["address_line1"] or "",
                "delivery_zip": shipping_details["pincode"] or "",
                "delivery_city": shipping_details["city"] or "",
                "delivery_country": shipping_details["country"] or "",
                "optima_order_id": str(order_id),
                "optima_operation_id": str(order_id),
                "optima_sync_details": frappe.as_json({
                    "order_id": order_id,
                    "order_ref": order_ref,
                    "sync_time": str(datetime.now())
                })
            }

            if optima_order:
                existing_order = frappe.get_doc("Optima Order", optima_order[0].name)
                # Clear existing items
                existing_order.items = []
                # Add updated items
                for item in doc.items:
                    existing_order.append("items", {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "description": item.description or item.item_name,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount,
                        "optima_sync_status": "Synced"
                    })
                existing_order.update(order_data)
                existing_order.save()
            else:
                new_order = frappe.get_doc({
                    "doctype": "Optima Order",
                    **order_data,
                    "items": [{
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "description": item.description or item.item_name,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount,
                        "optima_sync_status": "Synced"
                    } for item in doc.items]
                })
                new_order.insert()

            # Update sync log
            if sync_log:
                sync_log.status = "Completed"
                sync_log.operation_id = order_id
                sync_log.save()

            # Update ERPNext status
            frappe.db.set_value('Sales Order', doc.name, {
                'custom_optima_sync_status': 'Completed',
                'custom_optima_order': order_id
            })
            frappe.db.commit()

            return {"success": True, "order_id": order_id}

        except Exception as e:
            if conn:
                conn.rollback()
            
            if sync_log:
                sync_log.status = "Failed"
                sync_log.message = str(e)[:140]
                sync_log.save()
            
            # Create/Update Optima Order with error status
            optima_order = frappe.get_all(
                "Optima Order",
                filters={"sales_order": doc.name},
                limit=1
            )

            error_data = {
                "sales_order": doc.name,
                "customer": doc.customer,
                "status": "Failed",
                "sync_status": "Failed",
                "sync_message": str(e)[:140],
                "items": [{
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "description": item.description or item.item_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "optima_sync_status": "Failed"
                } for item in doc.items]
            }

            if optima_order:
                existing_order = frappe.get_doc("Optima Order", optima_order[0].name)
                existing_order.items = []
                for item_data in error_data["items"]:
                    existing_order.append("items", item_data)
                existing_order.update(error_data)
                existing_order.save()
            else:
                new_order = frappe.get_doc({
                    "doctype": "Optima Order",
                    **error_data
                })
                new_order.insert()
            
            frappe.db.set_value('Sales Order', doc.name, {
                'custom_optima_sync_status': 'Failed',
                'custom_optima_sync_error': str(e)[:140]
            })
            frappe.db.commit()
            
            raise

