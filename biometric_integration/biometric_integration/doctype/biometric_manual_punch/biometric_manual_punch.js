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

frappe.ui.form.on('Biometric Manual Punch', {
    refresh: function(frm) {
        // Check if the document is new or not
        if (!frm.is_new()) {
            // Make the 'punch_time' and 'punch_date' fields read-only
            frm.set_df_property('punch_time', 'read_only', 1);
            frm.set_df_property('punch_date', 'read_only', 1);
        } else {
            // Make the fields editable if the document is new
            frm.set_df_property('punch_time', 'read_only', 0);
            frm.set_df_property('punch_date', 'read_only', 0);
        }
    }
});


frappe.ui.form.on('Biometric Manual Punch', {
    refresh: function(frm) {
        frm.add_custom_button(__('Edit Date & Time'), function() {
            frappe.prompt([
                {
                    label: 'New Punch Date',
                    fieldname: 'new_punch_date',
                    fieldtype: 'Date',
                    reqd: 1,
                    default: frm.doc.punch_date
                },
                {
                    label: 'New Punch Time',
                    fieldname: 'new_punch_time',
                    fieldtype: 'Time',
                    reqd: 1,
                    default: frm.doc.punch_time
                }
            ], function(values) {
                // Disable the form fields to prevent changes during deletion
                frm.set_df_property("punch_date", "read_only", 1);
                frm.set_df_property("punch_time", "read_only", 1);

                // Call the server-side method to delete old punch and update the date and time
                frappe.call({
                    method: "biometric_integration.biometric_integration.doctype.biometric_manual_punch.biometric_manual_punch.edit_button_delete_punch",
                    args: {
                        doc_name: frm.doc.name,
                        new_punch_date: values.new_punch_date,
                        new_punch_time: values.new_punch_time
                    },
                    callback: function(response) {
                        if (response.message) {
                            
                            frm.reload_doc()

                            frappe.show_alert({
                                message: 'Date & Time Edited Successfully',
                                indicator: 'green'
                            }, 5);
                        } else {
                            frappe.msgprint(__('Failed to update the manual punch. Please try again.'));
                        }
                    }
                });
            }, __("Edit Punch Date & Time"), __("Update"));
        });
    }
});


