import frappe

def create_default_user_rights():
    """Create default User Rights Profiles and Permissions if they don't exist"""
    
    # Define the default profiles
    default_profiles = [
        {
            "profile_name": "Admin Rights",
            "is_admin": 1,
            "permissions": [
                {"feature": f, "can_read": 1, "can_create": 1, "can_update": 1, "can_delete": 1, "can_submit": 1}
                for f in ["Dashboard", "POS", "Quotations", "Sales", "Products",
                          "Stock Management", "Payment Entries", "Reports", "Settings", "Printer"]
            ]
        },
        {
            "profile_name": "Basic User Rights",
            "is_admin": 0,
            "permissions": [
                {"feature": f, "can_read": 1}  # read-only
                for f in ["Dashboard", "POS", "Quotations", "Sales", "Products",
                          "Stock Management", "Payment Entries", "Reports", "Settings", "Printer"]
            ]
        }
    ]
    
    for profile in default_profiles:
        # Check if profile exists
        if frappe.db.exists("User Rights Profile", profile["profile_name"]):
            doc = frappe.get_doc("User Rights Profile", profile["profile_name"])
            print(f"Profile already exists: {profile['profile_name']}")
        else:
            doc = frappe.get_doc({
                "doctype": "User Rights Profile",
                "profile_name": profile["profile_name"],
                "is_admin": profile["is_admin"],
                "permissions": []
            })
            print(f"Creating profile: {profile['profile_name']}")
        
        # Ensure all permissions exist
        existing_features = [p.feature for p in doc.permissions]
        for perm in profile["permissions"]:
            if perm["feature"] not in existing_features:
                doc.append("permissions", perm)
        
        doc.save(ignore_permissions=True)
        frappe.db.commit()
