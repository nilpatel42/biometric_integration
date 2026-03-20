// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.ui.form.on('Biometric Integration Settings', {
    validate(frm) {
        if (frm.doc.enable_biometric_attendance_log_deletion) {
            if (!frm.doc.delete_logs_after_days || frm.doc.delete_logs_after_days <= 0) {
                frappe.throw("Delete Logs After (Days) must be greater than 0");
            }
        }
    },

    refresh(frm) {

        // Only show buttons if device credentials are filled
        if (!(frm.doc.ip && frm.doc.username && frm.doc.password)) {
            return;
        }

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
                        args: values,
                        freeze: true,
                        freeze_message: __('Syncing Attendance...'),
                        callback: function(r) {
                            if (r.message) {
                                frappe.show_alert({
                                    message: r.message,
                                    indicator: 'green'
                                }, 10);
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

        frm.add_custom_button('Fetch Device Info', () => {
            frappe.call({
                method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.fetch_device_info',
                callback: function(r) {
                    console.log(r);  // 🔥 DEBUG

                    if (!r.exc && r.message) {
                        frappe.show_alert({
                            message: r.message.message || 'Done',
                            indicator: 'green'
                        }, 5);

                        frm.reload_doc();
                    }
                },
                error: function(err) {
                    console.log(err);
                    frappe.show_alert({
                        message: 'Error fetching device info',
                        indicator: 'red'
                    }, 5);
                }
            });
        }, __('Device'));

        frm.add_custom_button('View Face', () => {

            frappe.prompt([
                {
                    label: 'Employee ID',
                    fieldname: 'emp_no',
                    fieldtype: 'Data',
                    reqd: 1
                }
            ], (values) => {

                frappe.call({
                    method: 'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.get_employee_face',
                    args: {
                        emp_no: values.emp_no
                    },
                    freeze: true,
                    freeze_message: 'Fetching face...',
                    callback: function(r) {

                        if (r.message.status === "success") {

                            let img_html = "";

                            if (r.message.type === "url") {
                                img_html = `<img src="${r.message.data}" style="max-width:100%;">`;
                            }

                            if (r.message.type === "base64") {
                                img_html = `<img src="data:image/jpeg;base64,${r.message.data}" style="max-width:100%;">`;
                            }

                            frappe.msgprint({
                                title: "Employee Face",
                                message: img_html
                            });

                        } else {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'red'
                            });
                        }
                    }
                });

            }, 'Enter Employee ID', 'Fetch');

        }, __('Device'));

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
        }, __('Device'));

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