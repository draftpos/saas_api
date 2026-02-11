# Copyright (c) 2026, chirovemunyaradzi@gmail.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe 
from frappe.utils import flt


class UserRightsProfile(Document):
        
    def before_save(self):
        """
        Create an Item called 'Food Tax' if:
        1. food_tax field is not empty
        2. food_tax is the same as tourism_tax
        """
        if self.food_tax:
            # Check if the item already exists to avoid duplicates
            if not frappe.db.exists("Item", "Food Tax"):
                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": "Food Tax",
                    "item_name": "Food Tax",
                    "item_group": "Services",  # Adjust item group as needed
                    "is_stock_item": 0,
                    "standard_rate": flt(self.food_tax),
                    "default_unit_of_measure": "Nos"  # Adjust UOM if needed
                })
                item.insert(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint("Food Tax item created successfully.")
        if self.tourism_tax:
            # Check if the item already exists to avoid duplicates
            if not frappe.db.exists("Item", "Tourism Tax"):
                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": "Tourism Tax",
                    "item_name": "Tourism Tax",
                    "item_group": "Services",  # Adjust item group as needed
                    "is_stock_item": 0,
                    "standard_rate": flt(self.tourism_tax),
                    "default_unit_of_measure": "Nos"  # Adjust UOM if needed
                })
                item.insert(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint("Tourism Tax item created successfully.")	
