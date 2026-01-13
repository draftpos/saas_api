import frappe

def execute():
    if not frappe.db.exists(
        "Custom Field",
        {"dt": "User", "fieldname": "user_rights_profile"}
    ):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "User",
            "label": "User Rights Profile",
            "fieldname": "user_rights_profile",
            "fieldtype": "Link",
            "options": "User Rights Profile",
            "insert_after": "role_profile_name",
        }).insert(ignore_permissions=True)
