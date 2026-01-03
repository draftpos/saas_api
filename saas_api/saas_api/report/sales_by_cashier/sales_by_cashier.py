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
    cashier = filters.get("cashier")  # expected to be email
    cost_center = filters.get("cost_center")

    conditions = ["si.docstatus = 1"]

    if from_date:
        conditions.append(f"si.posting_date >= '{from_date}'")
    if to_date:
        conditions.append(f"si.posting_date <= '{to_date}'")
    if cashier:
        conditions.append(f"u.email = '{cashier}'")
    if cost_center:
        conditions.append(f"si.cost_center = '{cost_center}'")

    condition_str = " AND ".join(conditions)

    sales = frappe.db.sql(
        f"""
        SELECT
            u.email AS cashier,
            COUNT(si.name) AS invoice_count,
            SUM(si.grand_total) AS total_sales
        FROM `tabSales Invoice` si
        INNER JOIN `tabUser` u ON u.name = si.owner
        WHERE {condition_str}
        GROUP BY u.email
        ORDER BY total_sales DESC
        """,
        as_dict=True
    )

    columns = [
        {
            "label": "Cashier Email",
            "fieldname": "cashier",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": "Invoices",
            "fieldname": "invoice_count",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Total Sales",
            "fieldname": "total_sales",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]

    return columns, sales
