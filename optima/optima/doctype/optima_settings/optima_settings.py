# Copyright (c) 2024, Ronoh and contributors
# For license information, please see license.txt
import frappe
from frappe import _
import pymssql
from frappe.utils import cint
from frappe.model.document import Document
from datetime import datetime, timedelta


class OptimaSettings(Document):
	def validate(self):
		# Ensure port is numeric
		if not self.port.isdigit():
			frappe.throw("Port must be a valid number")

	def get_connection(self, with_database=True):
		"""Get MSSQL connection for Optima."""
		if not self.enabled:
			frappe.throw(_("Optima Integration is not enabled"))
		
		try:
			connection_params = {
				'server': self.server_ip,
				'port': cint(self.port),
				'user': self.username,
				'password': self.get_password('password')
			}
			
			# Only include database if with_database is True and database_name is set
			if with_database and self.database_name:
				connection_params['database'] = self.database_name
			
			conn = pymssql.connect(**connection_params)
			return conn
		except Exception as e:
			frappe.log_error(f"Optima Connection Error: {str(e)}", "Optima Integration")
			
			frappe.throw(_("Could not connect to Optima database. Please check settings and try again."))

	@frappe.whitelist()
	def get_orders(self):
		try:
			# First test without database
			conn = self.get_connection()
			cursor = conn.cursor()
			# cursor.execute("""
			# 	SELECT OPTIMA_Orders.ID, OPTIMA_OrderLines.ID, Optima_BOM.ID
			# 	FROM OPTIMA_Orders
			# 	inner join OPTIMA_OrderLines on OPTIMA_OrderLines.id_ORDINI = OPTIMA_Orders.ID
			# 	inner join Optima_BOM on Optima_BOM.id_ORDINI = OPTIMA_Orders.ID and Optima_BOM.ID_ORDMAST = OPTIMA_OrderLines.ID 
			# 	ORDER BY DATAORD DESC
			# """)
			# cursor.execute("""
			# 	SELECT OPTIMA_OrderLines.ID_ORDMAST, OPTIMA_Orders.ID, OPTIMA_OrderLines.ID, CLIENTE, CODICE_ANAGRAFICA, PRODOTTI_CODICE
			# 	FROM OPTIMA_Orders
			# 	inner join OPTIMA_OrderLines on OPTIMA_OrderLines.ID_ORDINI = OPTIMA_Orders.ID_ORDINI
			# 	ORDER BY DATAORD DESC
			# """)
			# cursor.execute("""
			# 	SELECT ID, ID_ORDINI, CLIENTE
			# 	FROM OPTIMA_Orders
			# 	ORDER BY DATAORD DESC
			# """)
			cursor.execute("""
				SELECT ID, ID_ORDINI, CODICE_ANAGRAFICA, ID_ORDMAST
				FROM OPTIMA_OrderLines
			""")
			# cursor.execute("""
			# 	SELECT ID, PRODOTTI_CODICE, id_ORDINI, ID_ORDMAST
			# 	FROM ORDINI 
			# """)
			orders = [row for row in cursor.fetchall()]
			cursor.close()
			conn.close()
			return {
				"success": True,
				"orders": orders
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to fetch orders: {str(e)}"
			}

	@frappe.whitelist()
	def test_connection(self):
		"""Test connection to Optima database."""
		try:
			# First test without database
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute("SELECT @@VERSION")
			version = cursor.fetchone()
			
			# If database name is provided, try to use it
			database_msg = ""
			if self.database_name:
				try:
					cursor.execute(f"USE {self.database_name}")
					database_msg = f"\nSuccessfully connected to database: {self.database_name}"
				except Exception as e:
					database_msg = f"\nWarning: Could not connect to database '{self.database_name}': {str(e)}"
			
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"message": f"Successfully connected to SQL Server.\nSQL Server Version: {version[0]}{database_msg}"
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Connection failed: {str(e)}"
			}

	@frappe.whitelist()
	def get_databases(self):
		"""Get list of available databases."""
		try:
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute("""
				SELECT name 
				FROM sys.databases 
				WHERE database_id > 4  -- Exclude system databases
				ORDER BY name
			""")
			databases = [row[0] for row in cursor.fetchall()]
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"databases": databases
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to fetch databases: {str(e)}"
			}

	@frappe.whitelist()
	def get_tables(self, database):
		"""Get list of tables in specified database."""
		try:
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute(f"USE {database}")
			cursor.execute("""
				SELECT TABLE_NAME 
				FROM INFORMATION_SCHEMA.TABLES 
				WHERE TABLE_TYPE = 'BASE TABLE'
				ORDER BY TABLE_NAME
			""")
			tables = [row[0] for row in cursor.fetchall()]
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"tables": tables
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to fetch tables: {str(e)}"
			}

	@frappe.whitelist()
	def get_table_fields(self, database, table):
		"""Get field information for a specific table."""
		try:
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute(f"USE {database}")
			cursor.execute("""
				SELECT 
					c.name AS column_name,
					t.name AS data_type,
					c.is_nullable,
					CASE WHEN i.index_id IS NOT NULL AND i.is_primary_key = 1 
						THEN 1 ELSE 0 END AS is_primary_key
				FROM sys.columns c
				INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
				LEFT JOIN sys.index_columns ic ON ic.object_id = c.object_id 
					AND ic.column_id = c.column_id
				LEFT JOIN sys.indexes i ON ic.object_id = i.object_id 
					AND ic.index_id = i.index_id
				WHERE c.object_id = OBJECT_ID(%s)
				ORDER BY c.column_id
			""", (table,))
			
			fields = [
				{
					'name': row[0],
					'type': row[1],
					'is_nullable': bool(row[2]),
					'is_primary_key': bool(row[3])
				}
				for row in cursor.fetchall()
			]
			
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"fields": fields
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to fetch table fields: {str(e)}"
			}
	@frappe.whitelist()
	def get_table_relationships(self, database, table):
		"""Get relationships for a specific table, identifying foreign key constraints."""
		try:
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute(f"USE {database}")
			cursor.execute("""
				SELECT 
					fk.name AS foreign_key_name,
					tp.name AS parent_table,
					cp.name AS parent_column,
					tr.name AS referenced_table,
					cr.name AS referenced_column
				FROM sys.foreign_keys AS fk
				INNER JOIN sys.foreign_key_columns AS fkc ON fk.object_id = fkc.constraint_object_id
				INNER JOIN sys.tables AS tp ON fk.parent_object_id = tp.object_id
				INNER JOIN sys.columns AS cp ON fkc.parent_column_id = cp.column_id AND tp.object_id = cp.object_id
				INNER JOIN sys.tables AS tr ON fk.referenced_object_id = tr.object_id
				INNER JOIN sys.columns AS cr ON fkc.referenced_column_id = cr.column_id AND tr.object_id = cr.object_id
				WHERE tp.name = %s
				ORDER BY foreign_key_name
			""", (table,))
			
			relationships = [
				{
					'foreign_key_name': row[0],
					'parent_table': row[1],
					'parent_column': row[2],
					'referenced_table': row[3],
					'referenced_column': row[4]
				}
				for row in cursor.fetchall()
			]
			
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"relationships": relationships
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to fetch relationships: {str(e)}"
			}

	@frappe.whitelist()
	def dump_database_schema(self, database):
		"""Generate a detailed schema dump of the database including tables, fields, and relationships."""
		try:
			conn = self.get_connection(with_database=False)
			cursor = conn.cursor()
			cursor.execute(f"USE {database}")
			
			# Get all tables
			cursor.execute("""
				SELECT TABLE_NAME 
				FROM INFORMATION_SCHEMA.TABLES 
				WHERE TABLE_TYPE = 'BASE TABLE'
				ORDER BY TABLE_NAME
			""")
			tables = [row[0] for row in cursor.fetchall()]
			
			# Prepare the schema content
			content = f"Database Schema: {database}\n"
			content += "=" * 50 + "\n\n"
			
			for table in tables:
				content += f"Table: {table}\n"
				content += "-" * 50 + "\n\n"
				
				# Get fields
				cursor.execute("""
					SELECT 
						c.name AS column_name,
						t.name AS data_type,
						c.max_length,
						c.is_nullable,
						CASE WHEN i.index_id IS NOT NULL AND i.is_primary_key = 1 
							THEN 1 ELSE 0 END AS is_primary_key,
						CASE WHEN i.index_id IS NOT NULL AND i.is_unique = 1 
							THEN 1 ELSE 0 END AS is_unique
					FROM sys.columns c
					INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
					LEFT JOIN sys.index_columns ic ON ic.object_id = c.object_id 
						AND ic.column_id = c.column_id
					LEFT JOIN sys.indexes i ON ic.object_id = i.object_id 
						AND ic.index_id = i.index_id
					WHERE c.object_id = OBJECT_ID(%s)
					ORDER BY c.column_id
				""", (table,))
				
				content += "Fields:\n"
				for row in cursor.fetchall():
					flags = []
					if row[3]: flags.append("NULL")
					if not row[3]: flags.append("NOT NULL")
					if row[4]: flags.append("PRIMARY KEY")
					if row[5]: flags.append("UNIQUE")
					
					length_info = f"({row[2]})" if row[2] != -1 else ""
					content += f"  - {row[0]}: {row[1]}{length_info} {' '.join(flags)}\n"
				
				# Get foreign keys
				cursor.execute("""
					SELECT 
						fk.name AS foreign_key_name,
						cp.name AS parent_column,
						tr.name AS referenced_table,
						cr.name AS referenced_column
					FROM sys.foreign_keys AS fk
					INNER JOIN sys.foreign_key_columns AS fkc ON fk.object_id = fkc.constraint_object_id
					INNER JOIN sys.tables AS tp ON fk.parent_object_id = tp.object_id
					INNER JOIN sys.columns AS cp ON fkc.parent_column_id = cp.column_id AND tp.object_id = cp.object_id
					INNER JOIN sys.tables AS tr ON fk.referenced_object_id = tr.object_id
					INNER JOIN sys.columns AS cr ON fkc.referenced_column_id = cr.column_id AND tr.object_id = cr.object_id
					WHERE tp.name = %s
					ORDER BY foreign_key_name
				""", (table,))
				
				relationships = cursor.fetchall()
				if relationships:
					content += "\nForeign Keys:\n"
					for rel in relationships:
						content += f"  - {rel[0]}: {rel[1]} -> {rel[2]}.{rel[3]}\n"
				
				content += "\n"
			
			cursor.close()
			conn.close()
			
			# Save the content to a file
			filename = f"schema_{database}_{frappe.utils.now().split()[0]}.txt"
			file_url = save_file(filename, content)
			
			return {
				"success": True,
				"file_url": file_url
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to generate schema: {str(e)}"
			}

	@frappe.whitelist()
	def insert_test_order(self):
		"""Insert a test order into Optima database."""
		try:
			conn = self.get_connection()
			cursor = conn.cursor()
			
			# Generate shorter unique order reference (12 chars max for ORDINE column)
			
			doc = frappe.get_doc("Sales Order", "SAL-ORD-2025-00001")
			order_ref = "S202500006"
			# Insert into OPTIMA_Orders
			cursor.execute(f"""
				INSERT INTO OPTIMA_Orders (
					CLIENTE, DESCR_TIPICAUDOC, RIFCLI, RIF, ALLNRDOC, 
					DATAORD, DATACONS, DEF, NOTE1, ID_ORDINI,
					abilitazione_optima
				) VALUES (
					'1000', 'Production Order', '{order_ref}', '{order_ref}', '{order_ref}', 
					'{doc.transaction_date}', '{doc.delivery_date}',
					'Y', 'Test Order', 2017, 'Y'
				)
			""")
			
			# # Get the ID of inserted order
			# # cursor.execute("SELECT @@IDENTITY")
			order_id = 2017
			line_id = 2700
			cursor.execute(f"""
				INSERT INTO OPTIMA_Orderlines (
					CODICE_ANAGRAFICA, PRODOTTI_CODICE, DESCR_MAT_COMP, COD_ART_CLIENTE, DESCMAT,
					QTAPZ, RIGA, ID_ORDINI, ID_ORDMAST, ID_PZ, DIMXPZ, DIMYPZ
				) VALUES (
					'Tempered Glass', 'Tempered Glass', 'Tempered Glass', 'Tempered Glass', 'Tempered Glass',
					3 , 1, '{order_id}', '{line_id}', '{line_id}', 1500, 900
				)
			""")
			
				# cursor.execute("SELECT @@IDENTITY")
				# line_id = cursor.fetchone()[0]
				# i += 1
				# j = 1000
				# for comp in doc.components:
				# 	if comp.parent_name == item.name_id:

			cursor.execute(f"""
				INSERT INTO OPTIMA_Bom_Detail (
					id_ORDINI, ID_ORDMAST, COMPONENT_URL, 
					CODICE_ANAGRAFICA
				) VALUES (
					{order_id}, {line_id}, 'Prod1.Mat1', '11610108'
				)
			""")

			cursor.execute(f"""
				INSERT INTO OPTIMA_Bom_Detail (
					id_ORDINI, ID_ORDMAST, COMPONENT_URL, 
					CODICE_ANAGRAFICA
				) VALUES (
					{order_id}, {line_id}, 'Prod1.Mat1.Work4', 'SandBlasting'
				)
			""")

			
			conn.commit()
			cursor.close()
			conn.close()
			
			return {
				"success": True,
				"message": f"Test order {order_ref} created successfully"
			}
		except Exception as e:
			return {
				"success": False,
				"message": f"Failed to create test order: {str(e)}"
			}

def save_file(filename, content):
	"""Save content to a file in the site's public folder."""
	from frappe.utils import get_files_path
	import os
	
	# Create the file path
	file_path = os.path.join(get_files_path(), filename)
	
	# Write the content to the file
	with open(file_path, 'w') as f:
		f.write(content)
	
	# Return the URL to access the file
	return f"/files/{filename}"
