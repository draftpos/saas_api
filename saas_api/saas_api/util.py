import frappe

def create_default_user_rights():
    """Create two default User Rights Profiles with permissions"""
    
    default_profiles = [
        {
            "profile_name": "Admin Rights",
            "is_admin": 1,
            "permissions": [
                {"feature": "Dashboard", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "POS", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Quotations", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Sales", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Products", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Stock Management", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Payment Entries", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Reports", "can_read": 1},
                {"feature": "Settings", "can_read": 1},
                {"feature": "Printer", "can_read": 1}
            ]
        },
        {
            "profile_name": "Cashier Rights",
            "is_admin": 0,
            "permissions": [
                {"feature": "Dashboard", "can_read": 1},
                {"feature": "POS", "can_read": 1},
                {"feature": "Quotations", "can_read": 1},
                # Add other features with limited permissions
            ]
        }
    ]
    
    for profile in default_profiles:
        # Avoid duplicates
        if not frappe.db.exists("User Rights Profile", profile["profile_name"]):
            doc = frappe.get_doc({
                "doctype": "User Rights Profile",
                "profile_name": profile["profile_name"],
                "is_admin": profile["is_admin"],
                "permissions": profile["permissions"]
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Created default profile: {profile['profile_name']}")
