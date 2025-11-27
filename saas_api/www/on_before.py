import frappe
from .api import generate_item_code, generate_supplier_code, generate_item_group_code

def item_before_insert(doc, method):
    doc.item_code = generate_item_code()
    if not doc.item_group:
        doc.item_group = "All Item Groups"
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
    if not doc.company:
        user = frappe.get_doc("User", frappe.session.user)
        allowed_companies = frappe.get_list("User Permission",
                                            filters={"user": user.name, "allow": "Company"},
                                            pluck="for_value")
        if allowed_companies:
            doc.company = allowed_companies[0]  
        else:
            frappe.throw("No company assigned for the logged-in user.") 

def supplier_permission_query(user):
    if not user or user == "Administrator":
        return ""
    return f"`tabSupplier`.owner = '{user}'"

def warehouse_permission_query(user):
    if not user or user == "Administrator":
        return ""
    return f"`tabWarehouse`.owner = '{user}'"

def users_permission_query(user):
    if not user or user == "Administrator":
        return ""
    return f"`tabUser`.owner = '{user}'"


def item_group_permission_query(user):
    if not user or user == "Administrator":
        return ""
    return f"`tabItem Group`.owner = '{user}'"
