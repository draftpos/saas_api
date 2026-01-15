import frappe

def create_default_user_rights():
    """Create default User Rights Profiles safely on install"""

    if not frappe.db.table_exists("tabUser Rights Profile"):
        return

    default_profiles = [
        {
            "profile_name": "Admin Rights", # NOTE: Ensure this name matches what you use in assign_admin_profile
            "is_admin": 1,
            "permissions": [
                {
                    "feature": f, "can_read": 1, "can_create": 1, "can_update": 1, 
                    "can_delete": 1, "can_submit": 1
                } for f in ["Dashboard", "POS", "Quotations", "Sales", "Products",
                            "Stock Management", "Payment Entries", "Reports", "Settings", "Printer"]
            ]
        },
        # ... your Basic User Rights ...
    ]

    for profile in default_profiles:
        if not frappe.db.exists("User Rights Profile", profile["profile_name"]):
            doc = frappe.get_doc({
                "doctype": "User Rights Profile",
                "profile_name": profile["profile_name"],
                "is_admin": profile["is_admin"],
                "permissions": profile["permissions"]
            })
            doc.insert(ignore_permissions=True)
    
    # CRITICAL: Commit changes so the next hook can see the new records
    frappe.db.commit()