// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.ui.form.on('Biometric Integration Settings', {
    refresh(frm) {
        frm.add_custom_button(__('Sync Attendance'), function() {
            frappe.call({
                method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.sync_attendance',
                freeze: true,
                freeze_message: __('Syncing Attendance...'),
                callback: function(r) {
                    frappe.hide_progress();
                    if (r.message) {
                        frappe.show_alert({
                            message: __(r.message),
                            indicator: 'green'
                        });
                    }
                }
            });
        });

        frm.add_custom_button(__('Sync Manual Punches'), function() {
            frappe.confirm(
                __('Are you sure you want to update all manual punches?'),
                function() {
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.update_all_manual_punches',
                        callback: function(response) {
                            frappe.show_alert({
                                message: __(response.message),
                                indicator: 'green'
                            });
                        }
                    });
                },
                function() {
                    frappe.show_alert({
                        message: __('Action Canceled'),
                        indicator: 'yellow'
                    });
                }
            );
        });

        frm.add_custom_button(__('Update Manual Punch for Maganbhai'), function() {
            const d = new frappe.ui.Dialog({
                title: __('Select Date'),
                fields: [
                    {
                        label: __('Date'),
                        fieldname: 'target_date',
                        fieldtype: 'Date',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Update'),
                primary_action(values) {
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.update_manual_punch_for_employee',
                        args: {
                            target_date: values.target_date
                        },
                        callback: function(response) {
                            frappe.msgprint(response.message?.message || response.message || __('Update completed.'));
                        }
                    });
                    d.hide();
                }
            });
            d.show();
        });

        bind_check_connection_button(frm);
    }
});

function bind_check_connection_button(frm) {
    const buttonField = frm.fields_dict.check_connection_button;
    if (!buttonField || !buttonField.$input || frm._connection_check_bound) {
        return;
    }

    frm._connection_check_bound = true;
    buttonField.$input.on('click', function() {
        frappe.call({
            method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.check_machine_connection',
            freeze: true,
            freeze_message: __('Checking machine connection...'),
            callback: function(r) {
                const result = r.message || {};
                const indicator = result.status === 'success' ? 'green' : 'red';
                frappe.msgprint({
                    title: result.status === 'success' ? __('Connection Successful') : __('Connection Failed'),
                    indicator,
                    message: `<div><b>${__('Result')}:</b> ${frappe.utils.escape_html(result.message || __('Unknown response'))}</div>
                              <br><div><b>${__('Details')}:</b><br>${frappe.utils.escape_html(result.details || __('No details available'))}</div>`
                });
            }
        });
    });
}
