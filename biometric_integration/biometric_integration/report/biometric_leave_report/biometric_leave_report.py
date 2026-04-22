# Copyright (c) 2026, NDV and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime
import calendar

def execute(filters=None):
    columns = [
        {"fieldname": "employee_name",  "label": _("Name"),           "fieldtype": "Data", "width": 250, "align": "left"},
        {"fieldname": "employee_id",    "label": _("ID"),             "fieldtype": "Data", "width": 80,  "align": "center"},
        {"fieldname": "leave_duration", "label": _("Leave Duration"), "fieldtype": "Data", "width": 100, "align": "center"},
        {"fieldname": "full_day",       "label": _("Full Day"),       "fieldtype": "Data", "width": 80,  "align": "center"},
        {"fieldname": "leave_from",     "label": _("Leave From"),     "fieldtype": "Data", "width": 100, "align": "center"},
        {"fieldname": "leave_to",       "label": _("Leave To"),       "fieldtype": "Data", "width": 100, "align": "center"},
    ]

    selected_date  = filters.get('date')     if filters else None
    selected_emp   = filters.get('employee') if filters else None
    selected_month = filters.get('month')    if filters else None
    selected_year  = filters.get('year')     if filters else None

    # Nothing filled — just return empty, no error
    if not selected_date and not (selected_emp and selected_month and selected_year):
        return columns, []

    SHIFT_START = 7 * 3600 + 40 * 60
    shift_end_times = {
        "Full-time": 19 * 3600 + 40 * 60,
        "Mid Shift": 19 * 3600,
        "Part-time": 18 * 3600
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

    def yellow(val):
        return f'<span style="color: #cccc00">{val}</span>'

    if selected_emp and selected_month and selected_year:
        # Parse month name + year string into first/last day
        month_dt   = datetime.strptime(f"{selected_month} {selected_year}", "%B %Y")
        first_day  = month_dt.replace(day=1).strftime('%Y-%m-%d')
        last_day   = month_dt.replace(
                         day=calendar.monthrange(month_dt.year, month_dt.month)[1]
                     ).strftime('%Y-%m-%d')

        columns[0]["label"] = month_dt.strftime('%b %Y')
        columns.insert(1, {
            "fieldname": "leave_date",
            "label":     _("Date"),
            "fieldtype": "Data",
            "width":     150,
            "align":     "center"
        })

        where_clause = "l.date BETWEEN %(first_day)s AND %(last_day)s AND e.name = %(employee)s"
        conditions   = {"first_day": first_day, "last_day": last_day, "employee": selected_emp}
        order_by     = "l.date ASC"

    else:
        formatted_date     = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%b-%Y')
        columns[0]["label"] = formatted_date
        where_clause        = "l.date = %(selected_date)s"
        conditions          = {"selected_date": selected_date}
        order_by            = "CAST(l.employee_no AS UNSIGNED)"

    leave_logs = frappe.db.sql(f"""
        SELECT
            l.employee_no,
            l.full_day,
            l.leave_from,
            l.leave_to,
            l.date AS leave_date,
            e.employee_name,
            e.attendance_device_id,
            e.employment_type
        FROM `tabBiometric Leave Log` l
        JOIN `tabEmployee` e ON e.attendance_device_id = l.employee_no
        WHERE {where_clause}
        ORDER BY {order_by}
    """, conditions, as_dict=True)

    data = []

    for log in leave_logs:
        leave_from_seconds = parse_time_to_seconds(log.leave_from)
        leave_to_seconds   = parse_time_to_seconds(log.leave_to)
        employment_type    = log.employment_type
        shift_end          = shift_end_times.get(employment_type)
        full_shift_minutes = ((shift_end - SHIFT_START) / 60) if shift_end else None

        if log.full_day:
            leave_duration = fmt_duration(full_shift_minutes) if full_shift_minutes else ""
        elif leave_from_seconds is not None and shift_end is not None:
            leave_duration = fmt_duration((shift_end - leave_from_seconds) / 60)
        elif leave_to_seconds is not None:
            leave_duration = fmt_duration((leave_to_seconds - SHIFT_START) / 60)
        else:
            leave_duration = ""

        if log.full_day:
            leave_from_display = "-"
        elif leave_from_seconds is not None:
            leave_from_display = fmt_seconds(leave_from_seconds)
        elif leave_to_seconds is not None:
            leave_from_display = yellow(fmt_seconds(SHIFT_START))
        else:
            leave_from_display = ""

        if log.full_day:
            leave_to_display = "-"
        elif leave_to_seconds is not None:
            leave_to_display = fmt_seconds(leave_to_seconds)
        elif leave_from_seconds is not None:
            leave_to_display = yellow(fmt_seconds(shift_end)) if shift_end else ""
        else:
            leave_to_display = ""

        row = {
            "employee_name":  log.employee_name,
            "employee_id":    log.attendance_device_id,
            "leave_duration": leave_duration,
            "full_day":       "Yes" if log.full_day else "-",
            "leave_from":     leave_from_display,
            "leave_to":       leave_to_display,
        }

        if selected_emp and selected_month:
            row["leave_date"] = datetime.strptime(str(log.leave_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        data.append(row)

    return columns, data