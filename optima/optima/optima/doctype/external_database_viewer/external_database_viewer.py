# Copyright (c) 2024, JCMAPP and contributors
# For license information, please see license.txt

import pymssql
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class ExternalDatabaseViewer(Document):
	pass

@frappe.whitelist()
def fetch_databases(server, port, username, password):
    try:
        # Connect to the MS SQL server
        conn = pymssql.connect(server=server, port=port, user=username, password=password)
        cursor = conn.cursor()
        
        # Query to list all databases
        cursor.execute("SELECT name FROM master.dbo.sysdatabases")
        databases = cursor.fetchall()
        
        # Close connection
        cursor.close()
        conn.close()

        # Return the list of databases
        return [{"name": db[0]} for db in databases]

    except Exception as e:
        frappe.log_error(message=str(e), title="MS SQL Connection Error")
        return {"error": str(e)}

@frappe.whitelist()
def fetch_tables(server, port, username, password, database):
    try:
        # Connect to the specific MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()
        
        # Query to list all tables in the database
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
        tables = cursor.fetchall()
        
        # Close connection
        cursor.close()
        conn.close()

        # Return the list of tables
        return [{"table_name": table[0]} for table in tables]

    except Exception as e:
        frappe.log_error(message=str(e), title="MS SQL Connection Error")
        return {"error": str(e)}

@frappe.whitelist()
def fetch_columns(server, port, username, password, database, table):
    try:
        # Connect to the specific MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()
        
        # Query to get column details for the specified table
        cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_name = '{table}'")
        columns = cursor.fetchall()
        
        # Close connection
        cursor.close()
        conn.close()

        # Return the list of columns with their data types
        return [{"column_name": col[0], "data_type": col[1]} for col in columns]

    except Exception as e:
        frappe.log_error(message=str(e), title="MS SQL Column Fetch Error")
        return {"error": str(e)}
@frappe.whitelist()
def fetch_table_data(server, port, username, password, database, table):
    try:
        # Connect to the specific MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()
        
        # Query to get the first 5 rows from the specified table
        cursor.execute(f"SELECT TOP 5 * FROM {table}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]  # Column names
        
        # Format data as a list of dictionaries for better readability
        data = [dict(zip(columns, row)) for row in rows]
        
        # Close connection
        cursor.close()
        conn.close()

        # Return the table data
        return data

    except Exception as e:
        frappe.log_error(message=str(e), title="MS SQL Data Fetch Error")
        return {"error": str(e)}
@frappe.whitelist()
def fetch_items(server, port, username, password, database, table, limit=5):
    try:
        # Connect to the specific MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor(as_dict=True)

        # Query to get the first `limit` items from the specified table
        cursor.execute(f"SELECT TOP {limit} * FROM {table} ORDER BY [id] DESC")
        items = cursor.fetchall()

        # Close connection
        cursor.close()
        conn.close()

        # Return the list of items
        return items

    except Exception as e:
        frappe.log_error(message=str(e), title="MS SQL Item Fetch Error")
        return {"error": str(e)}
@frappe.whitelist()
def fetch_latest_items(server, port, username, password, database, table):
    try:
        # Connect to the specific MS SQL database
        server = "196.200.26.2"
        port = "1433"
        username = "sa"
        password = "123@impala"
        database = "CONNECTOR_ORDERS"

        # Connect to the MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()

        # Query to get column names to identify a suitable ordering column
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}'")
        columns = [col[0] for col in cursor.fetchall()]

        # Choose an appropriate column for ordering (e.g., created_at or first column as fallback)
        order_column = 'created_at' if 'created_at' in columns else columns[0]

        # Query to get the latest 5 items using the identified column
        cursor.execute(f"SELECT * FROM {table} ORDER BY [{order_column}] DESC")
        items = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]  # Get column names

        # Close connection
        cursor.close()
        conn.close()

        # Return the list of items with column names
        return {
            "columns": column_names,
            "items": items
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Fetch Latest Items Error")
        return {"error": str(e)}

import pymssql
import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def insert_item_to_external_db(item_name, description, item_code, start_date=None, end_date=None):
    try:
        # Connection parameters
        server = "196.200.26.2"
        port = "1433"
        username = "sa"
        password = "123@impala"
        database = "CONNECTOR_ORDERS"

        # Connect to the MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()

        # SQL insert query with all columns specified
        insert_query = """
            INSERT INTO ITEMS (
                ID_ITEMS, ID_DBASEORDINI, PROGR, ID_COMMESSE, STATO, RACK, RACKSORT, ID_WORKS, ELAB,
                PROGRELAB, POSPZ, RACKNO, SIDENO, STACKNO, X, Y, Z, ID_RACKS, ID_CBOLLER, ID_RWKITS,
                ID_ORDMAST, PRIOPZ, PREFEPZ, BATCH_RACKSORT, NOTES, START_DATE, END_DATE, SEQX,
                FLAGS_PROD, StartForDate, EndForDate, StartRealDate, EndRealDate, TimeStdUnit,
                TimeRealUnit, WasteStdQty, WasteRealQty, EWPOSPZ, ID_LASTRE, IS_STOCK, LASTUSER,
                LASTDATE, LASTCLIENT, USERCREATE, DATECREATE, CLIENTCREATE, ID_ITEMS_PARENT,
                EXTERNAL_ID_ITEMS, ROTANGLE, RACKCDL, DESTINATION, RACKROTATED, TIPOSCARICO,
                ID_DOC_BOOKED, ID_CBOLLER_UNLOAD, QUANTITY, RACK_X, RACK_Y, RACK_Z, DURATION,
                ID_RACKINSTANCE, ID_ITEMSDBASE, TIPO_ITEM, GMCQ_BARCODE, Excluded, Excluded_REASON
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """

        now = now_datetime()
        data = (
            9999,  # ID_ITEMS
            None,  # ID_DBASEORDINI
            1,  # PROGR
            None,  # ID_COMMESSE
            'NEW',  # STATO
            None,  # RACK
            None,  # RACKSORT
            None,  # ID_WORKS
            0,  # ELAB
            None,  # PROGRELAB
            None,  # POSPZ
            None,  # RACKNO
            None,  # SIDENO
            None,  # STACKNO
            None,  # X
            None,  # Y
            None,  # Z
            None,  # ID_RACKS
            None,  # ID_CBOLLER
            None,  # ID_RWKITS
            None,  # ID_ORDMAST
            None,  # PRIOPZ
            None,  # PREFEPZ
            None,  # BATCH_RACKSORT
            description,  # NOTES
            start_date,  # START_DATE
            end_date,  # END_DATE
            None,  # SEQX
            None,  # FLAGS_PROD
            start_date,  # StartForDate
            end_date,  # EndForDate
            None,  # StartRealDate
            None,  # EndRealDate
            None,  # TimeStdUnit
            None,  # TimeRealUnit
            None,  # WasteStdQty
            None,  # WasteRealQty
            None,  # EWPOSPZ
            None,  # ID_LASTRE
            1,  # IS_STOCK
            'system_user',  # LASTUSER
            now,  # LASTDATE
            'system_client',  # LASTCLIENT
            'system_user',  # USERCREATE
            now,  # DATECREATE
            'system_client',  # CLIENTCREATE
            None,  # ID_ITEMS_PARENT
            None,  # EXTERNAL_ID_ITEMS
            None,  # ROTANGLE
            None,  # RACKCDL
            None,  # DESTINATION
            0,  # RACKROTATED
            None,  # TIPOSCARICO
            None,  # ID_DOC_BOOKED
            None,  # ID_CBOLLER_UNLOAD
            1,  # QUANTITY
            None,  # RACK_X
            None,  # RACK_Y
            None,  # RACK_Z
            None,  # DURATION
            None,  # ID_RACKINSTANCE
            None,  # ID_ITEMSDBASE
            None,  # TIPO_ITEM
            item_code,  # GMCQ_BARCODE
            0,  # Excluded
            None  # Excluded_REASON
        )

        # Execute the insert query
        cursor.execute(insert_query, data)
        conn.commit()
        print("Insert committed successfully.")

        # Close the connection
        cursor.close()
        conn.close()

        return {"message": "Item inserted successfully"}

    except Exception as e:
        frappe.log_error(f"Error while inserting item: {str(e)}", "Insert Item to External DB")
        return f"Error: {str(e)}"

    finally:
        if 'conn' in locals() and conn:
            conn.close()

import pymssql
import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def insert_customer_to_external_db(code, description, address, city, province, email, telephone, vat_ex):
    try:
        # Connection parameters
        server = "196.200.26.2"
        port = "1433"
        username = "sa"
        password = "123@impala"
        database = "CONNECTOR_ORDERS"

        # Connect to the MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()

        # SQL insert query (remove the IDENTITY column 'id')
        insert_query = """
            INSERT INTO ERP_Customers (
                Code, Description, Address, City, Province, Email, Telephone, VatEx,
                ID_OPERATIONS, TimeStamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        # Static data and provided values
        now = now_datetime()
        data = (
            code,
            description,
            address,
            city,
            province,
            email,
            telephone,
            vat_ex,
            1,  # ID_OPERATIONS (example value)
            now  # TimeStamp
        )

        # Execute the insert query
        cursor.execute(insert_query, data)
        conn.commit()
        print("Insert committed successfully.")

        # Close the connection
        cursor.close()
        conn.close()

        return {"message": "Customer inserted successfully"}

    except Exception as e:
        frappe.log_error(f"Error while inserting customer: {str(e)}", "Insert Customer to External DB")
        return {"error": str(e)}

    finally:
        if 'conn' in locals() and conn:
            conn.close()

import pymssql
import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def insert_sales_order_to_external_tables():
    try:
        # Connection parameters
        server = "196.200.26.2"
        port = "1433"
        username = "sa"
        password = "123@impala"
        database = "CONNECTOR_ORDERS"

        # Connect to the MS SQL database
        conn = pymssql.connect(server=server, port=port, user=username, password=password, database=database)
        cursor = conn.cursor()

        # Insert into OPTIMA_Orders
        insert_order_query = """
            INSERT INTO OPTIMA_Orders (
                CLIENTE, DATAORD, DESCR1_SPED, DESCR_TIPICAUDOC, NAZIONI_CODICE, RIF, DEF, statoordine, ID_ORDINI
            )
            VALUES (
                123, GETDATE(), 'Static Description', 'Static Document Description', 'CTY', 'Ref123', 'D', 'O', 1001  -- Adjust ID_ORDINI if necessary
            )
        """
        cursor.execute(insert_order_query)

        # Retrieve the last inserted ID if needed for future linkage (can replace ID_ORDINI with 1001)
        cursor.execute("SELECT @@IDENTITY")
        last_inserted_id = cursor.fetchone()[0]

        # Insert into OPTIMA_Orderlines with matching ID_ORDINI
        insert_orderline_query = """
            INSERT INTO OPTIMA_Orderlines (
                ID_ORDINI, ID_ORDMAST, RIGA, DESCMAT, QTAPZ, DESCR_MAT_COMP, COD_ART_CLIENTE
            )
            VALUES (%s, %s, 1, 'Static Item Description', 10, 'Static Material Description', 'ClientCode123')
        """
        cursor.execute(insert_orderline_query, (1001, last_inserted_id))  # Matching ID_ORDINI (1001) with the OPTIMA_Orders entry

        # Insert into OPTIMA_OrderTimes
        insert_ordertimes_query = """
            INSERT INTO OPTIMA_Bom (ID_ORDMAST, RIGA,ID_ORDINI)
            VALUES (%s, 1,1001)
        """
        cursor.execute(insert_ordertimes_query, (last_inserted_id,))

        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Sales order and related records inserted successfully"}

    except Exception as e:
        frappe.log_error(f"Error while inserting sales order: {str(e)}", "Insert Sales Order to External Tables")
        return {"error": str(e)}

    finally:
        if 'conn' in locals() and conn:
            conn.close()

