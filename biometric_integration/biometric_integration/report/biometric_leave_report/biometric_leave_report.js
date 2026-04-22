// Copyright (c) 2026, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Leave Report"] = {
    onload: function(report) {
        report.report_settings.auto_run = false;
    },

    filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 0
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            reqd: 0,
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            default: new Date().toLocaleString('en', { month: 'long' }),
            reqd: 0,
            depends_on: "eval:doc.employee"
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            options: (function() {
                const y = new Date().getFullYear();
                return `\n${y - 1}\n${y}`;
            })(),
            default: String(new Date().getFullYear()),
            reqd: 0,
            depends_on: "eval:doc.employee"
        }
    ]
};