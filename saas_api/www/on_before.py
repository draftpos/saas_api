import frappe
from .api import generate_item_code, generate_supplier_code, generate_item_group_code

def item_before_insert(doc, method):
   
    """
    Before inserting an Item:
    - Auto-generate item_code if missing
    - Ensure item_group exists or auto-create
    """
    # Generate item_code if missing
    
    doc.item_code = generate_item_code()

    # Ensure item_group exists
    if not doc.item_group:
        doc.item_group = "All Item Groups"

    # Auto-create Item Group if it doesn't exist
    if not frappe.db.exists("Item Group", doc.item_group):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": doc.item_group,
            "parent_item_group": "All Item Groups"
        }).insert(ignore_permissions=True)


def supplier_before_insert(doc, method):
    doc.supplier_name = generate_supplier_code()

def item_group_before_insert(doc, method):

    doc.item_group_name = generate_item_group_code()
