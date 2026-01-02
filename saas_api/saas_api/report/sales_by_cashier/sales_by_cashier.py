# Copyright (c) 2026, chirovemunyaradzi@gmail.com and contributors
# For license information, please see license.txt

# import frappe

# sales_by_cashier.py (Script Report for Sales Invoice)


# sales_by_cashier.py

# sales_by_cashier.py (using created_by)

# sales_by_cashier.py

import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    cashier = filters.get("cashier")
    cost_center = filters.get("cost_center")

    # Base conditions: only submitted invoices
    conditions = ["si.docstatus = 1"]

    # Apply optional filters
    if from_date:
        conditions.append(f"si.posting_date >= '{from_date}'")
    if to_date:
        conditions.append(f"si.posting_date <= '{to_date}'")
    if cashier:
        conditions.append(f"si.owner = '{cashier}'")
    if cost_center:
        conditions.append(f"si.cost_center = '{cost_center}'")

    condition_str = " AND ".join(conditions)

    # Aggregate total sales per cashier (owner)
    sales = frappe.db.sql(
        f"""
        SELECT
            si.owner AS cashier,
            SUM(si.grand_total) AS total_sales
        FROM `tabSales Invoice` si
        WHERE {condition_str}
        GROUP BY si.owner
        ORDER BY total_sales DESC
        """,
        as_dict=True
    )

    # Report columns
    columns = [
        {"label": "Cashier", "fieldname": "cashier", "fieldtype": "Link", "options": "User", "width": 200},
        {"label": "Total Sales", "fieldname": "total_sales", "fieldtype": "Currency", "width": 150},
    ]

    return columns, sales

