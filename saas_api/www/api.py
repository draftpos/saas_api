import frappe
import json
import random
import string
from frappe.utils import escape_html,cstr
from frappe.auth import LoginManager
from frappe import throw, msgprint, _
from frappe.utils.background_jobs import enqueue
import requests
import random
import json
import base64
from .utils import create_response, check_user_has_company
from tzlocal import get_localzone
import pytz
from frappe.utils.data import flt
from frappe.utils import cint
from frappe.utils import flt, today, add_days


def generate_item_code():
    """Generate a unique item code: HA-XXXXX-### style with incrementing numbers"""
    prefix = "HA-"
    random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))

    last_item = frappe.db.sql("""
        SELECT item_code FROM `tabItem` 
        WHERE item_code LIKE %s
        ORDER BY creation DESC LIMIT 1
    """, (f"{prefix}%-%%",))  # match HA-ANYLETTERS-NUM

    if last_item:
        last_code = last_item[0][0]
        try:
            last_num = int(last_code.split("-")[-1])
        except:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1

    new_code = f"{prefix}{random_letters}-{next_num:03d}"

    # Double-check uniqueness
    while frappe.db.exists("Item", new_code):
        next_num += 1
        new_code = f"{prefix}{random_letters}-{next_num:03d}"

    return new_code
def generate_supplier_code():
    """Generate a unique supplier code: HS-XXXXX-### style with sequential last 3 digits"""
    prefix = "HS-"

    last_supplier = frappe.db.sql("""
        SELECT supplier_name FROM `tabSupplier`
        WHERE supplier_name LIKE %s
        ORDER BY creation DESC LIMIT 1
    """, (f"{prefix}%-%%",))

    if last_supplier:
        last_code = last_supplier[0][0]
        try:
            last_num = int(last_code.split("-")[-1])
        except:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1

    random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    new_code = f"{prefix}{random_letters}-{next_num:03d}"

    while frappe.db.exists("Supplier", {"supplier_code": new_code}):
        next_num += 1
        random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        new_code = f"{prefix}{random_letters}-{next_num:03d}"

    return new_code



@frappe.whitelist(allow_guest=True)
def create_item():
    """POST: Create Item with auto-generated item_code (Guest-safe, no Stock Entry)"""
    try:
        data = json.loads(frappe.request.data or "{}")

        item_name = data.get("item_name")
        # simple_code = data.get("simple_code")
        item_group = data.get("item_group")
        stock_uom = data.get("stock_uom")
        valuation_rate = float(data.get("valuation_rate", 0))
        is_stock_item = int(data.get("is_stock_item", 1))
        tax_template=data.get("tax_template")
        allow_sales=data.get("allow_sales")

        # Validate required fields
        if not item_name or not item_group or not stock_uom:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required fields: item_name, item_group, stock_uom."
            }

        # Check if user already has an item with the same simple_code
        # existing_item = frappe.db.exists(
        #     "Item",
        #     {
        #         "simple_code": simple_code,
        #         "owner": frappe.session.user
        #     }
        # )
        # if existing_item:
        #     frappe.local.response["http_status_code"] = 409  # Conflict
        #     return {
        #         "status": "error",
        #         "message": f"An item with simple_code '{simple_code}' already exists for this Company."
        #     }

        # Auto-generate item code
        item_code = generate_item_code()

        # Ensure Item Group exists
        if not frappe.db.exists("Item Group", item_group):
            group = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": item_group,
                "parent_item_group": "All Item Groups"
            })
            group.flags.ignore_permissions = True
            group.insert()

        # Ensure UOM exists
        if not frappe.db.exists("UOM", stock_uom):
            uom = frappe.get_doc({
                "doctype": "UOM",
                "uom_name": stock_uom
            })
            uom.flags.ignore_permissions = True
            uom.insert()

    # Create Item without setting opening_stock (avoids Stock Entry)
        item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_code,
        "item_name": item_name,
#"simple_code": simple_code,
        "item_group": item_group,
        "stock_uom": stock_uom,
        "is_stock_item": is_stock_item,
        "valuation_rate": valuation_rate,
        })
        item.is_sales_item = allow_sales

        # Add tax row if tax_template is provided
        if tax_template:
            if frappe.db.exists("Item Tax Template", tax_template):
                template_doc = frappe.get_doc("Item Tax Template", tax_template)

                # Default values
                tax_rate_value = 0
                tax_category = getattr(template_doc, "tax_category", "")

                # If the template has tax rates, get the first one
                if hasattr(template_doc, "taxes") and template_doc.taxes:
                    tax_rate_value = template_doc.taxes[0].tax_rate or 0

                if not hasattr(item, "taxes"):
                    item.taxes = []

                # Append tax row to the Item’s taxes child table
                item.append("taxes", {
                    "item_tax_template": template_doc.name,
                    "tax_category": tax_category,
                    "valid_from": getattr(template_doc, "valid_from", None),
                    "minimum_net_rate": tax_rate_value,
                    "maximum_net_rate": tax_rate_value
                })
            else:
                frappe.log_error(f"Item Tax Template '{tax_template}' not found", "create_item API")


        item.flags.ignore_permissions = True
        item.insert()
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "status": "success",
            "message": f"Item '{item_name}' created successfully.",
            "item_code": item.item_code,
            "item_name": item_name,
            # "simple_code": simple_code
        }

    except Exception as e:
        frappe.log_error(title="Item API Error", message=frappe.get_traceback())
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def create_supplier():
    """POST: Create Supplier with auto-generated supplier_code"""
    try:
        data = json.loads(frappe.request.data or "{}")
        supplier_full_name=data.get("supplier_full_name")

        if not supplier_full_name:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required field: supplier_full_name."
            }

        # Auto-generate supplier code
        supplier_name = generate_supplier_code()
        # Create Supplier
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_full_name": supplier_full_name,
            "supplier_type": "Company",
            "supplier_group": "All Supplier Groups"
        })
        supplier.flags.ignore_permissions = True
        supplier.insert()
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "status": "success",
            "message": f"Supplier '{supplier_name}' created successfully.",
            "supplier_full_name": supplier_full_name,
        }

    except Exception as e:
        frappe.log_error(title="Supplier API Error", message=frappe.get_traceback())
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}

def generate_item_group_code():
    """Generate a unique item group code: IG-XXXXX-### style"""
    prefix = "HA-"

    # Get last item group created
    last_group = frappe.db.sql("""
        SELECT item_group_name FROM `tabItem Group`
        WHERE item_group_name LIKE %s
        ORDER BY creation DESC LIMIT 1
    """, (f"{prefix}%-%%",))

    if last_group:
        last_code = last_group[0][0]
        try:
            last_num = int(last_code.split("-")[-1])
        except:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1

    # Generate random 5-letter prefix
    random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    new_code = f"{prefix}{random_letters}-{next_num:03d}"

    # Ensure uniqueness
    while frappe.db.exists("Item Group", {"item_group_name": new_code}):
        next_num += 1
        random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        new_code = f"{prefix}{random_letters}-{next_num:03d}"

    return new_code


@frappe.whitelist(allow_guest=True)
def create_item_group():
    """POST: Create Item Group with auto-generated _item_group_name"""
    try:
        data = json.loads(frappe.request.data or "{}")
        item_group_name = data.get("item_group_name")
        group_name_for_item=data.get("group_name_for_item")
        parent_item_group = data.get("parent_item_group", "All Item Groups")

        if not group_name_for_item:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required field: group_name_for_item"
            }

        # Auto-generate code
        item_group_name = generate_item_group_code()

        # Create Item Group
        group = frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": item_group_name,
            "group_name_for_item": group_name_for_item,
            "parent_item_group": parent_item_group
        })
        group.flags.ignore_permissions = True
        group.insert()
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "status": "success",
            "message": f"Item Group '{group_name_for_item}' created successfully.",
            "group_name_for_item": group_name_for_item,
            "res":group
        }
    except Exception as e:
        frappe.log_error(title="Item Group API Error", message=frappe.get_traceback())
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def create_customer(
    customer_name,
    custom_trade_name=None,
    custom_customer_tin=None,
    custom_customer_vat=None,
    custom_customer_address=None,
    custom_telephone_number=None,
    custom_province=None,
    custom_street=None,
    custom_city=None,
    custom_house_no=None,
    custom_email_address=None,
    customer_type="Individual",
    price_list=None  # New parameter
):
    try:
        if not price_list:
            frappe.throw("Price List is required for this customer.")
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": customer_type,
            "custom_trade_name": custom_trade_name,
            "custom_customer_tin": custom_customer_tin,
            "custom_customer_vat": custom_customer_vat,
            "custom_customer_address": custom_customer_address,
            "custom_telephone_number": custom_telephone_number,
            "custom_province": custom_province,
            "custom_street": custom_street,
            "custom_city": custom_city,
            "custom_house_no": custom_house_no,
            "custom_email_address": custom_email_address
        })

        # Ignore permission restrictions
        customer.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.logger().info(f"✅ Customer created: {customer.name}")
        return {"customer_id": customer.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Customer Error")
        return {"error": str(e)}

@frappe.whitelist()
def create_quotation(customer, items,reference_number):
    try:
        if isinstance(items, str):
            items = frappe.parse_json(items)

        if not reference_number:
            frappe.throw("Reference Number is required.")


        doc = frappe.new_doc("Quotation")
        doc.customer = customer
        doc.currency = "USD"
        doc.conversion_rate = 1
        doc.selling_price_list = "Standard Selling"
        doc.reference_number=reference_number

        for it in items:
            doc.append("items", {
                "item_code": it["item_code"],
                "qty": it.get("qty", 1),
                "rate": it.get("rate", 0),
                "uom": "Nos"
            })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        try:
            doc.submit()
            frappe.db.commit()
        except Exception as e:
            return {
                "status": "draft_created",
                "quotation": doc.name,
                "submit_error": str(e)
            }

        return {
            "status": "success",
            "quotation": doc.name
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "API Create Quotation Failed")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def cancel_quotation(quotation_name):
    """
    Cancel a submitted Quotation.
    Args:
        quotation_name (str): The Quotation name, e.g. SAL-QTN-2025-00001
    """

    try:
        doc = frappe.get_doc("Quotation", quotation_name)

        if doc.docstatus == 1:
            doc.db_set("docstatus", 2)  # 2 = cancelled
            frappe.db.commit()
            return {"status": "success", "message": f"Quotation {quotation_name} cancelled."}

        # Already draft
        elif doc.docstatus == 0:
            return {"status": "not_submitted", "message": f"Quotation {quotation_name} is still a draft."}

        else:
            return {"status": "already_cancelled", "message": f"Quotation {quotation_name} is already cancelled."}

    except frappe.DoesNotExistError:
        return {"status": "error", "message": f"Quotation {quotation_name} does not exist."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Cancel Quotation Failed")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def update_quotation(quotation_name, customer=None, items=None, transaction_date=None, valid_till=None, terms=None):
    try:
        doc = frappe.get_doc("Quotation", quotation_name)

        if doc.docstatus == 2:
            return {"status": "error", "message": f"Quotation {quotation_name} is cancelled and cannot be modified."}

        # If submitted, cancel first
        if doc.docstatus == 1:
            doc.cancel()
            frappe.db.commit()
        if customer:
            doc.customer = customer
        if transaction_date:
            doc.transaction_date = transaction_date
        if valid_till:
            doc.valid_till = valid_till
        if terms:
            doc.tc_name = terms

        if items:
            if isinstance(items, str):
                items = frappe.parse_json(items)
            doc.set("items", [])
            for it in items:
                doc.append("items", {
                    "item_code": it.get("item_code"),
                    "qty": it.get("qty", 1),
                    "rate": it.get("rate"),
                    "uom": "Nos"
                })

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        if doc.docstatus == 1:
            doc.submit()
            frappe.db.commit()

        return {"status": "success", "message": f"Quotation {quotation_name} updated.", "quotation": doc.name}

    except frappe.DoesNotExistError:
        return {"status": "error", "message": f"Quotation {quotation_name} does not exist."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Quotation Failed")
        return {"status": "error", "message": str(e)}


from frappe.model.mapper import get_mapped_doc
@frappe.whitelist()
def create_invoice_from_quotation(quotation_name):
    invoice = get_mapped_doc(
        "Quotation",
        quotation_name,
        {
            "Quotation": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "customer_name": "customer",
                    "grand_total": "grand_total"
                }
            },
            "Quotation Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_code": "item_code",
                    "qty": "qty",
                    "rate": "rate"
                }
            }
        },
        ignore_permissions=True  
    )
    invoice.insert()
    frappe.db.commit()
    return invoice.name


@frappe.whitelist()
def get_quotations(limit=20, start=0, status=None):
    """
    Get list of quotations for the logged-in user's company.
    Admin sees all.
    Returns quotation + item details (item name, simple code, qty, rate, amount).
    """

    user = frappe.session.user
    filters = {}

    if user != "Administrator":
        company = frappe.get_value(
            "User Permission",
            {"user": user, "allow": "Company"},
            "for_value"
        )
        if not company:
            return {"status": "error", "message": "User has no company assigned."}

        filters["company"] = company
    if status:
        status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        if status in status_map:
            filters["docstatus"] = status_map[status]

    meta_fields = [f.fieldname for f in frappe.get_meta("Quotation").fields]
    if "customer_name" in meta_fields:
        customer_field = "customer_name"
    elif "party_name" in meta_fields:
        customer_field = "party_name"
    else:
        customer_field = None

    fields_to_fetch = [
        "name",
        "transaction_date",
        "valid_till",
        "grand_total",
        "docstatus",
        "company",
        "reference_number"
    ]

    if customer_field:
        fields_to_fetch.append(customer_field)
    quotations = frappe.get_all(
        "Quotation",
        filters=filters,
        fields=fields_to_fetch,
        limit_start=start,
        limit_page_length=limit,
        order_by="creation desc"
    )
    status_dict = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

    for q in quotations:
        q["status"] = status_dict.get(q["docstatus"], "Unknown")
        if customer_field:
            q["customer"] = q.pop(customer_field)

        # -----------------------------
        # FETCH ITEMS FOR THIS QUOTATION
        # -----------------------------
        q["items"] = frappe.get_all(
            "Quotation Item",
            filters={"parent": q["name"]},
            fields=[
                "item_code",
                "item_name",
                "description",
                "qty",
                "rate",
                "amount",
                "uom",
                "simple_code"
            ],
            order_by="idx asc",
        )

    return {"status": "success", "quotations": quotations}

import frappe
from frappe import _


@frappe.whitelist(allow_guest=False)
def upload_company_logo():
    """
    Upload a logo to a company.
    Expects multipart/form-data with:
        - company_name
        - file
    """
    company_name = frappe.form_dict.get("company_name")
    upload_file = frappe.request.files.get("file")  

    if not company_name:
        frappe.throw(_("Company name is required"))

    if not upload_file:
        frappe.throw(_("File is required"))

    if not frappe.db.exists("Company", company_name):
        frappe.throw(_("Company {0} does not exist").format(company_name))
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": upload_file.filename,
        "attached_to_doctype": "Company",
        "attached_to_name": company_name,
        "content": upload_file.read()
    }).insert()
    frappe.db.set_value("Company", company_name, "custom_logo", file_doc.file_url)
    frappe.db.commit()

    return {
        "status": "success",
        "file_url": file_doc.file_url
    }

@frappe.whitelist()
def get_quotations_by_date(date, limit=20, start=0, status=None):
    """
    Get list of quotations for the logged-in user's company filtered by a specific date.
    """
    user = frappe.session.user
    filters = {}

    if user != "Administrator":
        company = frappe.get_value(
            "User Permission",
            {"user": user, "allow": "Company"},
            "for_value"
        )
        if not company:
            return {"status": "error", "message": "User has no company assigned."}

        filters["company"] = company
    if date:
        filters["transaction_date"] = date

    if status:
        status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        if status in status_map:
            filters["docstatus"] = status_map[status]
    meta_fields = [f.fieldname for f in frappe.get_meta("Quotation").fields]
    if "customer_name" in meta_fields:
        customer_field = "customer_name"
    elif "party_name" in meta_fields:
        customer_field = "party_name"
    else:
        customer_field = None

    fields_to_fetch = [
        "name",
        "transaction_date",
        "valid_till",
        "grand_total",
        "docstatus",
        "company",
        "reference_number"
    ]

    if customer_field:
        fields_to_fetch.append(customer_field)

    quotations = frappe.get_all(
        "Quotation",
        filters=filters,
        fields=fields_to_fetch,
        limit_start=start,
        limit_page_length=limit,
        order_by="creation desc"
    )

    status_dict = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
    for q in quotations:
        q["status"] = status_dict.get(q["docstatus"], "Unknown")
        if customer_field:
            q["customer"] = q.pop(customer_field)

        # -----------------------------
        # FETCH ITEMS FOR THIS QUOTATION
        # -----------------------------
        q["items"] = frappe.get_all(
            "Quotation Item",
            filters={"parent": q["name"]},
            fields=[
                "item_code",
                "item_name",
                "description",
                "qty",
                "rate",
                "amount",
                "uom",
                "simple_code"
            ],
            order_by="idx asc",
        )
    return {"status": "success", "quotations": quotations}
    
@frappe.whitelist()
def get_account():
    try:
        # Get logged-in user
        user = frappe.session.user

        # Try to get employee linked to user
        employee_company = frappe.db.get_value(
            "Employee",
            {"user_id": user},
            "company"
        )

        # Fallback: Use system default company
        if not employee_company:
            employee_company = frappe.db.get_single_value("Global Defaults", "default_company")

        # Fetch accounts for that company only
        accounts = frappe.get_all(
            "Account",
            filters={
                "company": employee_company,
                "account_type": ["in", ["Cash", "Bank"]],
                "is_group": 0
            },
            fields=[
                "name",
                "account_name",
                "account_number",
                "company",
                "parent_account",
                "account_type",
                "account_currency"
            ]
        )

        return {"status ": 200, "accounts":accounts}
        return

    except Exception as e:
        create_response("417", {"error": str(e)})
        frappe.log_error(message=str(e), title="Error fetching account data")
        return

@frappe.whitelist()
def get_customer_balance(customer, company=None):
    # 1️⃣ Check if customer exists
    if not frappe.db.exists("Customer", customer):
        frappe.throw(f"Customer '{customer}' does not exist.")

    # 2️⃣ Get company from user permissions if not provided
    if not company:
        user = frappe.session.user
        permissions = frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": "Company"},
            fields=["for_value", "is_default"]
        )

        default_company = None
        for perm in permissions:
            if perm.get("is_default"):
                default_company = perm.get("for_value")
                break

        if not default_company and permissions:
            default_company = permissions[0].get("for_value")

        company = default_company

    if not company:
        frappe.throw("No default Company found for the logged-in user.")

    # 3️⃣ Fetch balance
    result = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit)
        FROM `tabGL Entry`
        WHERE party_type = 'Customer'
          AND party = %s
          AND company = %s
    """, (customer, company))

    # If no GL entries exist, result[0][0] is None
    balance = result[0][0]
    if balance is None:
        return (f"No GL entries found for customer '{customer}' in company '{company}'.")

    return balance

def generate_keys(user):
    api_secret = api_key = ''
    if not user.api_key and not user.api_secret:
        api_secret = frappe.generate_hash(length=15)
        # if api key is not set generate api key
        api_key = frappe.generate_hash(length=15)
        user.api_key = api_key
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
    else:
        api_secret = user.get_password('api_secret')
        api_key = user.get('api_key')
    return {"api_secret": api_secret, "api_key": api_key}

@frappe.whitelist(allow_guest=True)
def login(usr, pwd, timezone):

    local_tz = str(get_localzone())
    erpnext_tz = frappe.utils.get_system_timezone()

    if timezone != erpnext_tz:
        frappe.local.response.http_status_code = 400
        frappe.local.response["message"] = f"Timezone mismatch. Your timezone is {timezone}, but system requires {erpnext_tz}"
        return

    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response.http_status_code = 422
        frappe.local.response["message"] = "Invalid Email or Password"
        return

    user = frappe.get_doc('User', frappe.session.user)
    api_generate = generate_keys(user)
    token_string = f"{api_generate['api_key']}:{api_generate['api_secret']}"

    # Get default permissions
    default_warehouse = frappe.db.get_value("User Permission", {"user": user.name, "allow": "Warehouse", "is_default": 1}, "for_value")
    default_cost_center = frappe.db.get_value("User Permission", {"user": user.name, "allow": "Cost Center", "is_default": 1}, "for_value")
    default_customer = frappe.db.get_value("User Permission", {"user": user.name, "allow": "Customer", "is_default": 1}, "for_value")

    # Warehouse items
    warehouse_items = []
    if default_warehouse:
        warehouse_items = frappe.db.sql("""
            SELECT 
                item.item_code,
                item.item_name,
                item.description,
                item.stock_uom,
                bin.actual_qty,
                bin.projected_qty
            FROM `tabItem` item
            LEFT JOIN `tabBin` bin ON bin.item_code = item.item_code 
            WHERE bin.warehouse = %s
        """, default_warehouse, as_dict=1)

    # Customers linked to cost center
    customers = []
    if default_cost_center:
        customers = frappe.get_list("Customer",
            filters={"custom_cost_center": default_cost_center},
            fields=["name", "customer_name", "customer_group", "territory", "custom_cost_center"],
            ignore_permissions=True
        )

    frappe.response["user"] = {
        "first_name": escape_html(user.first_name or ""),
        "last_name": escape_html(user.last_name or ""),
        "gender": escape_html(user.gender or "") or "",
        "birth_date": user.birth_date or "",
        "mobile_no": user.mobile_no or "",
        "username": user.username or "",
        "full_name": user.full_name or "",
        "email": user.email or "",
        "warehouse": default_warehouse,
        "cost_center": default_cost_center,
        "default_customer": default_customer,
        "customers": customers,
        "warehouse_items": warehouse_items,
        "time_zone": {"client": local_tz, "server": erpnext_tz},
        "role": user.get("role_select") or "",
        "pin": user.get("pin")
    }

    frappe.response["token_string"] = token_string
    frappe.response["token"] = base64.b64encode(token_string.encode("ascii")).decode("utf-8")
    return


@frappe.whitelist()
def create_sales_invoice():
    invoice_data = frappe.local.form_dict

    try:
        # Helper function to get default for user if not provided
        def get_user_default(user, fieldname):
            value = invoice_data.get(fieldname)
            if not value:
                # Try from User Defaults
                value = frappe.defaults.get_user_default(fieldname, user)
            if not value:
                # Try from User Doc fields directly
                value = frappe.db.get_value("User", user, fieldname)
            if not value:
                frappe.throw(f"{fieldname.replace('_',' ').title()} not provided and no default found for user")
            return value

        user = frappe.session.user

        # Resolve missing fields from defaults
        company = get_user_default(user, "company")
        cost_center = get_user_default(user, "cost_center")
        warehouse = get_user_default(user, "set_warehouse")
        customer = get_user_default(user, "customer")

        si_doc = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": company,
            "set_warehouse": warehouse,
            "cost_center": cost_center,
            "update_stock": invoice_data.get("update_stock", 1),
            "posting_date": invoice_data.get("posting_date") or frappe.utils.nowdate(),
            "posting_time": invoice_data.get("posting_time") or frappe.utils.nowtime(),
            "custom_sales_reference": invoice_data.get("custom_sales_reference"),
            "taxes_and_charges": invoice_data.get("taxes_and_charges"),
            "payments": invoice_data.get("payments", []),
            "items": [
                {
                    "item_name": item.get("item_name"),
                    "item_code": item.get("item_code"),
                    "rate": item.get("rate"),
                    "qty": item.get("qty"),
                    "cost_center": item.get("cost_center") or cost_center
                } for item in invoice_data.get("items", [])
            ]
        })

        # Insert ignoring permissions
        si_doc.insert()

        # Temporarily ignore permissions for submission
        frappe.flags.ignore_permissions = True
        si_doc.submit()
        frappe.flags.ignore_permissions = False

        # Reload to get updated docstatus
        si_doc.reload()

        return {
            "status": "success",
            "message": "Sales Invoice created and submitted successfully",
            "invoice_name": si_doc.name,
            "docstatus": si_doc.docstatus,
            "created_by": si_doc.owner,
            "created_on": si_doc.creation
        }

    except frappe.ValidationError as ve:
        return {"status": "error", "message": str(ve)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sales Invoice Creation Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_my_product_bundles():
    user = frappe.session.user
    frappe.log_error(f"User: {user}", "DEBUG get_my_product_bundles")

    if user == "Guest":
        return {"error": "You must be logged in"}

    bundles = frappe.get_all(
        "Product Bundle",
        filters={"owner": user},
        fields=["name", "new_item_code", "description", "creation"]
    )

    for b in bundles:
        items = frappe.get_all(
            "Product Bundle Item",
            filters={"parent": b.name},
            fields=["item_code", "item_name","qty"]
        )
        b["items"] = items

    frappe.log_error(f"Bundles found: {len(bundles)}", "DEBUG get_my_product_bundles")
    return bundles
 
@frappe.whitelist()
def payment_entry(party, amount, mode_of_payment, reference_doctype=None, reference_name=None):
    if not party:
        frappe.throw("Party (customer) is required.")

    invoice = None

    # Use reference from payload if given
    if reference_doctype and reference_name:
        invoice = frappe.get_doc(reference_doctype, reference_name)

    # Otherwise, get last outstanding invoice
    if not invoice:
        last_invoice = frappe.get_list(
            "Sales Invoice",
            filters={"customer": party, "outstanding_amount": (">", 0)},
            fields=["name", "outstanding_amount"],
            order_by="posting_date desc, creation desc",
            limit=1
        )

        if last_invoice:
            invoice = frappe.get_doc("Sales Invoice", last_invoice[0].name)

    # Create Payment Entry
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = party
    pe.paid_amount = amount
    pe.received_amount = amount
    pe.mode_of_payment = mode_of_payment

    # ⚡ Ignore permissions for everything below
    frappe.flags.ignore_permissions = True

    # Setup accounts etc.
    pe.setup_party_account_field()
    pe.set_missing_values()

    # Allocate to invoice if found
    if invoice:
        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "allocated_amount": min(amount, invoice.outstanding_amount)
        })

    # Submit the Payment Entry
    pe.submit()

    # Reset ignore permissions
    frappe.flags.ignore_permissions = False

    return {
        "payment_entry": pe.name,
        "credited_invoice": invoice.name if invoice else None,
        "type": "Advance" if not invoice else "Invoice Payment"
    }


@frappe.whitelist(allow_guest=True)
def get_user_data():
    """
    Accepts JSON with { "user": "email@example.com" } 
    and returns the same data normally returned after login.
    """
    try:
        data = json.loads(frappe.request.data or "{}")
        usr = data.get("user")
        timezone = data.get("timezone") or str(get_localzone())

        if not usr:
            frappe.local.response["http_status_code"] = 400
            return {"status": "error", "message": "Missing 'user' in request JSON"}

        # Validate user exists
        if not frappe.db.exists("User", usr):
            frappe.local.response["http_status_code"] = 404
            return {"status": "error", "message": f"User '{usr}' not found"}

        user = frappe.get_doc("User", usr)

        # Just generate static API token for demonstration
        api_generate = generate_keys(user)
        token_string = f"{api_generate['api_key']}:{api_generate['api_secret']}"

        # Get user permissions for warehouse and cost center
        warehouses = frappe.get_list("User Permission",
            filters={"user": user.name, "allow": "Warehouse"},
            pluck="for_value", ignore_permissions=True
        )
        cost_centers = frappe.get_list("User Permission",
            filters={"user": user.name, "allow": "Cost Center"},
            pluck="for_value", ignore_permissions=True
        )

        default_warehouse = frappe.db.get_value("User Permission",
            {"user": user.name, "allow": "Warehouse", "is_default": 1}, "for_value")
        default_cost_center = frappe.db.get_value("User Permission",
            {"user": user.name, "allow": "Cost Center", "is_default": 1}, "for_value")
        default_customer = frappe.db.get_value("User Permission",
            {"user": user.name, "allow": "Customer", "is_default": 1}, "for_value")

        # Get warehouse items
        warehouse_items = []
        if default_warehouse:
            warehouse_items = frappe.db.sql("""
                SELECT 
                    item.item_code,
                    item.item_name,
                    item.description,
                    item.stock_uom,
                    bin.actual_qty,
                    bin.projected_qty
                FROM `tabItem` item
                LEFT JOIN `tabBin` bin ON bin.item_code = item.item_code 
                WHERE bin.warehouse = %s
            """, default_warehouse, as_dict=1)

        # Customers linked to cost center
        customers = []
        if default_cost_center:
            customers = frappe.get_list("Customer",
                filters={"custom_cost_center": default_cost_center},
                fields=["name", "customer_name", "customer_group", "territory", "custom_cost_center"],
                ignore_permissions=True
            )

        # Company registration
        company_registration = frappe.db.sql("""
            SELECT name, organization_name, status, company, industry, country, city, 
                company_status, subscription, days_left
            FROM `tabCompany Registration`
            WHERE user_created = %(user)s
            OR name IN (
                SELECT reference_name
                FROM `tabToDo`
                WHERE reference_type = 'Company Registration'
                AND allocated_to = %(user)s
            )
        """, {"user": usr}, as_dict=True)

        has_company = bool(company_registration)
        company_message = None if has_company else "You need to register your company to access all features."

        frappe.response["user"] = {
            "first_name": escape_html(user.first_name or ""),
            "last_name": escape_html(user.last_name or ""),
            "gender": escape_html(user.gender or "") or "",
            "birth_date": user.birth_date or "",
            "mobile_no": user.mobile_no or "",
            "username": user.username or "",
            "full_name": user.full_name or "",
            "email": user.email or "",
            "warehouse": default_warehouse,
            "cost_center": default_cost_center,
            "default_customer": default_customer,
            "customers": customers,
            "warehouse_items": warehouse_items,
            "company": company_registration[0].get("company") if company_registration else None,
            "has_company_registration": has_company,
            "company_registration": company_registration[0] if company_registration else None,
            "company_message": company_message,
            "role": user.get("role_select") or "",
            "pin": user.get("pin")
        }

        frappe.response["token_string"] = token_string
        frappe.response["token"] = base64.b64encode(token_string.encode("ascii")).decode("utf-8")

        if not has_company:
            frappe.response["help"] = {
                "endpoint": "/api/method/havano_company.apis.company.register_company",
                "required_fields": ["user_email", "organization_name"],
                "message": "Please register your company to access all features",
                "example": {
                    "user_email": user.email,
                    "organization_name": "Your Company Name",
                    "industry": "Retail grocery"
                }
            }

        return frappe.response

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_user_data API Error")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def default_cost_center(company):
    """
    Returns the first Cost Center for a given company
    whose name starts with 'Main' (case-insensitive).
    """
    if not company:
        return None

    # Fetch all cost centers for this company
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={"company": company},
        fields=["name"],
    )

    # Find the first one that starts with 'Main'
    for cc in cost_centers:
        cc_name = cc["name"]
        if cc_name.upper().startswith("MAIN"):
            print(f"-------------------Matched: {cc_name}")
            return cc_name

    return None


@frappe.whitelist(allow_guest=True)
def get_sales_invoice_report():
    """
    Returns a summary of Sales Invoices with optional filters.
    Expects JSON payload with:
    {
        "created_by": "user@example.com",
        "from_date": "2025-01-01",
        "to_date": "2025-01-31",
        "company": "Saas Company (Demo)"
    }
    """

    try:
        data = json.loads(frappe.request.data)  # Parse JSON payload
    except Exception:
        return {"status": "error", "message": "Invalid JSON payload"}

    created_by = data.get("created_by")
    from_date = data.get("from_date")
    to_date = data.get("to_date")
    company = data.get("company")

    if not company:
        return {"status": "error", "message": "company is required"}

    filters = {}

    if created_by:
        filters["owner"] = created_by
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["creation"] = [">=", from_date]
    elif to_date:
        filters["creation"] = ["<=", to_date]
    filters["company"] = company

    # Fetch invoices
    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["name", "customer", "grand_total", "creation", "owner", "company"],
        order_by="creation desc"
    )

    total_count = len(invoices)
    total_amount = sum([flt(inv.get("grand_total") or 0) for inv in invoices])

    return {
        "status": "success",
        "total_count": total_count,
        "total_amount": total_amount,
    }
@frappe.whitelist(allow_guest=True)
def calculate_and_store_profit_and_loss():
    # Default dates: yesterday to today
    to_date = today()
    from_date = add_days(to_date, -1)

    # Get all companies
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        # Get all cost centers for this company
        cost_centers = frappe.get_all("Cost Center", filters={"company": company}, pluck="name")
        cost_centers.append(None)  # Include total for the whole company

        for cc in cost_centers:
            filters = ["company=%s"]
            values = [company]

            filters.append("posting_date >= %s")
            values.append(from_date)
            filters.append("posting_date <= %s")
            values.append(to_date)

            if cc:
                filters.append("cost_center=%s")
                values.append(cc)

            where_clause = " AND ".join(filters)

            # Total Income
            income_total = frappe.db.sql(f"""
                SELECT SUM(credit - debit) as total_income
                FROM `tabGL Entry`
                WHERE {where_clause} AND account IN (
                    SELECT name FROM `tabAccount` WHERE root_type='Income'
                )
            """, tuple(values), as_dict=1)[0]["total_income"] or 0

            # Total Expense
            expense_total = frappe.db.sql(f"""
                SELECT SUM(debit - credit) as total_expense
                FROM `tabGL Entry`
                WHERE {where_clause} AND account IN (
                    SELECT name FROM `tabAccount` WHERE root_type='Expense'
                )
            """, tuple(values), as_dict=1)[0]["total_expense"] or 0

            gross_profit_loss = flt(income_total) - flt(expense_total)

            # Create / insert record in Profit and Loss per Cost Center
            pl_doc = frappe.get_doc({
                "doctype": "Profit and Loss per Cost Center",
                "company": company,
                "cost_center": cc or "All",
                "income": flt(income_total),
                "expense": flt(expense_total),
                "gross_profit__loss": gross_profit_loss,
                "date": to_date
            })

            pl_doc.flags.ignore_permissions = True
            pl_doc.insert()
            frappe.db.commit()

    return {"status": "success", "message": "Profit and Loss per Cost Center calculated and stored."}

@frappe.whitelist()
def get_pl_cost_center(company, cost_center=None):
    """
    Fetch Profit and Loss values from `Profit and Loss per Cost Center` doctype.
    Filters by company and optional cost center.
    """

    if not company:
        frappe.throw("Company is required")

    filters = {"company": company}

    if cost_center:
        filters["cost_center"] = cost_center

    doc = frappe.get_all(
        "Profit and Loss per Cost Center",
        filters=filters,
        fields=[
            "company",
            "cost_center",
            "income",
            "expense",
            "gross_profit__loss",
            "date"
        ],
        limit_page_length=1,
    )

    if not doc:
        return {"error": "No data found for given filters"}

    return doc[0]


@frappe.whitelist()
def get_sales_invoice(user=None):
    try:
        final_invoice = []
        # Return all invoices if user is Administrator, else filter by user
        filters = {} if user == "Administrator" else {"owner": user} if user else {}
        
        sales_invoice_list = frappe.get_all("Sales Invoice", 
            filters=filters,
            fields=[
                "name", "customer", "company", "customer_name",
                "posting_date", "posting_time", "due_date",
                "total_qty", "total", "total_taxes_and_charges",
                "grand_total", "owner", "modified_by"
            ])
        
        for invoice in sales_invoice_list:
            items = frappe.get_all("Sales Invoice Item", 
                filters={"parent": invoice.name},
                fields=["item_name", "qty", "rate", "amount"])
                
            invoice = {
                "name": invoice.name,
                "customer": invoice.customer,
                "company": invoice.company,
                "customer_name": invoice.customer_name,
                "posting_date": invoice.posting_date,
                "posting_time": invoice.posting_time,
                "due_date": invoice.due_date,
                "items": items,
                "total_qty": invoice.total_qty,
                "total": invoice.total,
                "total_taxes_and_charges": invoice.total_taxes_and_charges,
                "grand_total": invoice.grand_total,
                "created_by": invoice.owner,
                "last_modified_by": invoice.modified_by
            }
            final_invoice.append(invoice)
            
        create_response("200", final_invoice)
        return
    except Exception as e:
        create_response("417", {"error": str(e)})
        frappe.log_error(message=str(e), title="Error fetching sales invoice data")
        return


@frappe.whitelist()
def get_customers():
    try:
        # Get default cost center for the logged-in user
        default_cost_center = frappe.db.get_value(
            "User Permission", 
            {"user": frappe.session.user, "allow": "Cost Center", "is_default": 1}, 
            "for_value"
        )       

        # Fetch customer details with a default price list
        customers = frappe.get_all(
            "Customer",
            filters={
                "custom_cost_center": default_cost_center,
                "default_price_list": ["!=", ""]
            },
            fields=[
                "customer_name",
                "customer_type",
                "custom_cost_center",
                "custom_warehouse",
                "gender",
                "customer_pos_id",
                "default_price_list"
            ]
        )

        # Fetch item prices for each customer
        for customer in customers:
            customer["items"] = frappe.get_all(
                "Item Price",
                filters={"price_list": customer["default_price_list"]},
                fields=["item_code", "item_name", "price_list_rate"]
            )

        create_response("200", customers)
        return

    except Exception as e:
        create_response("417", {"error": str(e)})
        frappe.log_error(message=str(e), title="Error fetching customer data")
        return


@frappe.whitelist()
def get_my_product_bundles():
    user = frappe.session.user
    frappe.log_error(f"User: {user}", "DEBUG get_my_product_bundles")

    if user == "Guest":
        return {"error": "You must be logged in"}

    bundles = frappe.get_all(
        "Product Bundle",
        filters={"owner": user},
        fields=["name", "new_item_code", "description", "creation"]
    )

    for b in bundles:
        items = frappe.get_all(
            "Product Bundle Item",
            filters={"parent": b.name},
            fields=["item_code", "item_name","qty"]
        )
        b["items"] = items

    frappe.log_error(f"Bundles found: {len(bundles)}", "DEBUG get_my_product_bundles")
    return bundles