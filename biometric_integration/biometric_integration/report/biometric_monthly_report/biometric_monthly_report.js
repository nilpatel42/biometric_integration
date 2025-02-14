// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Monthly Report"] = {
    filters: [
        {
            fieldname: "date_range",
            label: __("Enter Your Date Range"),
            fieldtype: "Date Range",
        },
    ]
};


// frappe.query_reports["Biometric Monthly Report"] = {
// 	filters: [
// 		{
// 			fieldname: "month",
// 			label: __("Month"),
// 			fieldtype: "Select",
// 			reqd: 1,
// 			options: [
// 				{ value: 1, label: __("Jan") },
// 				{ value: 2, label: __("Feb") },
// 				{ value: 3, label: __("Mar") },
// 				{ value: 4, label: __("Apr") },
// 				{ value: 5, label: __("May") },
// 				{ value: 6, label: __("June") },
// 				{ value: 7, label: __("July") },
// 				{ value: 8, label: __("Aug") },
// 				{ value: 9, label: __("Sep") },
// 				{ value: 10, label: __("Oct") },
// 				{ value: 11, label: __("Nov") },
// 				{ value: 12, label: __("Dec") },
// 			],
// 			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
// 		},
// 		{
// 			fieldname: "year",
// 			label: __("Year"),
// 			fieldtype: "Select",
// 			reqd: 1,
// 		},
// 		{
// 			fieldname: "employee",
// 			label: __("Employee"),
// 			fieldtype: "Link",
// 			options: "Employee",
// 		},
// 	],
// 	onload: function () {
// 		return frappe.call({
// 			method: "biometric_integration.biometric_integration.report.biometric_monthly_report.biometric_monthly_report.get_attendance_years",            
// 			callback: function (r) {
// 				var year_filter = frappe.query_report.get_filter("year");
// 				year_filter.df.options = r.message;
// 				year_filter.df.default = r.message.split("\n")[0];
// 				year_filter.refresh();
// 				year_filter.set_input(year_filter.df.default);
// 			},
// 		});
// 	}
// };
    