// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Monthly Report"] = {
    filters: [
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            options: ["2025"],  // Provide at least one default option
            reqd: 1,
            on_change: function() {
                update_month_filter();
            }
        },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            reqd: 1,
            options: [
                { value: 1, label: "January" },
                { value: 2, label: "February" },
                { value: 3, label: "March" },
                { value: 4, label: "April" },
                { value: 5, label: "May" }
            ],  // Default options
        },
        {
            fieldname: "total_hours_hh_mm",
            label: "Total Hours (HH:MM)",
            fieldtype: "Check",
        },
    ],

    onload: function(report) {
        // Set default for total_hours_hh_mm
        report.set_filter_value("total_hours_hh_mm", 0);
        
        // Use setTimeout to ensure filters are initialized
        setTimeout(function() {
            try {
                frappe.call({
                    method: "biometric_integration.biometric_integration.report.biometric_monthly_report.biometric_monthly_report.get_attendance_years",
                    callback: function(r) {
                        if (r.message && r.message.length) {
                            try {
                                let year_filter = frappe.query_report.get_filter("year");
                                if (!year_filter) {
                                    console.error("Year filter not found");
                                    return;
                                }
                                
                                year_filter.df.options = r.message;
                                year_filter.refresh();
                                
                                // Set default to current year
                                const currentYear = new Date().getFullYear().toString();
                                if (r.message.includes(currentYear)) {
                                    year_filter.set_input(currentYear);
                                } else if (r.message.length > 0) {
                                    year_filter.set_input(r.message[0]);
                                }
                                
                                // Now update the month filter
                                update_month_filter();
                            } catch (e) {
                                console.error("Error setting year filter:", e);
                            }
                        } else {
                            console.error("No years returned from server");
                        }
                    }
                });
            } catch (e) {
                console.error("Error in onload:", e);
            }
        }, 1000);
    },

    refresh: function(report) {
        report.set_filter_value("total_hours_hh_mm", 0);
    },
};

// Function to update the month filter based on the selected year
function update_month_filter() {
    try {
        let year_filter = frappe.query_report.get_filter_value("year");
        let current_year = new Date().getFullYear().toString();
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

        let filtered_months = year_filter === current_year ? months.slice(0, current_month) : months;
        
        let month_filter = frappe.query_report.get_filter("month");
        if (!month_filter) {
            console.error("Month filter not found");
            return;
        }
        
        month_filter.df.options = filtered_months;
        month_filter.df.default = filtered_months.length ? filtered_months[filtered_months.length - 1].value : null;
        month_filter.refresh();
        month_filter.set_input(month_filter.df.default);
    } catch (e) {
        console.error("Error in update_month_filter:", e);
    }
}