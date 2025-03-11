// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

// frappe.query_reports["Biometric Monthly Report"] = {
//     filters: [
//         {
//             fieldname: "date_range",
//             label: __("Enter Your Date Range"),
//             fieldtype: "Date Range",
//         },
        // {
        //         fieldname: 'total_hours_hh_mm',
        //         label: 'Total Hours (HH:MM)',
        //         fieldtype: 'Check',
        // },
//     ],
//     onload: function(report) {
//         // Ensuring the default value of total_hours_hh_mm is 0 on load
//         report.set_filter_value("total_hours_hh_mm", 0);
//     }
// };

frappe.query_reports["Biometric Monthly Report"] = {
    filters: [
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            reqd: 1,
            on_change: function () {
                update_month_filter();
            },
        },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            reqd: 1,
            options: [],
        },
        // {
        //     fieldname: "employee",
        //     label: "Employee",
        //     fieldtype: "Link",
        //     options: "Employee",
        // },
        {
            fieldname: "total_hours_hh_mm",
            label: "Total Hours (HH:MM)",
            fieldtype: "Check",
        },
    ],

    onload: function () {
        frappe.call({
            method: "biometric_integration.biometric_integration.report.biometric_monthly_report.biometric_monthly_report.get_attendance_years",
            callback: function (r) {
                let year_filter = frappe.query_report.get_filter("year");
                year_filter.df.options = r.message;
                year_filter.df.default = new Date().getFullYear();
                year_filter.refresh();
                year_filter.set_input(year_filter.df.default);
                update_month_filter();
            },
        });
    },

    refresh: function () {
        report.set_filter_value("total_hours_hh_mm", 0);
    },
};

// Function to update the month filter based on the selected year
function update_month_filter() {
    let year_filter = frappe.query_report.get_filter_value("year");
    let current_year = new Date().getFullYear();
    let current_month = new Date().getMonth() + 1; // 0-based index

    let months = [
        { value: 1, label: "January" },
        { value: 2, label: "February" },
        { value: 3, label: "March" },
        { value: 4, label: "April" },
        { value: 5, label: "May" },
        { value: 6, label: "June" },
        { value: 7, label: "July" },
        { value: 8, label: "August" },
        { value: 9, label: "September" },
        { value: 10, label: "October" },
        { value: 11, label: "November" },
        { value: 12, label: "December" },
    ];

    let filtered_months = year_filter == current_year ? months.slice(0, current_month) : months;
    
    let month_filter = frappe.query_report.get_filter("month");
    month_filter.df.options = filtered_months;
    month_filter.df.default = filtered_months.length ? filtered_months[filtered_months.length - 1].value : null;
    month_filter.refresh();
    month_filter.set_input(month_filter.df.default);
}
