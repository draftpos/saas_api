import frappe

def execute(filters=None):
    filters = filters or {}
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not company or not from_date or not to_date:
        frappe.throw("Please select Company, From Date, and To Date")
    def get_income_tax_expense():
        settings = frappe.get_single("profit and loss settings")

        # adjust fieldname to match your doctype
        return round(settings.income_tax_expense or 0, 2)



    revenue_total = get_total_by_parent_prefix("Direct Income", from_date, to_date, company)
    cost_of_sales_total = get_total_by_parent_prefix("Stock Expenses", from_date, to_date, company)
    other_income_total = get_total_by_parent_prefix("Indirect Income", from_date, to_date, company)
    distribution_cost = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Distribution Costs")
    administrative_expenses = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Administrative Expenses")
    other_operating_expenses = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Other Operating Expenses")
    operating_profit = revenue_total - cost_of_sales_total + other_income_total - distribution_cost - administrative_expenses - other_operating_expenses
    profit_before_financing_and_income_tax = operating_profit + 150  # needs to be calculated properly
    interest_expense_on_borrowings = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Interest Expense on Borrowings")
    interest_expense_on_long_term_provisions = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Interest Expense on Long-Term Provisions")
    profit_before_income_tax = profit_before_financing_and_income_tax - interest_expense_on_borrowings - interest_expense_on_long_term_provisions
    income_tax_expense = get_income_tax_expense() # needs to be calculated properly
    profit_from_continuing_operations = profit_before_income_tax - income_tax_expense
    loss_from_discontinued_operations = get_total_by_parent_prefix("Indirect Expenses", from_date, to_date, company, reporting_category="Loss from Discontinued Operations")
    profit_for_the_year = profit_from_continuing_operations - loss_from_discontinued_operations

    columns = [
        {"label": "Account", "fieldname": "account", "fieldtype": "Data"},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency"},

    ]

    data = [
        {"account": "Revenue", "amount": revenue_total, "profit_associates": 0, "investment_income": 0},
        {"account": "Cost of Sales", "amount": cost_of_sales_total, "profit_associates": 0, "investment_income": 0},
        {"account": "Gross Profit", "amount":round(revenue_total - abs(cost_of_sales_total), 2), "profit_associates": 0, "investment_income": 0},
        {"account": "Other Operating Income", "amount": other_income_total, "profit_associates": 0, "investment_income": 0},
        {"account": "Distribution Costs", "amount": distribution_cost, "profit_associates": 0, "investment_income": 0},
        {"account": "Administrative Expenses", "amount": administrative_expenses, "profit_associates": 0, "investment_income": 0},
        {"account": "Other Operating Expenses", "amount": other_operating_expenses, "profit_associates": 0, "investment_income": 0},
        {"account": "Operating Profit", "amount": operating_profit, "profit_associates": 50, "investment_income": 100},
         {"account": "Profit before financing and income tax", "amount": profit_before_financing_and_income_tax, "profit_associates": 50, "investment_income": 100},
        # {"account": "Share of Profit of Associates", "amount": 0, "profit_associates": 50, "investment_income": 0},
        # {"account": "Income from Investment Properties", "amount": 0, "profit_associates": 0, "investment_income": 100},
        {"account": "Interest expense on borrowings", "amount": interest_expense_on_borrowings, "profit_associates": 0, "investment_income": 0},
        {"account": "Interest expense on long-term provisions", "amount": interest_expense_on_long_term_provisions, "profit_associates": 0, "investment_income": 0},
        {"account": "Profit before income tax", "amount": profit_before_income_tax, "profit_associates": 50, "investment_income": 100},
        {"account": "Income tax expense", "amount": income_tax_expense, "profit_associates": 0, "investment_income": 0},
        {"account": "Profit from continuing operations", "amount": profit_from_continuing_operations, "profit_associates": 50, "investment_income": 100},
        {"account": "Loss from discontinued operations", "amount": loss_from_discontinued_operations, "profit_associates": 0, "investment_income": 0},
        {"account": "Profit for the year", "amount": profit_for_the_year, "profit_associates": 50, "investment_income": 100},
    ]

    return columns, data

def get_total_by_parent_prefix(prefix, from_date, to_date, company, reporting_category=None):
    """
    Sum all GL Entry balances for accounts whose parent_account starts with `prefix`.
    Handles both Income and Expense automatically.
    """
    # 1️⃣ Get accounts with parent starting with the prefix
    accounts = frappe.get_all(
        "Account",
        filters={
            "report_type": "Profit and Loss",
            "company": company,
            "parent_account": ["like", f"{prefix}%"],
            "reporting_category": reporting_category
        },
        pluck="name"
    )

    total = 0
    if accounts:
        placeholders = ", ".join(["%s"] * len(accounts))
        query = f"""
            SELECT SUM(
                CASE
                    WHEN a.root_type = 'Income' THEN gl.credit - gl.debit
                    WHEN a.root_type = 'Expense' THEN gl.debit - gl.credit
                    ELSE 0
                END
            ) as balance
            FROM `tabGL Entry` gl
            JOIN `tabAccount` a ON gl.account = a.name
            WHERE gl.account IN ({placeholders})
            AND gl.posting_date BETWEEN %s AND %s
        """
        params = tuple(accounts) + (from_date, to_date)
        result = frappe.db.sql(query, params, as_dict=True)
        total = result[0].balance or 0

    return round(total or 0, 2)
