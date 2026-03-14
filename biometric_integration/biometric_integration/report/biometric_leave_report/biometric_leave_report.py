# Copyright (c) 2026, NDV and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = [
        {"fieldname": "employee_name",   "label": _("Name"),           "fieldtype": "Data", "width": 250, "align": "left"},
        {"fieldname": "employee_id",     "label": _("ID"),             "fieldtype": "Data", "width": 80,  "align": "center"},
        {"fieldname": "employment_type", "label": _("Type"),           "fieldtype": "Data", "width": 100, "align": "center"},
        {"fieldname": "full_day",        "label": _("Full Day"),       "fieldtype": "Data", "width": 80,  "align": "center"},
        {"fieldname": "leave_from",      "label": _("Leave From"),     "fieldtype": "Data", "width": 100, "align": "center"},
        {"fieldname": "leave_to",        "label": _("Leave To"),       "fieldtype": "Data", "width": 100, "align": "center"},
        {"fieldname": "leave_duration",  "label": _("Leave Duration"), "fieldtype": "Data", "width": 150, "align": "center"},
    ]

    if not filters or not filters.get('date'):
        frappe.throw(_("Please select a date."))

    selected_date = filters.get('date')
    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%b-%Y')
    columns[0]["label"] = formatted_date

    # Shift timings in seconds
    SHIFT_START = 7 * 3600 + 40 * 60  # 07:40
    shift_end_times = {
        "Full-time": 19 * 3600 + 40 * 60,  # 19:40
        "Mid Shift": 19 * 3600,              # 19:00
        "Part-time": 18 * 3600               # 18:00
    }

    def parse_time_to_seconds(val):
        if val is None:
            return None
        if hasattr(val, 'total_seconds'):
            return val.total_seconds()
        try:
            parts = str(val).split(":")
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            return None

    def fmt_seconds(total_seconds):
        if total_seconds is None:
            return ""
        h, m = divmod(int(total_seconds / 60), 60)
        return f"{h:02}:{m:02}"

    def fmt_duration(minutes):
        if minutes is None or minutes <= 0:
            return ""
        h, m = divmod(int(minutes), 60)
        return f"{h:02}:{m:02}"

    # Fetch leave logs for selected date with employee details
    leave_logs = frappe.db.sql("""
        SELECT
            l.employee_no,
            l.full_day,
            l.leave_from,
            l.leave_to,
            e.employee_name,
            e.attendance_device_id,
            e.employment_type
        FROM `Biometric Leave Log` l
        JOIN `tabEmployee` e ON e.attendance_device_id = l.employee_no
        WHERE l.date = %(selected_date)s
        ORDER BY CAST(l.employee_no AS UNSIGNED)
    """, {"selected_date": selected_date}, as_dict=True)

    def natural_sort_key(log):
        try:
            return int(log.employee_no)
        except Exception:
            return log.employee_no

    leave_logs.sort(key=natural_sort_key)

    data = []

    for log in leave_logs:
        leave_from_seconds = parse_time_to_seconds(log.leave_from)
        leave_to_seconds   = parse_time_to_seconds(log.leave_to)
        employment_type    = log.employment_type
        shift_end          = shift_end_times.get(employment_type)
        full_shift_minutes = ((shift_end - SHIFT_START) / 60) if shift_end else None

        # Calculate leave duration
        leave_duration = ""
        if log.full_day:
            leave_duration = fmt_duration(full_shift_minutes) if full_shift_minutes else ""
        elif leave_from_seconds is not None and shift_end is not None:
            # leave_from to shift end
            duration_minutes = (shift_end - leave_from_seconds) / 60
            leave_duration = fmt_duration(duration_minutes)
        elif leave_to_seconds is not None:
            # day start to leave_to
            duration_minutes = (leave_to_seconds - SHIFT_START) / 60
            leave_duration = fmt_duration(duration_minutes)

        def yellow(val):
            return f'<span style="color: #cccc00">{val}</span>'

        # leave_from display: actual value or system-added shift end in yellow
        if log.full_day:
            leave_from_display = "-"
        elif leave_from_seconds is not None:
            leave_from_display = fmt_seconds(leave_from_seconds)
        elif leave_to_seconds is not None:
            # leave_to present, no leave_from -> system fills day start
            leave_from_display = yellow(fmt_seconds(SHIFT_START))
        else:
            leave_from_display = ""

        # leave_to display: actual value or system-added shift end in yellow
        if log.full_day:
            leave_to_display = "-"
        elif leave_to_seconds is not None:
            leave_to_display = fmt_seconds(leave_to_seconds)
        elif leave_from_seconds is not None:
            # leave_from present, no leave_to -> system fills shift end
            leave_to_display = yellow(fmt_seconds(shift_end)) if shift_end else ""
        else:
            leave_to_display = ""

        row = {
            "employee_name":   log.employee_name,
            "employee_id":     log.attendance_device_id,
            "employment_type": employment_type or "",
            "full_day":        "Yes" if log.full_day else "-",
            "leave_from":      leave_from_display,
            "leave_to":        leave_to_display,
            "leave_duration":  leave_duration,
        }
        data.append(row)

    return columns, data