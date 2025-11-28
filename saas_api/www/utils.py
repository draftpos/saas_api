import frappe
from frappe import _

def create_response(status,message,data=None):
    frappe.local.response.http_status_code = status
    frappe.local.response.message = message
    if data is not None:
        frappe.local.response.data = data


def check_user_has_company():
    """
    Check if current user has a company registration and is assigned to it
    
    Returns:
        dict: Company registration data if exists and user is assigned
    
    Raises:
        frappe.exceptions.ValidationError: If user doesn't have company registration or is not assigned
        frappe.exceptions.PermissionError: If user is not logged in
    """
    user = frappe.session.user
    
    if user == "Guest":
        frappe.throw(_("Please login to access this resource"), frappe.PermissionError)
    
    company_registration = frappe.db.get_value(
        "Company Registration",
        {"user_created": user},
        ["name", "organization_name", "status", "company"],
        as_dict=True
    )
    
    if not company_registration:
        frappe.throw(_("You do not have a company registration. Please register your company first."), frappe.ValidationError)
    
    # Check if user is assigned to the company (via User Permission)
    if company_registration.get("company"):
        is_assigned = frappe.db.exists("User Permission", {
            "user": user,
            "allow": "Company",
            "for_value": company_registration.company
        })
        
        if not is_assigned:
            frappe.throw(_("You are not assigned to this company. Please contact administrator."), frappe.ValidationError)
    
    return company_registration


def require_company_registration(func):
    """
    Decorator to check if user has company registration before executing function
    
    Usage:
        @frappe.whitelist()
        @require_company_registration
        def my_function():
            # Your code here
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            check_user_has_company()
            return func(*args, **kwargs)
        except frappe.ValidationError as e:
            create_response(
                status=403,
                message=str(e)
            )
            return
        except frappe.PermissionError as e:
            create_response(
                status=401,
                message=str(e)
            )
            return
    return wrapper