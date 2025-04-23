# Copyright (c) 2024, Ronoh and contributors
# For license information, please see license.txt
import random
from copy import deepcopy
import frappe
from frappe.model.document import Document
from optima.optima.doctype.optima_settings.optima_settings import OptimaSettings


class OptimaOrder(Document):
	def validate(self):
		tree, products = build_tree(self.components)
		assign_component_urls(tree, products)
		self.update({"components": tree})

def build_tree(items):
	# Create a lookup dict where each node is extended with an empty children list.
	nodes = {}
	products = {}
	i = 1
	for item in items:
		node = deepcopy(item)  # make a copy of the dictionary item
		node = node.__dict__
		node["children"] = []
		nodes[(item.get("name_id"), item.get("parent_name"))] = node
		if not products.get(item.get("parent_name")):
			products[item.get("parent_name")] = f"Prod{i}"
			i += 1
	# Build the tree by linking children to their parent node.
	tree = []
	for item in items:
		node = nodes[(item.get("name_id"), item.get("parent_name"))]
		parent_id = item.get("group_item_name")
		if parent_id:  # if group_item is not empty, attach to parent
			parent_node = nodes.get((parent_id, item.get("parent_name")))
			if parent_node:
				parent_node["children"].append(node)
			else:
				print(f"Warning: Parent {parent_id} not found for item {item['name_id']}")
		tree.append(node)
	return tree, products

def assign_component_urls(tree, products, parent_url=None, level=1):
	"""
	Recursively assign a component_url field to each node.
	
	Args:
		tree (list): list of nodes at the current level.
		parent_url (str): the component_url of the parent node.
		level (int): numeric level (1 for top-level, 2 for children, etc.).
	"""
	# Mindex = 1
	# Windex = 1
	indexes = {}
	if level == 1:
		# Top-level: assign "Product{index}"
		for node in tree:
			print(node["parent_name"])
			print(node["item_code"])
			if not indexes.get(node["parent_name"]):
				indexes[node["parent_name"]] = [1, 1]  # 1- Mat, 2- Work
			if "checked" not in node or not node["checked"]:
				if frappe.db.get_value("Item", node["item_code"], "is_process"):
					node["component_url"] = f"{products[node.get("parent_name")]}.Work{indexes[node["parent_name"]][1]}"
					indexes[node["parent_name"]][1] += 1

				else: 
					node["component_url"] = f"{products[node.get("parent_name")]}.Mat{indexes[node["parent_name"]][0]}"
					indexes[node["parent_name"]][0] += 1
				
				node["checked"] = 1
				
			# Process children using level 2 pattern.
			assign_component_urls(node["children"], products, parent_url=node["component_url"], level=2)
	else:
		# Second-level: parent's url plus "-Material{index}"
		for node in tree:
			print(node["parent_name"])
			print(node["item_code"])
			if not indexes.get(node["parent_name"]):
				indexes[node["parent_name"]] = [1, 1]  # 1- Mat, 2- Work
			if "checked" not in node or not node["checked"]:
				if frappe.db.get_value("Item", node["item_code"], "is_process"):
					node["component_url"] = f"{parent_url}.Work{indexes[node["parent_name"]][1]}"
					indexes[(node["parent_name"])][1] += 1

				else:
					node["component_url"] = f"{parent_url}.Mat{indexes[node["parent_name"]][0]}"
					indexes[node["parent_name"]][0] += 1

				node["checked"] = 1

			# Process children using level 3 pattern.
			assign_component_urls(node["children"], products, parent_url=node["component_url"], level=3)

# A helper function to print the tree for visualization.
def print_tree(tree, level=0):
	for node in tree:
		print("  " * level + f"{node['item_code']} ({node['name_id']}): {node['component_url']}")
		print_tree(node["children"], level+1)

@frappe.whitelist()
def make_optima_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	return get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Optima Order",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {
					"name": "sales_order",
					"transaction_date": "order_date"
				}
			},
			"Sales Order Item": {
				"doctype": "Optima Order Item",
				"field_map": {
					"name": "so_detail",
					"parent": "sales_order",
				},
			},
			"Sales Order Item Components": {
				"doctype": "Optima Order Component",
				"field_map": {
					"name": "component_row",
				},
			},
		},
		target_doc,
	)

@frappe.whitelist()
def send_to_optima(order):
	doc = frappe.get_doc("Optima Order", order)
	msg = ""
	i = 1
	if not doc.order_number:
		msg += f"{i}- Order Number"
		i += 1

	if not doc.optima_order_id:
		msg += f"{i}- Optima Order ID"
		i += 1

	if msg:
		return {"stauts": "failed", "msg": "Missing Fields: \n" + msg}

	try:
		optima_sett = frappe.get_single("Optima Settings")
		conn = optima_sett.get_connection()
		cursor = conn.cursor()
		cursor.execute(f"""
			INSERT INTO OPTIMA_Orders (
				CLIENTE, DESCR_TIPICAUDOC, RIFCLI, RIF, ALLNRDOC, 
				DATAORD, DATACONS, DEF, ID_ORDINI, abilitazione_optima,
				DATAINIZIO, DATAFINE,
				NOTES,
				DESCR1_SPED, DESCR2_SPED,
				INDIRI_SPED, CAP_SPED, LOCALITA_SPED, PROV_SPED,
				COMMESSA_CLI, RIFINTERNO, RIFAGENTE
			) VALUES (
				{sql_safe(doc.get("customer"))}, 'Production Order', {sql_safe(doc.optima_order_id)}, {sql_safe(doc.optima_order_id)}, {sql_safe(doc.optima_order_id)}, 
				{sql_safe(doc.get("transaction_date"))}, {sql_safe(doc.get("delivery_date"))}, 'Y', {sql_safe(doc.order_number)}, 'Y',
				{sql_safe(doc.get("start_date"))}, {sql_safe(doc.get("end_date"))},
				{sql_safe(doc.get("notes"))},
				{sql_safe(doc.get("delivery_description_1"))}, {sql_safe(doc.get("delivery_description_2"))},
				{sql_safe(doc.get("delivery_address"))}, {sql_safe(doc.get("delivery_zip"))}, {sql_safe(doc.get("delivery_city"))}, {sql_safe(doc.get("delivery_country"))},
				{sql_safe(doc.get("work_order"))}, {sql_safe(doc.get("internal_reference"))}, {sql_safe(doc.get("agent_reference"))}
			)
		""")
		insert_items(cursor, doc)

		conn.commit()
		cursor.close()
		conn.close()
		
		return {
			"success": 1,
			"message": f"Order {doc.optima_order_id} created successfully"
		}
	except Exception as e:
		return {
			"success": 0,
			"message": f"Failed to create test order: {str(e)}"
		}


def insert_items(cursor, doc):
	for item in doc.items:
		print("HHHHH")
		unique_id = False
		while not unique_id:
			line_id = random.randint(1, 10000)

			cursor.execute(f"""
				SELECT TOP 1 ID_ORDMAST FROM OPTIMA_Orderlines
				WHERE ID_ORDMAST = '{line_id}'
			""")

			lines = cursor.fetchall()
			if not lines:
				unique_id = True

		cursor.execute(f"""
			INSERT INTO OPTIMA_Orderlines (
				CODICE_ANAGRAFICA, PRODOTTI_CODICE, DESCR_MAT_COMP,
				RIGA, ID_ORDINI, ID_ORDMAST, ID_PZ, DIMXPZ, DIMYPZ, QTAPZ
			) VALUES (
				'{item.item_code}', '{item.item_code}', '{item.description}',
				{item.idx}, '{doc.order_number}', '{line_id}', '{line_id}', {item.width}, {item.height}, {item.pcs}
			)
		""")

		if doc.components:
			for comp in doc.components:
				if comp.parent_name == item.name_id:
					item_code = comp.item_code
					if frappe.db.get_value("Item", comp.item_code, "is_process"):
						item_code = frappe.db.get_value("Item", comp.item_code, "process")
					print("ZZZZZ")
					cursor.execute(f"""
						INSERT INTO OPTIMA_Bom_Detail (
							id_ORDINI, ID_ORDMAST, COMPONENT_URL, 
							CODICE_ANAGRAFICA
						) VALUES (
							{doc.order_number}, {line_id}, '{comp.component_url}', '{item_code}'
						)
					""")


def sql_safe(value):
    return f"'{value}'" if value is not None else "NULL"