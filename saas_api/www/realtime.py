import frappe
import json


def on_item_change(doc, method):
    """Emit real-time event when an Item is created or updated."""
    try:
        frappe.publish_realtime(
            event="pos:item_changed",
            message={
                "item_code": doc.item_code,
                "item_name": doc.item_name,
                "item_group": doc.item_group,
                "action": "created" if method == "after_insert" else "modified",
                "modified": str(doc.modified),
                "disabled": doc.disabled,
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_item_change")


def on_item_delete(doc, method):
    """Emit real-time event when an Item is deleted."""
    try:
        frappe.publish_realtime(
            event="pos:item_changed",
            message={
                "item_code": doc.item_code,
                "item_name": doc.item_name,
                "action": "deleted",
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_item_delete")


def on_price_change(doc, method):
    """Emit real-time event when an Item Price is created, updated, or deleted."""
    try:
        frappe.publish_realtime(
            event="pos:price_changed",
            message={
                "item_code": doc.item_code,
                "price_list": doc.price_list,
                "price_list_rate": doc.price_list_rate,
                "selling": doc.selling,
                "buying": doc.buying,
                "uom": doc.uom,
                "action": "deleted" if method == "on_trash" else "modified",
                "modified": str(doc.modified) if hasattr(doc, "modified") else None,
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_price_change")


def on_stock_change(doc, method):
    """Emit real-time event when a Stock Ledger Entry is created (stock movement)."""
    try:
        frappe.publish_realtime(
            event="pos:stock_changed",
            message={
                "item_code": doc.item_code,
                "warehouse": doc.warehouse,
                "actual_qty": doc.qty_after_transaction,
                "posting_date": str(doc.posting_date),
                "voucher_type": doc.voucher_type,
                "modified": str(doc.modified),
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_stock_change")


def on_invoice_status_change(doc, method):
    """Emit real-time event when a Sales Invoice status changes."""
    try:
        # Extract item codes from invoice items
        items = [{"item_code": item.item_code} for item in doc.items] if doc.items else []

        # Broadcast to all users so everyone sees stock updates
        frappe.publish_realtime(
            event="pos:invoice_changed",
            message={
                "name": doc.name,
                "customer": doc.customer,
                "grand_total": doc.grand_total,
                "docstatus": doc.docstatus,
                "status": doc.status,
                "action": method,
                "modified": str(doc.modified),
                "custom_sync_reference": doc.get("custom_sync_reference"),
                "owner": doc.owner,
                "items": items,
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_invoice_status_change")


def on_quotation_change(doc, method):
    """Emit real-time event when a Quotation changes."""
    try:
        # Extract item codes from quotation items
        items = [{"item_code": item.item_code} for item in doc.items] if doc.items else []

        frappe.publish_realtime(
            event="pos:quotation_changed",
            message={
                "name": doc.name,
                "docstatus": doc.docstatus,
                "grand_total": doc.grand_total,
                "action": "created" if method == "after_insert" else "modified",
                "modified": str(doc.modified),
                "items": items,
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_quotation_change")


def on_customer_change(doc, method):
    """Emit real-time event when a Customer is created or updated."""
    try:
        frappe.publish_realtime(
            event="pos:customer_changed",
            message={
                "name": doc.name,
                "customer_name": doc.customer_name,
                "customer_type": doc.customer_type,
                "default_price_list": doc.get("default_price_list"),
                "action": "created" if method == "after_insert" else "modified",
                "modified": str(doc.modified),
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_customer_change")


def on_permission_change(doc, method):
    """Emit real-time event when a User Permission changes."""
    try:
        frappe.publish_realtime(
            event="pos:permission_changed",
            message={
                "user": doc.user,
                "allow": doc.allow,
                "for_value": doc.for_value,
                "is_default": doc.is_default,
                "action": "deleted" if method == "on_trash" else "modified",
            },
            user=doc.user,
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Realtime: on_permission_change")
