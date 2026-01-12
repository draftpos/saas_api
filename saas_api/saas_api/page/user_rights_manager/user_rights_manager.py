import frappe


def get_context(context):
    context.title = "User Rights Manager"


@frappe.whitelist()
def load_data():
    return {
        "users": frappe.get_all("User", fields=["name", "full_name"]),
        "user_rights": frappe.get_all("user rights",fields=["name", "user"])
    }