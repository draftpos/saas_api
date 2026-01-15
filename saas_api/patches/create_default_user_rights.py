import frappe


def create_default_user_rights():
    """Create default User Rights Profiles safely on install"""

    # Hard stop if table is not ready (first migrate protection)
    if not frappe.db.table_exists("tabUser Rights Profile"):
        frappe.logger().warning(
            "User Rights Profile table not found. Skipping default rights creation."
        )
        return

    default_profiles = [
        {
            "profile_name": "Admin Rights",
            "is_admin": 1,
            "permissions": [
                {
                    "feature": f,
                    "can_read": 1,
                    "can_create": 1,
                    "can_update": 1,
                    "can_delete": 1,
                    "can_submit": 1,
                }
                for f in [
                    "Dashboard", "POS", "Quotations", "Sales", "Products",
                    "Stock Management", "Payment Entries", "Reports",
                    "Settings", "Printer"
                ]
            ]
        },
        {
            "profile_name": "Basic User Rights",
            "is_admin": 0,
            "permissions": [
                {"feature": f, "can_read": 1}
                for f in [
                    "Dashboard", "POS", "Quotations", "Sales", "Products",
                    "Stock Management", "Payment Entries", "Reports",
                    "Settings", "Printer"
                ]
            ]
        }
    ]

    for profile in default_profiles:
        if frappe.db.exists("User Rights Profile", profile["profile_name"]):
            continue  # DO NOT mutate existing profiles

        doc = frappe.get_doc({
            "doctype": "User Rights Profile",
            "profile_name": profile["profile_name"],
            "is_admin": profile["is_admin"],
            "permissions": profile["permissions"]
        })

        doc.insert(ignore_permissions=True)