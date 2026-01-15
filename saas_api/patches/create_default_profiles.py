import frappe

def execute():
    """Create default User Rights Profiles: Admin and Cashier"""
    
    if not frappe.db.table_exists("tabUser Rights Profile"):
        frappe.throw("User Rights Profile table does not exist. Run `bench migrate` first.")

    # Define profiles
    default_profiles = [
        {
            "profile_name": "Admin",
            "is_admin": 1,
            "permissions": [
                {"feature": f, "can_read": 1, "can_create": 1,
                 "can_update": 1, "can_delete": 1, "can_submit": 1}
                for f in ["Dashboard", "POS", "Quotations", "Sales", "Products",
                          "Stock Management", "Payment Entries", "Reports", "Settings", "Printer"]
            ]
        },
        {
            "profile_name": "Cashier",
            "is_admin": 0,
            "permissions": [
                {"feature": "POS", "can_read": 1, "can_create": 1, "can_update": 0, "can_delete": 0, "can_submit": 1},
                {"feature": "Sales", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1},
                {"feature": "Printer", "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1}
            ]
        }
    ]

    for profile in default_profiles:
        doc = frappe.get_doc("User Rights Profile", profile["profile_name"]) \
            if frappe.db.exists("User Rights Profile", profile["profile_name"]) else frappe.new_doc("User Rights Profile")
        
        doc.profile_name = profile["profile_name"]
        doc.is_admin = profile["is_admin"]

        # Add missing permissions only
        existing_features = [p.feature for p in doc.permissions]
        for perm in profile["permissions"]:
            if perm["feature"] not in existing_features:
                doc.append("permissions", perm)

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Profile created/updated: {profile['profile_name']}")
