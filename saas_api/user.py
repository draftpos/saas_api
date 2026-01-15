import frappe

def assign_admin_profile():
    # Use 'Admin Rights' to match the name in your create_default_user_rights script
    target_profile = "Admin Rights" 
    
    if frappe.db.exists("User Rights Profile", target_profile):
        # We use db_set instead of .save() because db_set bypasses 
        # Link Validation, preventing the install-app crash.
        frappe.db.set_value("User", "Administrator", "user_rights_profile", target_profile)
        
        # Ensure the change is written to the database immediately
        frappe.db.commit()
    else:
        # We log a warning instead of throwing an error so the install finishes
        frappe.logger().warning(f"Assignment skipped: Profile '{target_profile}' not found.")