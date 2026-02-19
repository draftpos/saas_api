import frappe

@frappe.whitelist(allow_guest=True)
def get_quotations(site_id, limit=20, start=0, status=None, modified_since=None):

    from frappe.utils.data import get_datetime
    if not modified_since:
        modified_since = "1970-01-01T00:00:00"

    filters = {}

    if status:
        status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        if status in status_map:
            filters["docstatus"] = status_map[status]

    # Always filter by modified
    filters["modified"] = [">=", get_datetime(modified_since)]

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
        "modified"
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

        # Fetch items for this quotation
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

    # Include site_id in response so WS server knows where to send
    return {"status": "success", "site": site_id, "quotations": quotations}
