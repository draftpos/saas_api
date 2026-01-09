frappe.query_reports["Custom Profit and Loss"] = {
        "filters": [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        }
    ],
    onload: function(report) {
        report.page.add_inner_button("Print PDF", function() {
            if (!report.data || report.data.length === 0) {
                frappe.msgprint("Please run the report first.");
                return;
            }

            // 👇 configurable variables
            const TABLE_WIDTH = "50%";   // half screen width
            const BODY_FONT_SIZE = "12px"; // all table body font size
            const HEADER_FONT_SIZE = "16px";
            const BOLD_FONT_SIZE = "15px";
            const INDENT_PX = 15;

            let html = `
                <html>
                <head>
                    <title>Profit & Loss Statement</title>
                    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 20px; 
                        }
                        h2 { 
                            text-align: center; 
                            margin-bottom: 10px; 
                            font-size: ${HEADER_FONT_SIZE};
                        }
                        table { 
                            width: ${TABLE_WIDTH} !important;
                            margin: 0 auto;
                            font-size: ${BODY_FONT_SIZE} !important;  /* force all rows smaller */
                        }
                        .big-bold { 
                            font-weight: bold; 
                            font-size: ${BOLD_FONT_SIZE} !important;  /* bold totals smaller */
                        }
                        .indent { padding-left: ${INDENT_PX}px; }
                        td.amount { text-align: right; }
                    </style>
                </head>
                <body>
                  <h1> ${frappe.defaults.get_default("company")} </h1>
                    <h2>Profit & Loss Statement</h2>
                    <table class="table table-bordered table-striped">
                        <thead class="table-light">
                            <tr>
                                <th style="width:70%;">Account</th>
                                <th style="width:30%;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            report.data.forEach(row => {
                let boldClass = row.account.toLowerCase().includes("profit") ? "big-bold" : "";
                let indentStyle = row.indent ? `padding-left:${row.indent * INDENT_PX}px;` : "";

                html += `
                    <tr>
                        <td class="${boldClass}" style="${indentStyle}">${row.account}</td>
                        <td class="amount ${boldClass}">${row.amount}</td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </body>
                </html>
            `;

            const w = window.open();
            w.document.write(html);
            w.document.close();
            w.print();
        });
    }
};
