import frappe

def assign_admin_profile():
    admin_user = frappe.get_doc("User", "Administrator")
    if not admin_user.user_rights_profile:
        admin_user.user_rights_profile = "Admin"
        admin_user.save(ignore_permissions=True)