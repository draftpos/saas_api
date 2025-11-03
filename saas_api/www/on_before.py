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


def set_user_company(doc, method):
    print("0000000000000000000000000")
    if not doc.company:
        user = frappe.get_doc("User", frappe.session.user)
        # Assuming the user has one company assigned in User Permissions
        allowed_companies = frappe.get_list("User Permission",
                                            filters={"user": user.name, "allow": "Company"},
                                            pluck="for_value")
        if allowed_companies:
            doc.company = allowed_companies[0]  # Pick the first allowed company
        else:
            frappe.throw("No company assigned for the logged-in user.") 


def supplier_permission_query(user):
    # Allow full access to Administrator or Supplier Managers
    print("----------------------------------------now-------------------")
    if not user or user == "Administrator":
        return ""
    # Regular users can only see what they created
    return f"`tabSupplier`.owner = '{user}'"

def customer_permission_query(user):
    # Allow full access to Administrator or Supplier Managers
    print("----------------------------------------now-------------------")
    if not user or user == "Administrator":
        return ""
    # Regular users can only see what they created
    return f"`tabCustomer`.owner = '{user}'"

