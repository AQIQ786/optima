import frappe
from frappe import _
import pymssql
from frappe.utils import cint
from contextlib import contextmanager
import time

def get_optima_settings():
    """Get Optima settings from the doctype."""
    settings = frappe.get_single("Optima Settings")
    if not settings.enabled:
        frappe.throw(_("Optima Integration is not enabled"))
    return settings

@contextmanager
def get_optima_connection():
    """Get connection to Optima database."""
    settings = frappe.get_doc("Optima Settings")
    conn = None
    
    try:
        conn = pymssql.connect(
            server=settings.server_ip,
            user=settings.username,
            password=settings.get_password('password'),
            database='CONNECTOR_ORDERS',
            autocommit=False
        )
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def test_connection():
    """Test connection to Optima database."""
    try:
        conn = get_optima_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "success": True,
            "message": f"Successfully connected to Optima database.\nSQL Server Version: {version[0]}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        } 

def verify_permissions(cursor):
    """Verify user has proper permissions"""
    try:
        cursor.execute("""
            SELECT HAS_PERMS_BY_NAME('CONNECTOR_ORDERS', 'SCHEMA', 'INSERT')
        """)
        has_insert = cursor.fetchone()[0]
        
        if not has_insert:
            raise Exception("User does not have required permissions on CONNECTOR_ORDERS schema")
            
    except Exception as e:
        frappe.log_error(f"Permission verification error: {str(e)}", "Optima Permissions Error")
        raise 