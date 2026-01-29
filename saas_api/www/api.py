import frappe
import json
import random
import string
from frappe.utils import escape_html,cstr
from frappe.auth import LoginManager
from frappe import throw, msgprint, _
from frappe.utils.background_jobs import enqueue
from frappe.model.mapper import get_mapped_doc
import requests
import random
import json
import base64
from .utils import create_response, check_user_has_company
from tzlocal import get_localzone
import pytz
from frappe.utils.data import flt
from frappe.utils import cint
import re
from frappe.utils import validate_email_address
from frappe.utils import flt, today, add_days,getdate

import os
from frappe.desk.query_report import run

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
        simple_code = data.get("simple_code")
        item_group = data.get("item_group")
        stock_uom = data.get("stock_uom")
        valuation_rate = float(data.get("valuation_rate", 0))
        is_stock_item = int(data.get("is_stock_item", 1))
        tax_template=data.get("tax_template")
        allow_sales=data.get("allow_sales")
        is_sales_item=int(data.get("is_sales_item", 1))

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
        # item_code = generate_item_code()
        item_code = data.get("item_code")
        min_tax_val = data.get("min_tax_val")
        max_tax_val = data.get("max_tax_val")
        tax_cat = data.get("tax_category")
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
		"custom_simple_code": simple_code,
        "item_group": item_group,
        "stock_uom": stock_uom,
        "is_stock_item": is_stock_item,
        "valuation_rate": valuation_rate,
        })
        item.is_sales_item = allow_sales

        # Add tax row if tax_template is provided
        if tax_template:
       
            template_doc = frappe.db.get_value("Item Tax Template", filters={}, order_by="creation asc" )
            first_template_name = frappe.db.get_value("Item Tax Template", 
                                             filters={}, 
                                             fieldname="name", 
                                             order_by="creation asc")
    
            if first_template_name:
                # 2. Fetch the actual Document object so you can see child tables (taxes)
                template_doc = frappe.get_doc("Item Tax Template", first_template_name)
                # 3. Extract values safely
                tax_rate_value = 0

                if template_doc.taxes:
                    tax_rate_value = template_doc.taxes[0].tax_rate or 0

                # 4. Append to the Item
                if not hasattr(item, "taxes"):
                    item.taxes = []

                item.append("taxes", {
                    "item_tax_template": template_doc.name,
                    "tax_category": tax_cat,
                    "valid_from": getattr(first_template_name, "valid_from", None),
                    "minimum_net_rate": min_tax_val, # Ensure these are defined in your API
                    "maximum_net_rate": max_tax_val
                })
            else:
                frappe.log_error("No Item Tax Templates found in system", "tax_template_logic")

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
        supplier_name = data.get("supplier_name")

        if not supplier_full_name or not supplier_name:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required field: supplier_full_name or supplier_name."
            }

        # Auto-generate supplier code
        
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

        if not group_name_for_item or not item_group_name:
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
    default_warehouse=None,
    customer_type="Individual",
    default_price_list=None,
    default_cost_center=None,

):
    try:
        if not default_price_list:
            frappe.throw("Price List is required for this customer.")
        if not default_cost_center:
            frappe.throw("Cost center is required for this customer.")
        if not default_warehouse:
            frappe.throw("Warehouse is required for this customer.")
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
            "custom_email_address": custom_email_address,
            "custom_warehouse": default_warehouse,
            "custom_cost_center": default_cost_center,
            "default_price_list": default_price_list,
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
def create_quotation(customer, items,reference_number,cost_center):
    try:
        if isinstance(items, str):
            items = frappe.parse_json(items)

        if not reference_number:
            frappe.throw("Reference Number is required.")

        if not cost_center:
            frappe.throw("Cost Center Number is required.")

        doc = frappe.new_doc("Quotation")
        doc.customer = customer
        doc.currency = "USD"
        doc.conversion_rate = 1
        doc.selling_price_list = "Standard Selling"
        doc.reference_number=reference_number
        doc.cost_center=cost_center

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
                "uom"
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
def get_quotations_by_date(date, limit=20, start=0, status=None,cost_center=None):
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
    if cost_center:
        filters["cost_center"] = cost_center
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
        "reference_number",
        "cost_center"
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
    try:
        # 1️⃣ Check if customer exists
        if not frappe.db.exists("Customer", customer):
            return {
                "status": "error",
                "message": f"Customer '{customer}' does not exist."
            }

        # 2️⃣ Get company from user permissions if not provided
        if not company:
            user = frappe.session.user

            permissions = frappe.get_all(
                "User Permission",
                filters={"user": user, "allow": "Company"},
                fields=["for_value", "is_default"]
            )

            default_company = None

            # Get the default company if marked as default
            for perm in permissions:
                if perm.get("is_default"):
                    default_company = perm.get("for_value")
                    break

            # If still nothing, pick the first company
            if not default_company and permissions:
                default_company = permissions[0].get("for_value")

            company = default_company

        if not company:
            return {
                "status": "error",
                "message": "No default Company found for the logged-in user."
            }

        # 3️⃣ Fetch balance
        result = frappe.db.sql("""
            SELECT SUM(debit) - SUM(credit)
            FROM `tabGL Entry`
            WHERE party_type = 'Customer'
            AND party = %s
            AND company = %s
        """, (customer, company))

        balance = result[0][0] or 0

        return {
            "status": "success",
            "customer": customer,
            "company": company,
            "balance": balance
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_customer_balance error")
        return {
            "status": "error",
            "message": str(e)
        }


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
    default_company = frappe.db.get_value("User Permission", {"user": user.name, "allow": "Company", "is_default": 1}, "for_value")
    user_rights_profile = None

    if user.user_rights_profile:
        profile = frappe.get_doc("User Rights Profile", user.user_rights_profile)

        user_rights_profile = {
        "name": profile.name,
        "profile_name": profile.profile_name,
        "is_admin": profile.is_admin,
        "permissions": [
            {
                "feature": p.feature,
                "can_read": p.can_read,
                "can_create": p.can_create,
                "can_update": p.can_update,
                "can_delete": p.can_delete,
                "can_submit": p.can_submit,
            }
            for p in profile.permissions
            ]
        }

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
        "company":default_company,
        "default_customer": default_customer,
        "user_rights": user_rights_profile,
        "customers": customers,
        "warehouse_items": warehouse_items,
        "time_zone": {"client": local_tz, "server": erpnext_tz},
        "role": user.get("role_select"),
        "pin": user.get("pin")
    }

    frappe.response["token_string"] = token_string
    frappe.response["token"] = base64.b64encode(token_string.encode("ascii")).decode("utf-8")
    return

# @frappe.whitelist()
# def create_sales_invoice():
#     invoice_data = frappe.local.form_dict
#     user = frappe.session.user

#     def get_user_default(fieldname):
#         value = invoice_data.get(fieldname)
#         if not value:
#             value = frappe.defaults.get_user_default(fieldname, user)
#         if not value:
#             value = frappe.db.get_value("User", user, fieldname)
#         if not value:
#             frappe.throw(f"{fieldname.replace('_',' ').title()} not provided and no default found for user")
#         return value

#     company = get_user_default("company")
#     customer = get_user_default("customer")
#     cost_center = get_user_default("cost_center")
#     warehouse = get_user_default("set_warehouse")
#     print(f"{company}, {customer}, {cost_center}, {warehouse}")

#     si_doc = frappe.get_doc({
#         "doctype": "Sales Invoice",
#         "customer": customer,
#         "company": company,
#         "currency": "USD",  # make sure this matches your default_currency or price list
#         "conversion_rate": 1.0,  # if USD to USD, else fetch correct rate
#         "set_warehouse": warehouse,
#         "cost_center": cost_center,
#         "update_stock": invoice_data.get("update_stock", 1),
#         "posting_date": invoice_data.get("posting_date") or frappe.utils.nowdate(),
#         "posting_time": invoice_data.get("posting_time") or frappe.utils.nowtime(),
#         # "custom_sales_reference": invoice_data.get("custom_sales_reference"),
#         "taxes_and_charges": invoice_data.get("taxes_and_charges"),
#         "payments": invoice_data.get("payments", []),
#         "items": [
#             {
#                 "item_name": item.get("item_name"),
#                 "item_code": item.get("item_code"),
#                 "rate": item.get("rate"),
#                 "qty": item.get("qty"),
#                 "cost_center": item.get("cost_center") or cost_center
#             } for item in invoice_data.get("items", [])
#         ]
#     })


#     si_doc.insert()
#     a=si_doc.submit()
#     return a
import frappe
import json
import frappe
import json
import traceback
import frappe
import json
import traceback


@frappe.whitelist(allow_guest=False)
def create_invoice(customer=None, items=None, posting_date=None,company=None, due_date=None,
                   cost_center=None,warehouse=None, update_stock=None, set_warehouse=None):
    """
    Create a Sales Invoice with safe default handling.
    If required fields are not provided, it tries to fetch from user defaults.
    """
    if not items:
        frappe.throw("Invoice items must be provided.")

    # Convert items if passed as string
    if isinstance(items, str):
        items = json.loads(items)
    user = frappe.session.user
    print(f"user: {user}")
   
    def get_user_default(fieldname):
        """
        Loop through User Permissions and return the default value
        for the given fieldname for the current user.
        """
        user = frappe.session.user

        # Get all user permissions for this user
        perms = frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": fieldname},
            fields=["for_value", "is_default"]
        )
        if not perms:
            frappe.throw(
                f"No user permissions found for '{fieldname}' for user {user}. "
                f"Please set a default in User Permissions."
            )

        # Find the one marked as default
        for p in perms:
            if p.get("is_default"):
                return p.get("for_value")

        # If none is default, just return the first one (optional)
        return perms[0].get("for_value")
    if not customer:
        customer = get_user_default("Customer")
    if not company:
        company = get_user_default("Company")
    if not cost_center:
       return "Cost Center is Mandatory"
    if not warehouse:
        warehouse = get_user_default("Warehouse")
    # Default posting/due dates
    if not posting_date:
        posting_date = frappe.utils.today()
    if not due_date:
        due_date = posting_date
    try:
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": company,
            "posting_date": posting_date,
            "due_date": due_date,
            "cost_center": cost_center,
            "update_stock": update_stock,
            "set_warehouse": warehouse,
            "items": items
        })
        invoice.insert()
        invoice.submit()
        frappe.db.commit()
        return {"status": "success", "invoice_name": invoice.name}
    except Exception as e:
        frappe.log_error(message=traceback.format_exc(), title="Create Invoice API Error")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_my_product_bundles():
    user = frappe.session.user
    frappe.log_error(f"User: {user}", "DEBUG get_my_product_bundles.")

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
            fields=["item_code", "rate","qty","uom"]
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

@frappe.whitelist(allow_guest=False)
def get_user_data(user=None):
    """
    Fetch user info along with defaults for warehouse, cost center, company, and linked customers/items.
    """
    if not user:
        user = frappe.session.user

    try:
        user_doc = frappe.get_doc("User", user)

        # Fetch default permissions
        default_warehouse = frappe.db.get_value(
            "User Permission",
            {"user": user_doc.name, "allow": "Warehouse", "is_default": 1},
            "for_value"
        )
        default_cost_center = frappe.db.get_value(
            "User Permission",
            {"user": user_doc.name, "allow": "Cost Center", "is_default": 1},
            "for_value"
        )
        default_customer = frappe.db.get_value(
            "User Permission",
            {"user": user_doc.name, "allow": "Customer", "is_default": 1},
            "for_value"
        )
        default_company = frappe.db.get_value(
            "User Permission",
            {"user": user_doc.name, "allow": "Company", "is_default": 1},
            "for_value"
        )
        # user_rights_profile = None

        if user_doc.user_rights_profile:
            profile = frappe.get_doc("User Rights Profile", user_doc.user_rights_profile)

            user_rights_profile = {
            "name": profile.name,
            "profile_name": profile.profile_name,
            "is_admin": profile.is_admin,
            "permissions": [
                {
                    "feature": p.feature,
                    "can_read": p.can_read,
                    "can_create": p.can_create,
                    "can_update": p.can_update,
                    "can_delete": p.can_delete,
                    "can_submit": p.can_submit,
                }
                for p in profile.permissions
                ]
            }
        # # Warehouse items
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
            customers = frappe.get_list(
                "Customer",
                filters={"custom_cost_center": default_cost_center},
                fields=["name", "customer_name", "customer_group", "territory", "custom_cost_center"],
                ignore_permissions=True
            )

        return {
            "status": "success",
            "user": {
                "first_name": user_doc.first_name,
                "last_name": user_doc.last_name,
                "gender": user_doc.gender,
                "birth_date": user_doc.birth_date,
                "mobile_no": user_doc.mobile_no,
                "username": user_doc.username,
                "full_name": user_doc.full_name,
                "email": user_doc.email,
                "warehouse": default_warehouse,
                "cost_center": default_cost_center,
                "company": default_company,
                "default_customer": default_customer,
                "customers": customers,
                "warehouse_items": warehouse_items,
                "role": user_doc.get("role_select") or "",
                "pin": user_doc.get("pin"),
                # "user_rights": user_rights_profile
                
            }
        }

    except Exception as e:
        frappe.log_error(message=traceback.format_exc(), title="Get User Data API Error")
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

import json
from frappe import _
import frappe
from frappe.utils.data import get_datetime, flt
from datetime import timedelta

@frappe.whitelist(allow_guest=True)
def get_sales_invoice_report():
    # Load JSON payload
    try:
        data = json.loads(frappe.request.data)
    except Exception:
        return {"message": {"status": "error", "message": "Invalid JSON payload"}}

    # Extract filters
    user = data.get("user")
    from_date = data.get("from_date")
    to_date = data.get("to_date")
    company = data.get("company")
    cost_center = data.get("cost_center")

    if not company:
        return {"message": {"status": "error", "message": "company is required"}}

    # Convert to datetime objects
    if from_date:
        from_date = get_datetime(from_date)
    if to_date:
        to_date = get_datetime(to_date)
        # Include the whole day
        to_date = to_date + timedelta(days=1) - timedelta(seconds=1)

    # Validate date range
    if from_date and to_date and from_date > to_date:
        return {"message": {"status": "error", "message": "from_date cannot be after to_date"}}

    # Build filters
    filters = {"company": company}

    if user:
        filters["owner"] = user

    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["creation"] = [">=", from_date]
    elif to_date:
        filters["creation"] = ["<=", to_date]

    if cost_center:
        filters["cost_center"] = cost_center

    # Fetch grand_total for invoices
    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["grand_total"]
    )

    total_count = len(invoices)
    total_amount = sum([flt(inv.get("grand_total") or 0) for inv in invoices])

    return {
        "message": {
            "status": "success",
            "total_count": total_count,
            "total_amount": total_amount
        }
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

@frappe.whitelist(allow_guest =True)
def get_pl_cost_center(company, cost_center=None):
    calculate_and_store_profit_and_loss()
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
            "gross_profit_loss",
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
        if not default_cost_center:
            return create_response("400", {"error": "No default Cost Center found for the user."})
        default_warehouse = frappe.db.get_value(
            "User Permission", 
            {"user": frappe.session.user, "allow": "Warehouse", "is_default": 1}, 
            "for_value"
        )
        if not default_warehouse:
            return create_response("400", {"error": "No default Warehouse found for the user."})
        # Fetch customers with default price list
        customers = frappe.get_all(
            "Customer",
            filters={
                "custom_cost_center": default_cost_center,
                "custom_warehouse": default_warehouse,
                "default_price_list": ["!=", ""]
            },
            fields=[
                "name",
                "customer_name",
                "customer_type",
                "custom_cost_center",
                "custom_warehouse",
                "gender",
                "customer_pos_id",
                "default_price_list"
            ]
        )
        for customer in customers:
            customer["balance"] = get_customer_balance(customer["name"])
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

@frappe.whitelist(allow_guest=True)
def edit_user(email, first_name=None, last_name=None, full_name=None, password=None, pin=None,phone_number=None,user_status=None,role_select=None):
    """
    API endpoint to edit an existing user
    
    Args:
        email: User's email address (required to identify the user)
        first_name: New first name (optional)
        last_name: New last name (optional)
        full_name: New full name (optional, will be constructed if not provided)
        password: New password (optional)
        pin: New PIN (optional)
    
    Returns:
        dict: Success message with updated user details
    """
    try:
        if not email:
            frappe.throw(_("Email is required"))

        user = frappe.get_doc("User", email)
        if not user:
            frappe.throw(_("User not found"))

        # Update fields if provided
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if last_name:
            user.last_name = last_name
        if full_name:
            user.full_name = full_name
        if phone_number:
            user.phone_number = phone_number
        if user_status:
            user.user_status = user_status
        if role_select:
            user.role_select = role_select
        elif first_name or last_name:
            # Construct full_name if not provided
            user.full_name = f"{user.first_name} {user.last_name}".strip()

        if password:
            # Optionally validate password strength
            validate_password(password)
            user.new_password = password

        if pin:
            user.pin = pin

        user.flags.ignore_permissions = True
        user.save()
        frappe.db.commit()

        create_response(
            status=200,
            message=_("User updated successfully"),
            data={
                "user": {
                    "email": user.email,
                    "full_name": user.full_name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "pin": getattr(user, "pin", None)
                }
            }
        )
        return

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Edit User Error")
        create_response(
            status=400,
            message=str(e)
        )
        return

@frappe.whitelist()
def get_users():
    """
    Returns a list of users that belong to the same company as the currently logged-in user.
    Now includes default cost center for each user.
    """
    try:
        # Ensure user is logged in
        if not frappe.session.user or frappe.session.user == "Guest":
            return {
                "status": 403,
                "message": _("Login required to fetch users"),
                "data": []
            }

        # Get current user's company from User Permission
        current_user_company = frappe.db.get_value(
            "User Permission",
            {"user": frappe.session.user, "allow": "Company"},
            "for_value"
        )

        if not current_user_company:
            return {
                "status": 404,
                "message": _("No company permission found for current user"),
                "data": []
            }

        # Get current user's cost center to filter other users
        current_user_cost_center = frappe.db.get_value(
            "User Permission",
            {"user": frappe.session.user, "allow": "Cost Center", "is_default": 1},
            "for_value"
        )

        # Get all users who have the same company in User Permissions
        users_with_same_company = frappe.get_all(
            "User Permission",
            filters={"allow": "Company", "for_value": current_user_company},
            fields=["user"]
        )

        user_names = [u.user for u in users_with_same_company if u.user]

        if not user_names:
            return {
                "status": 404,
                "message": _("No users found for this company"),
                "data": []
            }

        # Get user details
        users = frappe.get_all(
            "User",
            filters={"name": ["in", user_names]},
            fields=[
                "name", "email", "full_name", "first_name", "last_name", 
                "enabled", "user_type", "pin", "role_select"
            ]
        )

        # Enhance each user with additional data
        filtered_users = []
        for user in users:
            # Get user's default cost center
            user_cost_center = frappe.db.get_value(
                "User Permission",
                {"user": user["name"], "allow": "Cost Center", "is_default": 1},
                "for_value"
            )
            
            # Filter: only include users with matching cost center (or if current user has no cost center)
            if current_user_cost_center:
                if user_cost_center != current_user_cost_center:
                    continue  # Skip users from different cost centers
            
            # Get user's default warehouse
            user_warehouse = frappe.db.get_value(
                "User Permission",
                {"user": user["name"], "allow": "Warehouse", "is_default": 1},
                "for_value"
            )
            
            # Add cost center and warehouse to user data
            user["cost_center"] = user_cost_center
            user["warehouse"] = user_warehouse
            filtered_users.append(user)

        return {
            "status": 200,
            "message": _("Users fetched successfully"),
            "company": current_user_company,
            "current_user_cost_center": current_user_cost_center,
            "data": filtered_users
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Users Error")
        return {
            "status": 400,
            "message": str(e),
            "data": []
        }

def validate_password(password):
    if len(password) < 8:
        frappe.throw(_("Password must be at least 8 characters long"))
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        frappe.throw(_("Password must contain at least one uppercase letter"))
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        frappe.throw(_("Password must contain at least one lowercase letter"))
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        frappe.throw(_("Password must contain at least one number"))
    
    # Check for at least one special character (optional, comment out if not needed)
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     frappe.throw(_("Password must contain at least one special character"))


@frappe.whitelist(allow_guest=True)
def verify_email(email, verification_code):
    """
    API endpoint for email verification (optional)
    
    Args:
        email: User's email address
        verification_code: Verification code sent to email
    
    Returns:
        dict: Success message
    """
    try:
        # Implement your email verification logic here
        # This is a placeholder implementation
        
        user = frappe.get_doc("User", email)
        
        if not user:
            frappe.throw(_("User not found"))
        
        # Add your verification logic here
        # For example, check verification_code against stored code
        
        user.enabled = 1
        user.save(ignore_permissions=True)
        frappe.db.commit()
        
        create_response(
            status=200,
            message=_("Email verified successfully")
        )
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Email Verification Error")
        create_response(
            status=400,
            message=str(e)
        )

@frappe.whitelist(allow_guest=True)
def create_user(email, password, first_name, last_name=None, full_name=None, pin=None, phone_number=None):
    """
    API endpoint for user signup with admin-level permissions
    
    Args:
        email: User's email address
        password: User's password
        first_name: User's first name
        last_name: User's last name (optional)
        full_name: User's full name (optional)
        pin: User's pin
        phone_number: User's phone number
    
    Returns:
        dict: Success message with user details
    """
    try:
        # Validate inputs
        if not email:
            frappe.throw(_("Email is required"))
        if not password:
            frappe.throw(_("Password is required"))
        if not pin:
            frappe.throw(_("Pin is required"))
        if not first_name:
            frappe.throw(_("First name is required"))
        if not phone_number:
            frappe.throw(_("Phone number is required"))

        # Validate email format
        try:
            validate_email_address(email, throw=True)
        except Exception:
            frappe.throw(_("Please enter a valid email address"))

        # Check if user already exists
        if frappe.db.exists("User", email):
            frappe.throw(_("User with this email already exists"))

        # Validate password strength
        validate_password(password)

        # Construct full name
        if not full_name:
            full_name = f"{first_name} {last_name}" if last_name else first_name

        # Create user
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "full_name": full_name,
            "enabled": 1,
            "new_password": password,
            "send_welcome_email": 1,
            "user_type": "System User",
            "pin": pin,
            "phone_number": phone_number
        })

        user.flags.ignore_permissions = True
        user.insert()

        # Add all roles available in the system
        all_roles = [r.name for r in frappe.get_all("Role")]
        user.add_roles(*all_roles)

        frappe.db.commit()
        set_defaults_for_user(email)
        ensure_default_customer_for_user(email)

        create_response(
            status=200,
            message=_("User registered successfully with admin-level permissions"),
            data={
                "user": {
                    "email": email,
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "pin": pin
                }
            }
        )
        return

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Signup Error")
        create_response(
            status=400,
            message=str(e)
        )
        return


def ensure_default_customer_for_user(user):
    """
    Ensures a 'Default' Customer exists and assigns:
    - default customer for logged-in user
    - user permission for customer
    - default cost center into Customer.custom_cost_center
    """

    customer_name = "Default"
  
            # 1. Get default company from Global Defaults
    default_company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not default_company:
            return "No default company set in Global Defaults"

        # 3. Find Cost Center starting with 'Main'
    default_cost_center = frappe.db.get_value(
            "Cost Center",
            {"company": default_company, "cost_center_name": ["like", "Main%"]},
            "name"
        )
    main_warehouse = frappe.db.get_value(
            "Warehouse",
            {"company": default_company, "warehouse_name": ["like", "Stores%"]},
            "name"
        )

    # 2. Create or update Customer
    if not frappe.db.exists("Customer", customer_name):
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Individual",
            "customer_group": frappe.db.get_value(
                "Customer Group", {"is_group": 0}, "name"
            ) or "Individual",
            "territory": frappe.db.get_value(
                "Territory", {"is_group": 0}, "name"
            ) or "All Territories",
            "custom_cost_center": default_cost_center,
             "custom_warehouse": main_warehouse
        })
        customer.flags.ignore_permissions = True
        customer.insert()
    else:
        customer = frappe.get_doc("Customer", customer_name)

        # Ensure cost center is set if missing
        if default_cost_center and not customer.get("custom_cost_center"):
            customer.custom_cost_center = default_cost_center
            customer.flags.ignore_permissions = True
            customer.save()

    # 3. Set default customer for logged-in user
    frappe.defaults.set_user_default(
        "customer",
        customer.name,
        user=user
    )

    # 4. Add User Permission if missing
    if not frappe.db.exists(
        "User Permission",
        {
            "user": user,
            "allow": "Customer",
            "for_value": customer.name,
            "is_default": 1,
            "apply_to_all_doctypes": 1,
        }
    ):
        perm = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": "Customer",
            "for_value": customer.name,
            "apply_to_all_doctypes": 1,
            "is_default": 1
        })
        perm.flags.ignore_permissions = True
        perm.insert()




@frappe.whitelist()
def get_currencies_with_exchange_involvement():
    try:
        # All currencies appearing as FROM
        from_currencies = frappe.get_all(
            "Currency Exchange",
            pluck="from_currency"
        )

        # All currencies appearing as TO
        to_currencies = frappe.get_all(
            "Currency Exchange",
            pluck="to_currency"
        )

        # Merge unique currencies
        currencies = list(set(from_currencies + to_currencies))

        result = []

        for currency in currencies:
            # Get all rates where currency is the FROM
            rates = frappe.get_all(
                "Currency Exchange",
                filters={"from_currency": currency},
                fields=["to_currency", "exchange_rate", "date"]
            )

            # Format
            result.append({
                "currency": currency,
                "exchange_rates": [
                    {
                        "to": r["to_currency"],
                        "rate": r["exchange_rate"],
                        "date": r["date"]
                    }
                    for r in rates
                ]
            })
        create_response("200", {
            "count": len(result),
            "currencies": result
        })
        return
    except Exception as e:
        frappe.log_error(message=str(e), title="Error fetching involved currency rates")
        create_response("417", {"error": str(e)})
        return

@frappe.whitelist()
def add_fields_to_user_core_json():
    # Path to core User JSON in frappe app
    json_path = os.path.join(
        frappe.get_app_path("frappe", "core", "doctype", "user", "user.json")
    )

    # Load the existing User JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Define new fields
    new_fields = [
        {
            "fieldname": "pin",
            "label": "PIN",
            "fieldtype": "Data",
            "insert_after": "email",  # place after email field
            "hidden": 0,
            "reqd": 0
        },
        {
            "fieldname": "role_select",
            "label": "Role",
            "fieldtype": "Select",
            "options": "Admin\nCashier\nQuote\nQuote and Sales",
            "insert_after": "blue_field",
            "hidden": 0,
            "reqd": 0
        }
    ]

    # Add fields if they don't exist
    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]
    added = False
    for field in new_fields:
        if field["fieldname"] not in existing_fieldnames:
            data["fields"].append(field)
            added = True

    # Save back and reload only if we added something
    if added:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload User DocType
        frappe.reload_doc("core", "doctype", "user", force=True)
        frappe.clear_cache(doctype="User")
        return "Fields added successfully"
    return "Fields already exist"


@frappe.whitelist()
def add_custom_fields_to_quotation():
    # Path to Quotation DocType JSON
    module_path = frappe.get_module_path("selling")
    json_path = os.path.join(module_path, "doctype/quotation/quotation.json")

    # Load JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Fields to add
    fields_to_add = [
        {
            "fieldname": "cost_center",
            "label": "Cost Center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "insert_after": "customer",
            "hidden": 0,
            "reqd": 0
        },
        {
            "fieldname": "reference_number",
            "label": "Reference Number",
            "fieldtype": "Data",
            "insert_after": "cost_center",
            "hidden": 0,
            "reqd": 0
        }
    ]

    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]
    added = False

    for field in fields_to_add:
        if field["fieldname"] not in existing_fieldnames:
            data["fields"].append(field)
            added = True

    if added:
        # Save JSON back
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload DocType
        frappe.reload_doc("selling", "doctype", "quotation", force=True)
        frappe.clear_cache(doctype="Quotation")

        return "Custom fields added to Quotation successfully"

    return "Custom fields already exist"

@frappe.whitelist()
def add_supplier_full_name_field():
    # Path to Supplier DocType JSON
    module_path = frappe.get_module_path("buying")
    json_path = os.path.join(module_path, "doctype/supplier/supplier.json")

    # Load existing JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Define the new field
    new_field = {
        "fieldname": "supplier_full_name",
        "label": "Supplier Full Name",
        "fieldtype": "Data",
        "insert_after": "supplier",
        "hidden": 0,
        "reqd": 0
    }

    # Add if not exists
    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]
    if new_field["fieldname"] not in existing_fieldnames:
        data["fields"].append(new_field)

        # Save JSON back
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload Supplier DocType
        frappe.reload_doc("buying", "doctype", "supplier", force=True)
        frappe.clear_cache(doctype="Supplier")
        return "Supplier Full Name field added successfully"
    return "Supplier Full Name field already exists"


@frappe.whitelist()
def add_reference_number_to_sales_invoice():
    module_path = frappe.get_module_path("accounts")
    json_path = os.path.join(
        module_path,
        "doctype/sales_invoice/sales_invoice.json"
    )

    with open(json_path, "r") as f:
        data = json.load(f)

    new_field = {
        "fieldname": "reference_number",
        "label": "Reference Number",
        "fieldtype": "Data",
        "insert_after": "customer",
        "reqd": 1,
        "unique": 1
    }

    existing_fieldnames = [
        f["fieldname"] for f in data.get("fields", [])
    ]

    if new_field["fieldname"] not in existing_fieldnames:
        data["fields"].append(new_field)

        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        frappe.reload_doc("accounts", "doctype", "sales_invoice", force=True)
        frappe.clear_cache(doctype="Sales Invoice")

        return "Reference Number field added successfully"

    return "Reference Number field already exists"


@frappe.whitelist()
def add_reporting_category_to_accounts():
    # Get path to the Accounts doctype JSON
    module_path = frappe.get_module_path("accounts")
    json_path = os.path.join(module_path, "doctype", "account", "account.json")

    # Load existing JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    # Define the new field
    new_field = {
        "fieldname": "reporting_category",
        "label": "Reporting Category",
        "fieldtype": "Data",
        "insert_after": "account_name",  # or whichever field you want it after
        "reqd": 0,                       # not required
        "unique": 0
    }

    # Check if field already exists
    existing_fieldnames = [f["fieldname"] for f in data.get("fields", [])]

    if new_field["fieldname"] not in existing_fieldnames:
        data["fields"].append(new_field)

        # Write back JSON
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        # Reload DocType so changes take effect
        frappe.reload_doc("accounts", "doctype", "accounts", force=True)
        frappe.clear_cache(doctype="Accounts")

        return "Reporting Category field added successfully"

    return "Reporting Category field already exists"

def add_fields_on_install():
    add_fields_to_user_core_json()
    add_custom_fields_to_quotation()
    add_supplier_full_name_field()
    add_reference_number_to_sales_invoice()
    add_reporting_category_to_accounts()

@frappe.whitelist()
def set_defaults_for_user(user_email):
    try:
        # 1. Get default company from Global Defaults
        default_company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not default_company:
            return "No default company set in Global Defaults"

        # 2. Set Company User Permission
        set_user_permission(user_email, "Company", default_company)

        # 3. Find Cost Center starting with 'Main'
        main_cost_center = frappe.db.get_value(
            "Cost Center",
            {"company": default_company, "cost_center_name": ["like", "Main%"]},
            "name"
        )

        if main_cost_center:
            set_user_permission(user_email, "Cost Center", main_cost_center)

        # 4. Find Warehouse starting with 'Stores'
        main_warehouse = frappe.db.get_value(
            "Warehouse",
            {"company": default_company, "warehouse_name": ["like", "Stores%"]},
            "name"
        )

        if main_warehouse:
            set_user_permission(user_email, "Warehouse", main_warehouse)

        frappe.clear_cache(user_email)

        return f"Defaults set for {user_email} successfully"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Set User Defaults Failed")
        return f"Error: {str(e)}"


def set_user_permission(user, doctype, value):
    """Utility to create or update User Permission"""
    if not frappe.db.exists("User Permission", {"user": user, "allow": doctype}):
        # Create new permission
        doc = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": doctype,
            "for_value": value,
            "is_default": 1
        })
        doc.insert(ignore_permissions=True)
    else:
        # Update existing permission
        doc = frappe.get_doc("User Permission", 
            {"user": user, "allow": doctype}
        )
        doc.for_value = value
        doc.is_default = 1
        doc.save(ignore_permissions=True)




@frappe.whitelist()
def run_sales_by_cost_center(filters):
    filters = frappe.parse_json(filters)
    if not filters.get("company"):
        frappe.throw("Company is required")

    filters.setdefault("fiscal_year", "2026")
    filters.setdefault("period", "Monthly")

    result = run(
        report_name="sales data",
        filters=filters,
      
    )
    

    frappe.log_error(
        title="Sales By Cost Center Debug",
        message=frappe.as_json(result)
    )
    # DEBUG: prove report executed
    if not result.get("columns"):
        frappe.log_error(
    title="Sales By Cost Center Debug",
    message=frappe.as_json(result)
)

    return {
        "columns": result.get("columns"),
        "data": result.get("result"),
        "chart": result.get("chart"),
        "summary": result.get("report_summary")
    }



@frappe.whitelist()
def get_stock_reconciliation_with_items(from_date, to_date):
    reconciliations = frappe.get_all(
        "Stock Reconciliation",
        filters={
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 1
        },
        fields=[
            "name",
            "company",
            "posting_date",
            "purpose",
            "difference_amount",
            "cost_center"
        ]
    )

    if not reconciliations:
        return []

    names = [r.name for r in reconciliations]

    items = frappe.get_all(
        "Stock Reconciliation Item",
        filters={"parent": ["in", names]},
        fields=[
            "parent",
            "item_code",
            "warehouse",
            "qty",
            "current_qty",
            "quantity_difference",
            "valuation_rate",
            "amount",
            "amount_difference",
            "item_name"
        ]
    )

    items_map = {}
    for i in items:
        items_map.setdefault(i.parent, []).append(i)

    for r in reconciliations:
        r["items"] = items_map.get(r.name, [])

    return reconciliations

@frappe.whitelist()
def get_stock_purchases_with_items(from_date, to_date):
    purchase_receipts = frappe.get_all(
        "Purchase Invoice",
        filters={
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 1
        },
        fields=[
            "name",
            "supplier",
            "company",
            "posting_date",
            "total_qty",
            "grand_total",
            "net_total",
            "cost_center"
        ]
    )

    if not purchase_receipts:
        return []

    names = [pr.name for pr in purchase_receipts]

    items = frappe.get_all(
        "Purchase Invoice Item",
        filters={"parent": ["in", names]},
        fields=[
            "parent",
            "item_code",
            "item_name",
            "warehouse",
            "qty",
            "received_qty",
            "rate",
            "amount",
            "valuation_rate",
            "stock_uom"
        ]
    )

    items_map = {}
    for i in items:
        items_map.setdefault(i.parent, []).append(i)

    for pr in purchase_receipts:
        pr["items"] = items_map.get(pr.name, [])

    return purchase_receipts

@frappe.whitelist()
def get_sales_invoices(
    from_date=None,
    to_date=None,
    cost_center=None,
    user=None
):
    conditions = ["si.docstatus = 1"]
    values = {}

    if from_date:
        conditions.append("si.posting_date >= %(from_date)s")
        values["from_date"] = getdate(from_date)

    if to_date:
        conditions.append("si.posting_date <= %(to_date)s")
        values["to_date"] = getdate(to_date)

    if user:
        conditions.append("si.owner = %(user)s")
        values["user"] = user

    if cost_center:
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabSales Invoice Item` sii
                WHERE sii.parent = si.name
                AND sii.cost_center = %(cost_center)s
            )
        """)
        values["cost_center"] = cost_center

    invoices = frappe.db.sql(f"""
        SELECT
            si.name,
            si.posting_date,
            si.customer,
            si.grand_total,
            si.net_total,
            si.owner,
            si.company
        FROM `tabSales Invoice` si
        WHERE {" AND ".join(conditions)}
        ORDER BY si.posting_date DESC
    """, values, as_dict=True)

    if not invoices:
        return []

    invoice_names = [inv.name for inv in invoices]

    # ------------------------------------------------------------------
    # ITEMS
    # ------------------------------------------------------------------
    items = frappe.db.sql("""
        SELECT
            parent,
            item_code,
            item_name,
            qty,
            rate,
            amount,
            cost_center
        FROM `tabSales Invoice Item`
        WHERE parent IN %(parents)s
    """, {"parents": tuple(invoice_names)}, as_dict=True)

    items_map = {}
    for item in items:
        items_map.setdefault(item.parent, []).append(item)

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------
    payments = frappe.db.sql("""
    SELECT
        per.reference_name AS parent,
        pe.mode_of_payment,
        pe.paid_to AS paid_to_account,
        per.allocated_amount AS amount
    FROM `tabPayment Entry Reference` per
    JOIN `tabPayment Entry` pe ON pe.name = per.parent
    WHERE per.reference_name IN %(parents)s
""", {"parents": tuple(invoice_names)}, as_dict=True)



    payments_map = {}
    for payment in payments:
        payments_map.setdefault(payment.parent, []).append(payment)

    # ------------------------------------------------------------------
    # MERGE RESPONSE
    # ------------------------------------------------------------------
    for invoice in invoices:
        invoice["items"] = items_map.get(invoice.name, [])
        invoice["payments"] = payments_map.get(invoice.name, [])

    return invoices 

    #sakles


@frappe.whitelist()
def assign_user_permissions(user, company=None, warehouse=None, cost_center=None, customer=None):
    permissions = {
        "Company": company,
        "Warehouse": warehouse,
        "Cost Center": cost_center,
        "Customer": customer,
    }

    for doctype, value in permissions.items():
        if not value:
            continue

        if not frappe.db.exists(
            "User Permission",
            {
                "user": user,
                "allow": doctype,
                "for_value": value,
            }
        ):
            frappe.get_doc({
                "doctype": "User Permission",
                "user": user,
                "allow": doctype,
                "for_value": value,
                "apply_to_all_doctypes": 1,
                  "is_default":1
            }).insert(ignore_permissions=True)

    frappe.db.commit()



@frappe.whitelist()
def get_missing_user_permissions(user):
    required = {
        "Company": None,
        "Warehouse": None,
        "Cost Center": None,
        "Customer": None,
    }

    existing = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": ["in", list(required.keys())],
        },
        fields=["allow", "for_value"],
    )

    for perm in existing:
        required.pop(perm.allow, None)

    return list(required.keys())
