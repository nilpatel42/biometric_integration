// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Biometric Integration Settings", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on("Biometric Integration Settings", {
    refresh: function(frm) {
        frm.add_custom_button(__('Sync Attendance'), function() {
            frappe.call({
                method: "biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.sync_attendance",
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                }
            });
            
        });        
    }
});

frappe.ui.form.on('Biometric Integration Settings', {
    refresh: function(frm) {
        frm.add_custom_button(__('Sync Manual Punches'), function() {
            // Confirm action
            frappe.confirm(
                __('Are you sure you want to update all manual punches?'),
                function() {
                    // Call the server-side method
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.update_all_manual_punches',
                        callback: function(response) {
                            frappe.msgprint(response.message);
                        }
                    });
                },
                function() {
                    frappe.msgprint(__('Action canceled.'));
                }
            );
        });
    }
});


frappe.ui.form.on('Biometric Integration Settings', {
    refresh: function(frm) {
        frm.add_custom_button(__('Update Manual Punch for Maganbhai'), function() {
            // Create a dialog to ask for a date
            let d = new frappe.ui.Dialog({
                title: 'Select Date',
                fields: [
                    {
                        label: 'Date',
                        fieldname: 'target_date',
                        fieldtype: 'Date',
                        reqd: 1
                    }
                ],
                primary_action_label: 'Update',
                primary_action(values) {
                    // Call the server-side method with selected date
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.update_manual_punch_for_employee',
                        args: {
                            target_date: values.target_date
                        },
                        callback: function(response) {
                            frappe.msgprint(response.message);
                        }
                    });
                    d.hide();
                }
            });
            d.show();
        });
    }
});

