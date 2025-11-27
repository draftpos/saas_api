import frappe
import json
import random
import string

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

        # Validate required fields
        if not item_name or not item_group or not stock_uom:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required fields: item_name, item_group, stock_uom."
            }

        # Check if user already has an item with the same simple_code
        existing_item = frappe.db.exists(
            "Item",
            {
                "simple_code": simple_code,
                "owner": frappe.session.user
            }
        )
        if existing_item:
            frappe.local.response["http_status_code"] = 409  # Conflict
            return {
                "status": "error",
                "message": f"An item with simple_code '{simple_code}' already exists for this Company."
            }

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
        "simple_code": simple_code,
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
            "simple_code": simple_code
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
