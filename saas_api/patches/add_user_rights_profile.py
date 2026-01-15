import frappe

def execute():
    # Check if doctype exists first
    if not frappe.db.exists("DocType", "User Rights Profile"):
        frappe.log_error("User Rights Profile doctype not found. Skipping patch.", "Patch Warning")
        return
    
    if not frappe.db.exists(
        "Custom Field",
        {"dt": "User", "fieldname": "user_rights_profile"}
    ):
        try:
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "User",
                "label": "User Rights Profile",
                "fieldname": "user_rights_profile",
                "fieldtype": "Link",
                "options": "User Rights Profile",
                "insert_after": "role_profile_name",
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error adding user_rights_profile field: {str(e)}", "Patch Error")
