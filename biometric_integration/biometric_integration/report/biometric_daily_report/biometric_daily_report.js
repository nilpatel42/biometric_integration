// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Daily Report"] = {
    filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1 // Makes the date field mandatory
        }
    ]
};
