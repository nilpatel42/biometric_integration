// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.ui.form.on('Biometric Integration Settings', {
    refresh(frm) {
        frm.add_custom_button(__('Sync Attendance'), function() {
            const d = new frappe.ui.Dialog({
                title: __('Sync Attendance by Date Range'),
                fields: [
                    {
                        fieldname: 'from_date',
                        label: __('From Date'),
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        fieldname: 'to_date',
                        label: __('To Date'),
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    }
                ],
                primary_action_label: __('Sync'),
                primary_action(values) {
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.sync_attendance',
                        args: {
                            start_date: values.from_date,
                            end_date: values.to_date
                        },
                        freeze: true,
                        freeze_message: __('Syncing Attendance from 00:00:00 to 23:59:59...'),
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
                    d.hide();
                }
            });

            d.show();
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
                        fieldname: 'target_date',
                        label: __('Date'),
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
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
                            const result = response.message || {};
                            frappe.msgprint(result.message || __('Update completed.'));
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
    const button_field = frm.fields_dict.check_connection_button;
    if (!button_field || !button_field.$input || frm._connection_check_bound) {
        return;
    }

    frm._connection_check_bound = true;
    button_field.$input.on('click', function() {
        frappe.call({
            method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.check_machine_connection',
            freeze: true,
            freeze_message: __('Checking machine connection...'),
            callback: function(r) {
                const result = r.message || {};
                const indicator = result.status === 'success' ? 'green' : 'red';

                frappe.msgprint({
                    title: result.status === 'success' ? __('Connection Successful') : __('Connection Failed'),
                    indicator: indicator,
                    message: `<div><b>${__('Result')}:</b> ${frappe.utils.escape_html(result.message || __('Unknown response'))}</div>
                              <br><div><b>${__('Details')}:</b><br>${frappe.utils.escape_html(result.details || __('No details available'))}</div>`
                });
            }
        });
    });
}
