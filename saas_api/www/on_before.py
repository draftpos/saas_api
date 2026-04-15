import frappe
from .api import generate_item_code, generate_supplier_code, generate_item_group_code,set_defaults_for_user

def item_before_insert(doc, method):
    if not doc.item_name:
        return

    exists = frappe.db.exists(
        "Item",
        {
            "item_name": doc.item_name,
            "name": ["!=", doc.name]  # important for updates
        }
    )

    if exists:
        frappe.throw(
            f"Item with name <b>{doc.item_name}</b> already exists."
        )
    if not doc.item_group:
        doc.item_group = "All Item Groups"
    if not frappe.db.exists("Item Group", doc.item_group):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": doc.item_group,
            "parent_item_group": "All Item Groups"
        }).insert(ignore_permissions=True)


# def supplier_before_insert(doc, method):
#     doc.supplier_name = generate_supplier_code()

# def item_group_before_insert(doc, method):
#     doc.item_group_name = generate_item_group_code()


# def set_user_company(doc, method):
#     if not doc.company:
#         user = frappe.get_doc("User", frappe.session.user)
#         allowed_companies = frappe.get_list("User Permission",
#                                             filters={"user": user.name, "allow": "Company"},
#                                             pluck="for_value")
#         if allowed_companies:
#             doc.company = allowed_companies[0]  
#         else:
#             frappe.throw("No company assigned for the logged-in user.") 

def supplier_permission_query(user):
    
    return ""

# def warehouse_permission_query(user):
#     if not user or user == "Administrator":
#         return ""
#     return f"`tabWarehouse`.owner = '{user}'"

# def users_permission_query(user):
#     if not user or user == "Administrator":
#         return ""
#     return f"`tabUser`.owner = '{user}'"
def warehouse_permission_query(user):
    """Return SQL condition string for Warehouse permissions for a given user."""
    if "System Manager" in frappe.get_roles(user):
        return ""

    company = frappe.db.get_value("User", user, "default_company")
    if company:
        return f"`tabWarehouse`.company = '{company}'"

    return "1=1"

def item_group_permission_query(user):
    if not user or user == "Administrator":
        return ""
    return f"`tabItem Group`.owner = '{user}'"


def customer_permission_query(user):
    print("yes------------------2")
    """
    Returning '1=1' effectively tells the SQL engine:
    'Where 1 equals 1' (which is always true), bypassing
    any restrictive User Permission filters.
    """
    return "1=1"

def has_customer_permission(doc, ptype, user):
    print("yes---------------------")
    # Returning True here tells Frappe: 
    # "This user has permission to access this specific document."
    return True

def after_insert(doc, method):
    """
    Apply defaults immediately after a new User is created
    """
    if not doc.email:
        return

    # Avoid applying defaults for Administrator or Guest
    # if doc.name in ("Administrator", "Guest"):
    #     return

    set_defaults_for_user(doc.email)
