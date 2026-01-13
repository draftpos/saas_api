import frappe

def execute():
    # Admin Profile
    if not frappe.db.exists("User Rights Profile", "Super Admin"):
        admin_profile = frappe.get_doc({
            "doctype": "User Rights Profile",
            "profile_name": "Admin",
            "is_admin": 1,
            "permissions": [
                {
                    "feature": "Dashboard", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                {
                    "feature": "POS", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                {
                    "feature": "Quotations", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                                {
                    "feature": "Printer", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                                {
                    "feature": "Settings", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                                {
                    "feature": "Sales", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },

                {
                    "feature": "Payement Entries", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                {
                    "feature": "Stock Management", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },                
                {
                    "feature": "Reports", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                }, 
                 {
                    "feature": "Products", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },               

                # Add all other features here...
            ]
        })
        admin_profile.insert(ignore_permissions=True)
        frappe.db.commit()
    
    # Cashier Profile
    if not frappe.db.exists("User Rights Profile", "Cashier"):
        cashier_profile = frappe.get_doc({
            "doctype": "User Rights Profile",
            "profile_name": "Cashier",
            "is_admin": 0,
            "permissions": [
                {
                    "feature": "POS", "can_read": 1, "can_create": 1,
                    "can_update": 0, "can_delete": 0, "can_submit": 1
                },
                                {
                    "feature": "Sales", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },
                {
                    "feature": "Printer", "can_read": 1, "can_create": 1,
                    "can_update": 1, "can_delete": 1, "can_submit": 1
                },               
                # Add other features as required
            ]
        })
        cashier_profile.insert(ignore_permissions=True)
        frappe.db.commit()
