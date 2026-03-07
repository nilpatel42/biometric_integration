// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.ui.form.on('Biometric Integration Settings', {
    refresh(frm) {

        frm.add_custom_button(__('Attendance'), function() {
            const d = new frappe.ui.Dialog({
                title: __('Select Date & Time Range'),
                fields: [
                    {
                        label: __('From Date'),
                        fieldname: 'from_date',
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        label: __('From Time'),
                        fieldname: 'from_time',
                        fieldtype: 'Time',
                        default: '00:00:00',
                        reqd: 1
                    },
                    { fieldtype: 'Column Break' },
                    {
                        label: __('To Date'),
                        fieldname: 'to_date',
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        label: __('To Time'),
                        fieldname: 'to_time',
                        fieldtype: 'Time',
                        default: '23:59:59',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Sync'),
                primary_action(values) {
                    d.hide();
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.sync_attendance',
                        args: {
                            from_date: values.from_date,
                            from_time: values.from_time,
                            to_date: values.to_date,
                            to_time: values.to_time
                        },
                        freeze: true,
                        freeze_message: __('Syncing Attendance...'),
                        callback: function(r) {
                            if (r.message) {
                                frappe.show_alert({
                                    message: __(r.message),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }
            });
            d.show();
        }, __('Sync'));

        frm.add_custom_button(__('Manual Punches'), function() {
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
        }, __('Sync'));

        frm.add_custom_button(__('Update Employee Name'), function() {
            const d = new frappe.ui.Dialog({
                title: __('Set Employee Name on Device'),
                fields: [
                    {
                        label: __('Employee ID (Device)'),
                        fieldname: 'emp_no',
                        fieldtype: 'Data',
                        reqd: 1
                    },
                    {
                        label: __('Employee Name'),
                        fieldname: 'emp_name',
                        fieldtype: 'Data',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Save'),
                primary_action(values) {
                    d.hide();
                    frappe.call({
                        method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.set_employee_name_on_device',
                        args: {
                            emp_no: values.emp_no,
                            emp_name: values.emp_name
                        },
                        freeze: true,
                        freeze_message: __('Saving...'),
                        callback: function(r) {
                            const result = r.message || {};
                            frappe.msgprint({
                                title: result.status === 'success' ? __('Success') : __('Failed'),
                                indicator: result.status === 'success' ? 'green' : 'red',
                                message: __(result.message)
                            });
                        }
                    });
                }
            });
            d.show();
        }, __('Set to Device'));

        frm.add_custom_button(__('Test Device Connection'), function() {
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
});