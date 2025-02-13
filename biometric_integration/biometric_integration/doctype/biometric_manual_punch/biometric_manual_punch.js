// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.ui.form.on('Biometric Manual Punch', {
    before_save: function(frm) {
        // Add manual punch (this part remains the same)
        frappe.call({
            method: 'biometric_integration.biometric_integration.doctype.biometric_manual_punch.biometric_manual_punch.add_manual_punch',
            args: {
                employee: frm.doc.employee,
                punch_date: frm.doc.punch_date,
                punch_time: frm.doc.punch_time
            },
            callback: function(r) {
                console.log(r);  // Log the response for debugging

                if (r.message && r.message.status === 'success') {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'green'  // Success message in green
                    }, 5);  // Show for 5 seconds
                } else if (r.message && r.message.status === 'error') {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'red'  // Error message in red
                    }, 5);
                    frappe.validated = false;  // Prevent saving the document
                } else {
                    frappe.show_alert({
                        message: 'An unknown error occurred',
                        indicator: 'red'
                    }, 5);
                    frappe.validated = false;
                }
            },
            error: function(r) {
                frappe.show_alert({
                    message: r.message.message || 'An error occurred',
                    indicator: 'red'
                }, 5);
                frappe.validated = false;
            }
        });
    }
});




