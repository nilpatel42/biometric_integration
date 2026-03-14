// Copyright (c) 2026, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Leave Report"] = {
    filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1 // Makes the date field mandatory
        }
    ]
};
