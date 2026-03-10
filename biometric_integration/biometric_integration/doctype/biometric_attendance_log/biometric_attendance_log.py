# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today
from frappe.model.document import Document


class BiometricAttendanceLog(Document):
    def on_update(self):
        update_total_hours(self)

    def after_insert(self):
        update_total_hours(self)


# ── helpers (exact logic from report) ─────────────────────────────────────────

def calculate_total_minutes(punches):
    total_minutes = 0
    for i in range(0, len(punches) - 1, 2):
        try:
            punch_in  = punches[i]["punch_time"]
            punch_out = punches[i + 1]["punch_time"]
            minutes_diff = int(punch_out.total_seconds() / 60) - int(punch_in.total_seconds() / 60)
            total_minutes += minutes_diff
        except Exception:
            return 0
    return total_minutes

def format_minutes_to_hhmm(minutes):
    hours, mins = divmod(minutes, 60)
    return f"{hours:02}:{mins:02}"

def update_total_hours(doc):
    punches = frappe.db.sql("""
        SELECT punch_time, punch_type
        FROM `tabBiometric Attendance Punch Table`
        WHERE parent = %(name)s
        ORDER BY punch_time
    """, {"name": doc.name}, as_dict=True)

    if not punches:
        return  
		
    if len(punches) % 2 != 0:
        result = "Odd Punches"
    else:
        result = format_minutes_to_hhmm(calculate_total_minutes(punches))

    frappe.db.set_value("Biometric Attendance Log", doc.name, "total_hours", result, update_modified=False)



def delete_old_attendance_logs():
    """Delete Biometric Attendance Logs based on Settings"""

    settings = frappe.get_single("Biometric Integration Settings")

    # Only run if deletion is enabled
    if not settings.enable_biometric_attendance_log_deletion:
        frappe.logger().info("Biometric Attendance Log deletion is disabled. Skipping.")
        return

    # Use configured days, fallback to 370 if 0 or not set
    retention_days = settings.delete_logs_after_days or 370

    cutoff_date = add_days(today(), -retention_days)

    old_logs = frappe.get_all(
        "Biometric Attendance Log",
        filters={
            "event_date": ["<", cutoff_date]
        },
        pluck="name"
    )

    if not old_logs:
        frappe.logger().info("No old Biometric Attendance Logs found to delete.")
        return

    for log_name in old_logs:
        frappe.delete_doc(
            "Biometric Attendance Log",
            log_name,
            ignore_permissions=True,
            force=True
        )

    frappe.db.commit()
    frappe.logger().info(
        f"Deleted {len(old_logs)} Biometric Attendance Logs older than "
        f"{retention_days} days (before {cutoff_date})"
    )