import frappe
import json
import random
import string


def generate_item_code():
    """Generate a unique item code: HA-XXXXX-### style with incrementing numbers"""
    prefix = "HA-"
    random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))

    # Find last item_code starting with HA-
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

    # Get the last supplier created
    last_supplier = frappe.db.sql("""
        SELECT supplier_name FROM `tabSupplier`
        WHERE supplier_name LIKE %s
        ORDER BY creation DESC LIMIT 1
    """, (f"{prefix}%-%%",))
    print(f"---------------------{last_supplier}")

    if last_supplier:
        last_code = last_supplier[0][0]
        try:
            last_num = int(last_code.split("-")[-1])
        except:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1

    # Generate new random 5-letter prefix
    random_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    new_code = f"{prefix}{random_letters}-{next_num:03d}"

    # Ensure uniqueness
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

        # Validate required fields
        if not item_name or not item_group or not stock_uom:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required fields: item_name, item_group, stock_uom."
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
            "simple_code":simple_code,
            "item_group": item_group,
            "stock_uom": stock_uom,
            "is_stock_item": is_stock_item,
            "valuation_rate": valuation_rate
        })
        item.flags.ignore_permissions = True
        item.insert()
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "status": "success",
            "message": f"Item '{item_name}' created successfully.",
            "item_code": item_code
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
        supplier_name = data.get("supplier_name")
        supplier_type = data.get("supplier_type", "Company")
        supplier_group = data.get("supplier_group", "All Supplier Groups")
        supplier_full_name=data.get("supplier_full_name")

        if not supplier_full_name:
            frappe.local.response["http_status_code"] = 400
            return {
                "status": "error",
                "message": "Missing required field: supplier_name."
            }

        # Auto-generate supplier code
        supplier_name = generate_supplier_code()

        # Ensure Supplier Group exists
        if not frappe.db.exists("Supplier Group", supplier_group):
            group = frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": supplier_group,
                "parent_supplier_group": "All Supplier Groups"
            })
            group.flags.ignore_permissions = True
            group.insert()

        # Create Supplier
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_full_name": supplier_full_name,
            "supplier_type": supplier_type,
            "supplier_group": supplier_group
        })
        supplier.flags.ignore_permissions = True
        supplier.insert()
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "status": "success",
            "message": f"Supplier '{supplier_name}' created successfully.",
            "supplier_full_name": supplier_full_name
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
